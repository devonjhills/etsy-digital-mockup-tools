"""
OpenAI AI provider implementation.
"""

import os
import base64
import re
import io
import time
from typing import Dict, Any, List
from PIL import Image

from .base import AIProvider

# Set up logging
from utils.common import setup_logging
from utils.ai_utils import process_ai_response

logger = setup_logging(__name__)

# Try to import the OpenAI API client
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI package not found. Install with: pip install openai")
    OPENAI_AVAILABLE = False


class OpenAIProvider(AIProvider):
    """OpenAI AI provider implementation."""

    def __init__(self, api_key: str, model_name: str):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: API key for OpenAI
            model_name: Name of the model to use (e.g., "gpt-4.1-mini")
        """
        super().__init__(api_key, model_name)
        self.client = None

        # Set up OpenAI API client
        if OPENAI_AVAILABLE:
            try:
                # Configure the API with the provided key
                self.client = OpenAI(api_key=api_key)
                logger.info(
                    f"Successfully initialized OpenAI client with model: {model_name}"
                )
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                self.client = None
        else:
            logger.error("OpenAI API not available. Install with: pip install openai")

    def generate_content_from_image(
        self, image_path: str, instructions: str
    ) -> Dict[str, Any]:
        """
        Generate content (title, description, tags) from an image using OpenAI API.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the AI

        Returns:
            Dictionary with title, description, and tags
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI API not available. Install with: pip install openai")
            return {"title": "", "description": "", "tags": []}

        if not self.client:
            logger.error("OpenAI client not initialized")
            return {"title": "", "description": "", "tags": []}

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {"title": "", "description": "", "tags": []}

        try:
            # Open and validate the image
            try:
                img = Image.open(image_path)
                logger.info(f"Successfully opened image: {image_path}")
            except Exception as e:
                logger.error(f"Error opening image: {e}")
                return {"title": "", "description": "", "tags": []}

            # Convert image to base64 for OpenAI API
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format or "PNG")
            img_bytes = img_byte_arr.getvalue()
            base64_image = base64.b64encode(img_bytes).decode("utf-8")

            # Create the content for OpenAI API
            # Using the Chat Completions API for image analysis
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instructions},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )

            # Get the raw response text
            raw_content = response.choices[0].message.content.strip()
            logger.info("Successfully received response from OpenAI API")

            # Log the raw response for debugging
            logger.info(f"Raw OpenAI API response:\n{raw_content}")

            # Process the response using our centralized utility function
            content = process_ai_response(raw_content, is_thinking_model=False)

            logger.info(f"Processed OpenAI API response:\n{content}")

            # Simple parsing to extract title, description, and tags
            logger.info("Parsing content from OpenAI API response")

            title = ""
            description = ""
            tags = []

            # Try to parse the response as structured data
            try:
                # Look for title
                title_match = re.search(
                    r"(?:^|\n)Title:?\s*(.*?)(?:\n|$)", content, re.IGNORECASE
                )
                if title_match:
                    title = title_match.group(1).strip()
                    logger.info(f"Extracted title: {title}")

                # First, find the position of 'Tags:' to properly split the content
                tags_pos = content.find("\nTags:")
                if tags_pos == -1:
                    tags_pos = content.find("\nTags ")

                # Initialize description
                description = ""

                # Look for description - capture everything between Description: and Tags:
                if tags_pos != -1:
                    # If we found Tags:, extract description up to that point
                    # First find where Description: starts
                    desc_pos = content.find("Description:")
                    if desc_pos == -1:
                        desc_pos = content.find("Description ")

                    if desc_pos != -1 and desc_pos < tags_pos:
                        # Extract from after 'Description:' to before '\nTags:'
                        desc_start = desc_pos + len("Description:")
                        description = content[desc_start:tags_pos].strip()
                    else:
                        # Fallback to regex if we can't find Description: or it's after Tags:
                        desc_match = re.search(
                            r"(?:^|\n)Description:?\s*([\s\S]*?)\nTags:",
                            content,
                            re.IGNORECASE,
                        )
                        if desc_match:
                            description = desc_match.group(1).strip()
                else:
                    # If no Tags: section, use regex to capture until the end
                    desc_match = re.search(
                        r"(?:^|\n)Description:?\s*([\s\S]*?)$",
                        content,
                        re.IGNORECASE,
                    )
                    if desc_match:
                        description = desc_match.group(1).strip()

                # Log the extracted description
                logger.info(
                    f"Extracted description: {description[:50] if description else 'None'}..."
                )

                # Look for tags
                tags_match = re.search(
                    r"(?:^|\n)Tags:?\s*([\s\S]*?)$",
                    content,
                    re.IGNORECASE,
                )
                if tags_match:
                    tags_text = tags_match.group(1).strip()
                    # Split tags by commas, newlines, or other common separators
                    tags_raw = re.split(r"[,\n|;]", tags_text)
                    # Clean up each tag
                    tags = [
                        re.sub(r"^\d+\.\s*", "", tag.strip())  # Remove numbering
                        .strip("\"'[](){} \t")  # Remove quotes and brackets
                        .strip()
                        for tag in tags_raw
                        if tag.strip()
                    ]
                    logger.info(f"Extracted tags: {tags}")

                # If we couldn't extract structured data, try to parse the whole content
                if not title and not description and not tags:
                    logger.warning(
                        "Could not extract structured data from OpenAI response, trying alternative parsing"
                    )
                    lines = content.split("\n")
                    if lines:
                        # First line is often the title
                        title = lines[0].strip()
                        # Rest could be description
                        if len(lines) > 1:
                            description = "\n".join(lines[1:]).strip()

            except Exception as e:
                logger.error(f"Error parsing OpenAI response: {e}")

            return {
                "title": title,
                "description": description,
                "tags": tags,
            }

        except Exception as e:
            logger.error(f"Error generating content from image with OpenAI: {e}")
            return {"title": "", "description": "", "tags": []}
