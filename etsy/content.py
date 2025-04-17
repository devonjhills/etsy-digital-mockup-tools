"""
Module for generating listing content with SEO optimization.
"""

import os
import re
import sys
from typing import Dict, Any, Optional
from PIL import Image

# Set up logging
from utils.common import setup_logging

logger = setup_logging(__name__)

# Import AI provider factory
from ai_providers.factory import AIProviderFactory


class ContentGenerator:
    """Generate listing content with SEO optimization."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider_type: str = None,
    ):
        """
        Initialize the content generator.

        Args:
            api_key: API key for the AI provider (if None, will try to get from environment)
            model_name: Name of the model to use (if None, will try to get from environment)
            provider_type: Type of AI provider to use (only 'gemini' is supported)
        """
        # Get the AI provider
        if provider_type:
            self.provider = AIProviderFactory.create_provider(
                provider_type, api_key, model_name
            )
        else:
            self.provider = AIProviderFactory.get_default_provider()

        if self.provider:
            logger.info(
                f"Initialized AI provider: {self.provider.__class__.__name__} with model: {self.provider.model_name}"
            )
        else:
            logger.error(
                "Failed to initialize AI provider. Check API keys and provider type."
            )
            print(
                "Failed to initialize AI provider. Check API keys and provider type.",
                file=sys.stderr,
            )

    # Custom functions for generating title, description, and tags have been removed
    # We now rely entirely on the instructions passed to the Gemini API

    def generate_content_from_image(
        self, image_path: str, instructions: str
    ) -> Dict[str, Any]:
        """
        Generate listing content (title, description, tags) from an image.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the AI

        Returns:
            Dictionary with title, description, and tags
        """
        if not os.path.exists(image_path):
            error_msg = f"Image file not found: {image_path}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        if not self.provider:
            error_msg = "AI provider not available. Check initialization."
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        try:
            # Add a strong note about avoiding markdown formatting
            prompt = instructions + (
                "\n\nIMPORTANT: Etsy only supports plain text in listings. DO NOT use any markdown formatting in your response. "
                "This means no asterisks for bold, no hashtags for headings, no hyphens or asterisks for bullet points, "
                "no backticks for code formatting, and no other markdown syntax. "
                "Provide all content as plain text only. Etsy will display your text exactly as provided."
            )

            # Generate content using the provider
            content_result = self.provider.generate_content_from_image(
                image_path, prompt
            )

            # If the provider returned a valid result, use it
            if (
                content_result
                and "title" in content_result
                and "description" in content_result
                and "tags" in content_result
            ):
                title = content_result["title"]
                description = content_result["description"]
                tags = content_result["tags"]

                # Log what we extracted
                logger.info(f"Extracted title: {title}")
                logger.info(f"Extracted description length: {len(description)}")
                logger.info(f"Extracted tags count: {len(tags)}")

                # Final cleanup to ensure all content is plain text
                def ensure_plain_text(text):
                    # Remove any remaining markdown formatting
                    text = re.sub(r"\*\*|\*|#|`|\[|\]|\(|\)|_", "", text)
                    # Remove any HTML tags
                    text = re.sub(r"<[^>]*>", "", text)
                    # Normalize whitespace
                    text = re.sub(r"\s+", " ", text).strip()
                    return text

                title = ensure_plain_text(title)
                description = description.replace(
                    "\n\n", "\n"
                )  # Preserve line breaks but remove excessive ones
                tags = [ensure_plain_text(tag) for tag in tags]

                return {"title": title, "description": description, "tags": tags}
            else:
                logger.error("AI provider returned invalid content format")
                return {"title": "", "description": "", "tags": []}

        except Exception as e:
            logger.error(f"Error generating content from image: {e}")
            print(f"Error generating content from image: {e}", file=sys.stderr)
            return {"title": "", "description": "", "tags": []}
