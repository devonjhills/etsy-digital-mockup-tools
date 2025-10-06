"""
Gemini AI provider implementation.
"""

import os
import base64
import re
import io
import time
from typing import Dict, Any
from PIL import Image

from .base import AIProvider

# Set up logging
from src.utils.common import setup_logging
from src.utils.ai_utils import process_ai_response

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


class GeminiProvider(AIProvider):
    """Gemini AI provider implementation."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-pro"):
        """
        Initialize the Gemini provider.

        Args:
            api_key: API key for the Gemini API
            model_name: Name of the Gemini model to use
        """
        super().__init__(api_key, model_name)
        self.gemini_model = None

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
            logger.info(f"Initialized Gemini model: {model_name}")

    def generate_content_from_image(
        self, image_path: str, instructions: str
    ) -> Dict[str, Any]:
        """
        Generate content (title, description, tags) from an image using Gemini API.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the AI

        Returns:
            Dictionary with title, description, and tags
        """
        if not GEMINI_AVAILABLE:
            logger.error(
                "Gemini API not available. Install with: pip install google-generativeai"
            )
            return {"title": "", "description": "", "tags": []}

        if not self.gemini_model:
            logger.error("Gemini model not initialized")
            return {"title": "", "description": "", "tags": []}

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {"title": "", "description": "", "tags": []}

        try:
            # Load the image
            img = Image.open(image_path)
            logger.info(f"Successfully loaded image: {image_path}")

            # Get the image file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            logger.info(f"Image file size: {file_size_mb:.2f} MB")

            # If image is too large, resize it
            max_size_mb = 3.5  # Maximum size in MB for reliable API calls
            if file_size_mb > max_size_mb:
                logger.info(
                    f"Image is large ({file_size_mb:.2f} MB), resizing for API call"
                )
                # Calculate new dimensions while maintaining aspect ratio
                max_dimension = 1500  # Maximum dimension in pixels
                if img.width > img.height:
                    new_width = min(img.width, max_dimension)
                    new_height = int(img.height * (new_width / img.width))
                else:
                    new_height = min(img.height, max_dimension)
                    new_width = int(img.width * (new_height / img.height))

                # Resize the image
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.info(f"Resized image to {new_width}x{new_height} for API call")

            # Convert image to bytes for Gemini API
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format or "PNG")
            img_bytes = img_byte_arr.getvalue()

            # Create the content parts
            parts = [
                {"text": instructions},
                {
                    "inline_data": {
                        "mime_type": f"image/{img.format.lower() if img.format else 'png'}",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    }
                },
            ]

            # Generate content
            response = self.gemini_model.generate_content(parts)

            # Check if the response is valid
            if not hasattr(response, "text"):
                logger.error(f"Invalid response from Gemini API: {response}")
                return {"title": "", "description": "", "tags": []}

            # Get the raw response text
            raw_content = response.text.strip()
            logger.info("Successfully received response from Gemini API")

            # Log the raw response for debugging
            logger.info(f"Raw Gemini API response:\n{raw_content}")

            # Process the response using our centralized utility function
            # Gemini doesn't have thinking models, so we set is_thinking_model to False
            content = process_ai_response(raw_content, is_thinking_model=False)

            logger.info(f"Processed Gemini API response:\n{content}")

            # Simple parsing to extract title, description, and tags
            logger.info("Parsing content from Gemini API response")

            title = ""
            description = ""
            tags = []

            # Basic extraction with regex
            # First try with "Title:" format
            title_match = re.search(
                r"Title:\s*(.+?)(?:\n|Description:)", content, re.DOTALL
            )
            if title_match:
                title = title_match.group(1).strip()
                # Remove any ** markers
                title = re.sub(r"^\*\*\s*", "", title)
                title = re.sub(r"\s*\*\*$", "", title)
                logger.info(f"Extracted title: {title}")
            else:
                logger.warning("Failed to extract title from Gemini API response")

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
                        r"Description:\s*([\s\S]*?)\nTags:", content, re.DOTALL
                    )
                    if desc_match:
                        description = desc_match.group(1).strip()
            else:
                # If no Tags: section, use regex to capture until the end
                desc_match = re.search(
                    r"Description:\s*([\s\S]*?)$", content, re.DOTALL
                )
                if desc_match:
                    description = desc_match.group(1).strip()

            # Log the extracted description
            if description:
                logger.info(f"Extracted description with length: {len(description)}")
            else:
                logger.warning("Failed to extract description from Gemini API response")

            # Extract tags
            tags_match = re.search(r"Tags:\s*([\s\S]*?)$", content, re.DOTALL)
            if tags_match:
                tags_text = tags_match.group(1).strip()
                # Split by comma and clean up
                tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
                logger.info(f"Extracted {len(tags)} tags: {', '.join(tags)}")
            else:
                logger.warning("Failed to extract tags from Gemini API response")

            return {
                "title": title,
                "description": description,
                "tags": tags,
            }

        except Exception as e:
            logger.error(f"Error generating content from image: {e}")
            return {"title": "", "description": "", "tags": []}

    def analyze_image_with_prompt(self, image_path: str, prompt: str) -> str:
        """
        Analyze an image with a given prompt using Gemini API.

        Args:
            image_path: Path to the image file
            prompt: Text prompt for analysis

        Returns:
            Generated text response
        """
        if not GEMINI_AVAILABLE:
            logger.error(
                "Gemini API not available. Install with: pip install google-generativeai"
            )
            return ""

        if not self.gemini_model:
            logger.error("Gemini model not initialized")
            return ""

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return ""

        try:
            # Load the image
            img = Image.open(image_path)
            logger.info(f"Successfully loaded image: {image_path}")

            # Get the image file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            logger.info(f"Image file size: {file_size_mb:.2f} MB")

            # If image is too large, resize it
            max_size_mb = 3.5  # Maximum size in MB for reliable API calls
            if file_size_mb > max_size_mb:
                logger.info(
                    f"Image is large ({file_size_mb:.2f} MB), resizing for API call"
                )
                # Calculate new dimensions while maintaining aspect ratio
                max_dimension = 1500  # Maximum dimension in pixels
                if img.width > img.height:
                    new_width = min(img.width, max_dimension)
                    new_height = int(img.height * (new_width / img.width))
                else:
                    new_height = min(img.height, max_dimension)
                    new_width = int(img.width * (new_height / img.height))

                # Resize the image
                img = img.resize((new_width, new_height), Image.LANCZOS)
                logger.info(f"Resized image to {new_width}x{new_height} for API call")

            # Convert image to bytes for Gemini API
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=img.format or "PNG")
            img_bytes = img_byte_arr.getvalue()

            # Create the content parts
            parts = [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": f"image/{img.format.lower() if img.format else 'png'}",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    }
                },
            ]

            # Generate content
            response = self.gemini_model.generate_content(parts)

            # Check if the response is valid
            if not hasattr(response, "text"):
                logger.error(f"Invalid response from Gemini API: {response}")
                return ""

            # Get the raw response text and process it
            raw_content = response.text.strip()
            logger.info("Successfully received response from Gemini API")

            return process_ai_response(raw_content, is_thinking_model=False)

        except Exception as e:
            logger.error(f"Error analyzing image with prompt: {e}")
            return ""

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Gemini API.

        Args:
            prompt: Text prompt for generation

        Returns:
            Generated text response
        """
        if not GEMINI_AVAILABLE:
            logger.error(
                "Gemini API not available. Install with: pip install google-generativeai"
            )
            return ""

        if not self.gemini_model:
            logger.error("Gemini model not initialized")
            return ""

        try:
            # Generate content
            response = self.gemini_model.generate_content(prompt)

            # Check if the response is valid
            if not hasattr(response, "text"):
                logger.error(f"Invalid response from Gemini API: {response}")
                return ""

            # Get the raw response text and process it
            raw_content = response.text.strip()
            logger.info("Successfully received response from Gemini API")

            return process_ai_response(raw_content, is_thinking_model=False)

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
