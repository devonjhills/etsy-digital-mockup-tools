"""
Module for generating listing content with SEO optimization.
"""

import os
import base64
from typing import Dict
import re
import sys
from PIL import Image
import io

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)

# Try to import the Gemini API client
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning(
        "Google Generative AI package not found. Install with: pip install google-generativeai"
    )
    GEMINI_AVAILABLE = False


class ContentGenerator:
    """Generate listing content with SEO optimization."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro-exp-03-25"):
        """
        Initialize the content generator.

        Args:
            api_key: API key for the Gemini API
            model_name: Name of the Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name

        # Set up Gemini API client
        if GEMINI_AVAILABLE:
            # Configure the API with the provided key
            genai.configure(api_key=api_key)

            # Set up safety settings according to documentation
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # Initialize the model with the specified name and safety settings
            self.gemini_model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                },
            )
            logger.info(f"Using Gemini API model {model_name} for content generation")
        else:
            logger.error(
                "Google Generative AI package not found. Install with: pip install google-generativeai"
            )
            print(
                "Google Generative AI package not found. Install with: pip install google-generativeai",
                file=sys.stderr,
            )

    # Custom functions for generating title, description, and tags have been removed
    # We now rely entirely on the instructions passed to the Gemini API

    def generate_content_from_image(
        self, image_path: str, instructions: str
    ) -> Dict[str, str]:
        """
        Generate listing content (title, description, tags) from an image using Gemini API.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the LLM

        Returns:
            Dictionary with title, description, and tags
        """
        if not os.path.exists(image_path):
            error_msg = f"Image file not found: {image_path}"
            logger.error(error_msg)
            import sys

            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        try:
            if not GEMINI_AVAILABLE:
                error_msg = "Gemini API not available. Install with: pip install google-generativeai"
                logger.error(error_msg)
                import sys

                print(error_msg, file=sys.stderr)
                return {"title": "", "description": "", "tags": []}

            # Check if the API key is valid
            if not self.api_key:
                error_msg = (
                    "No Gemini API key provided. Set GEMINI_API_KEY in environment."
                )
                logger.error(error_msg)
                import sys

                print(error_msg, file=sys.stderr)
                return {"title": "", "description": "", "tags": []}

            # Load the image
            try:
                img = Image.open(image_path)
                logger.info(f"Successfully loaded image: {image_path}")
            except Exception as e:
                logger.error(f"Error loading image {image_path}: {e}")
                return {"title": "", "description": "", "tags": []}

            # Use the instructions directly as the prompt
            prompt = instructions

            # Add a simple note about avoiding markers
            prompt += "\n\nIMPORTANT: DO NOT include any ** or other markers in your response."

            logger.info(f"Using Gemini model: {self.model_name}")

            # Call Gemini API with image
            try:
                # Convert PIL Image to bytes for Gemini API
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format=img.format or "PNG")
                img_bytes = img_byte_arr.getvalue()

                # Create the content parts according to documentation
                parts = [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": f"image/{img.format.lower() if img.format else 'png'}",
                            "data": base64.b64encode(img_bytes).decode("utf-8"),
                        }
                    },
                ]

                # Generate content with proper error handling
                response = self.gemini_model.generate_content(parts)

                # Check if the response is valid
                if not hasattr(response, "text"):
                    logger.error(f"Invalid response from Gemini API: {response}")
                    return {"title": "", "description": "", "tags": []}

                content = response.text.strip()
                logger.info("Successfully received response from Gemini API")

                # Log the raw response for debugging
                logger.info(f"Raw Gemini API response:\n{content}")
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                print(f"Error calling Gemini API: {e}", file=sys.stderr)
                return {"title": "", "description": "", "tags": []}

            # Simple parsing to extract title, description, and tags
            logger.info("Parsing content from Gemini API response")

            title = ""
            description = ""
            tags = []

            # Basic extraction with regex
            title_match = re.search(
                r"Title:\s*(.+?)(?:\n|Description:)", content, re.DOTALL
            )
            if title_match:
                title = title_match.group(1).strip()
                # Remove any ** markers if present
                title = re.sub(r"^\*\*\s*", "", title)

            # Extract description - look for everything between Description: and Tags:
            desc_start = content.find("Description:")
            tags_start = content.find("Tags:")

            if desc_start >= 0 and tags_start > desc_start:
                # Extract everything between Description: and Tags:
                description = content[desc_start + 12 : tags_start].strip()
                logger.info(f"Found description with length: {len(description)}")
            else:
                # Try regex as a fallback
                logger.info("Using regex fallback for description")
                desc_match = re.search(
                    r"Description:\s*(.+?)(?:\n|Tags:)", content, re.DOTALL
                )
                if desc_match:
                    description = desc_match.group(1).strip()

            # Remove any ** markers if present
            description = re.sub(r"^\*\*\s*", "", description)

            tags_match = re.search(r"Tags:\s*(.+)$", content, re.DOTALL)
            if tags_match:
                tags_text = tags_match.group(1).strip()
                # Remove any ** markers if present
                tags_text = re.sub(r"^\*\*\s*", "", tags_text)
                # Split by comma and clean up
                tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

            # Log what we extracted
            logger.info(f"Extracted title: {title}")
            logger.info(f"Extracted description length: {len(description)}")
            logger.info(f"Extracted tags count: {len(tags)}")

            return {"title": title, "description": description, "tags": tags}
        except Exception as e:
            logger.error(f"Error generating content from image: {e}")
            return {"title": "", "description": "", "tags": []}
