"""
Gemini AI provider implementation.
"""

import os
import base64
import re
import io
import time
from typing import Optional, Dict, Any
from PIL import Image

from .base import AIProvider

# Set up logging
from utils.common import setup_logging
from utils.ai_utils import process_ai_response

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

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
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

    def generate_title_from_image(
        self, image_path: str, max_retries: int = 2
    ) -> Optional[str]:
        """
        Generate a title from an image using Gemini API.

        Args:
            image_path: Path to the image file
            max_retries: Maximum number of retries on failure

        Returns:
            A title or None if generation failed
        """
        if not GEMINI_AVAILABLE:
            logger.error(
                "Gemini API not available. Install with: pip install google-generativeai"
            )
            return None

        if not self.gemini_model:
            logger.error("Gemini model not initialized")
            return None

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None

        # Get the image file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        logger.info(f"Image file size: {file_size_mb:.2f} MB")

        # If the image is too large, resize it to reduce API errors
        max_size_mb = 3.5  # Maximum size in MB for reliable API calls
        img = None

        try:
            # Load the image
            img = Image.open(image_path)
            logger.info(
                f"Image dimensions: {img.width}x{img.height}, format: {img.format}"
            )

            # If image is too large, resize it
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
        except Exception as e:
            logger.error(f"Error loading or resizing image {image_path}: {e}")
            return None

        # Try multiple times with increasing timeouts
        for attempt in range(max_retries + 1):
            try:
                # Convert image to bytes for Gemini API
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format=img.format or "PNG")
                img_bytes = img_byte_arr.getvalue()

                # Create the prompt - simplified for more reliable results
                prompt = "Generate a concise 2-3 word title for this image. Use title case (capitalize each word). ONLY return the title, nothing else."

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

                # Log attempt information
                logger.info(
                    f"Attempt {attempt + 1}/{max_retries + 1} to generate title"
                )

                # Generate content
                start_time = time.time()
                response = self.gemini_model.generate_content(parts)
                elapsed_time = time.time() - start_time
                logger.info(f"API call completed in {elapsed_time:.2f} seconds")

                # Check if the response is valid
                if not hasattr(response, "text"):
                    logger.error(f"Invalid response from Gemini API: {response}")
                    if attempt < max_retries:
                        logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                        continue
                    return None

                # Get the raw response text
                raw_response = response.text.strip()

                # Process the response using our centralized utility function
                # Gemini doesn't have thinking models, so we set is_thinking_model to False
                title = process_ai_response(raw_response, is_thinking_model=False)

                logger.info(f"Generated title: {title}")
                return title

            except Exception as e:
                logger.error(f"Error generating title with Gemini API: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                    # Wait before retrying
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                else:
                    return None

        # If we get here, all retries failed
        return None

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

            # Extract description
            desc_match = re.search(
                r"Description:\s*([\s\S]+?)(?:\n\s*Tags:|$)", content, re.DOTALL
            )
            if desc_match:
                description = desc_match.group(1).strip()
                logger.info(f"Extracted description with length: {len(description)}")
            else:
                logger.warning("Failed to extract description from Gemini API response")

            # Extract tags
            tags_match = re.search(
                r"Tags:\s*(.+?)(?:\n\d{4}-\d{2}-\d{2}|$)", content, re.DOTALL
            )
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
