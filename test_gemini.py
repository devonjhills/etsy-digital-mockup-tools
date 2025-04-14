#!/usr/bin/env python3
"""
Test script for Gemini API integration.
"""

import os
import sys
import argparse
from utils.common import setup_logging
from utils.env_loader import load_env_from_file
from etsy.content import ContentGenerator, GEMINI_AVAILABLE
from etsy.constants import DEFAULT_ETSY_INSTRUCTIONS

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the test script.
    """
    parser = argparse.ArgumentParser(description="Test Gemini API integration")
    parser.add_argument(
        "--image", required=True, help="Path to the image file to analyze"
    )
    parser.add_argument(
        "--instructions",
        default="Analyze this image and describe what you see. This is a digital product that will be sold on Etsy. IMPORTANT: Etsy only supports plain text in listings, so do not use any markdown formatting in your response.",
        help="Instructions for the LLM",
    )
    parser.add_argument(
        "--use-default-instructions",
        action="store_true",
        help="Use the default Etsy instructions from constants.py instead of the simple instructions",
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    load_env_from_file()

    # Get Gemini API key from environment
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if not gemini_api_key:
        logger.error(
            "Gemini API key not found. Set GEMINI_API_KEY environment variable."
        )
        sys.exit(1)

    if not GEMINI_AVAILABLE:
        logger.error(
            "Google Generative AI package not found. Install with: pip install google-generativeai"
        )
        sys.exit(1)

    # Get model name from environment or use default
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
    logger.info(f"Using Gemini model: {gemini_model}")

    # Initialize content generator
    content_generator = ContentGenerator(
        api_key=gemini_api_key, model_name=gemini_model
    )

    # Determine which instructions to use
    instructions = (
        DEFAULT_ETSY_INSTRUCTIONS
        if args.use_default_instructions
        else args.instructions
    )
    logger.info(
        f"Using {'default' if args.use_default_instructions else 'custom'} instructions"
    )

    # Generate content from image
    content = content_generator.generate_content_from_image(
        image_path=args.image,
        instructions=instructions,
    )

    if content and content["title"]:
        logger.info("\nGenerated content:")
        logger.info(f"\nTitle: {content['title']}")
        logger.info(f"\nDescription:\n{content['description']}")
        logger.info(f"\nTags: {', '.join(content['tags'])}")
    else:
        logger.error("Failed to generate content from image.")
        sys.exit(1)


if __name__ == "__main__":
    main()
