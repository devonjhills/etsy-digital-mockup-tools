"""
Command-line interface for Etsy integration.
"""

import os
import sys
import argparse

from utils.common import setup_logging
from utils.env_loader import load_env_from_file
from etsy.main import EtsyIntegration
from etsy.constants import DEFAULT_ETSY_INSTRUCTIONS
from folder_renamer import process_input_directory

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the Etsy CLI.
    """
    parser = argparse.ArgumentParser(description="Etsy integration tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Etsy commands
    etsy_parser = subparsers.add_parser("etsy", help="Etsy integration commands")
    etsy_subparsers = etsy_parser.add_subparsers(
        dest="etsy_command", help="Etsy command to run"
    )

    # Auth command
    auth_parser = etsy_subparsers.add_parser("auth", help="Authenticate with Etsy")

    # Create listing command
    create_parser = etsy_subparsers.add_parser("create", help="Create an Etsy listing")
    create_parser.add_argument(
        "--folder", required=True, help="Path to the product folder"
    )
    create_parser.add_argument(
        "--product_type",
        required=True,
        choices=["pattern", "clipart", "wall_art", "brush_strokes"],
        help="Product type",
    )
    create_parser.add_argument("--name", help="Product name (defaults to folder name)")
    create_parser.add_argument(
        "--title", help="Custom title for the listing (optional)"
    )
    create_parser.add_argument(
        "--description", help="Custom description for the listing (optional)"
    )
    create_parser.add_argument(
        "--tags", help="Comma-separated list of tags for the listing (optional, max 13)"
    )
    create_parser.add_argument(
        "--draft",
        action="store_true",
        help="Create as draft instead of publishing immediately",
    )

    # Bulk create listings command
    bulk_create_parser = etsy_subparsers.add_parser(
        "bulk-create", help="Create Etsy listings for all subfolders in input directory"
    )
    bulk_create_parser.add_argument(
        "--input_dir",
        required=True,
        help="Path to the input directory containing product subfolders",
    )
    bulk_create_parser.add_argument(
        "--product_type",
        required=True,
        choices=["pattern", "clipart"],
        help="Product type (pattern or clipart)",
    )
    bulk_create_parser.add_argument(
        "--draft",
        action="store_true",
        help="Create listings as drafts instead of publishing immediately",
    )

    # Bulk prepare listings command
    bulk_prepare_parser = etsy_subparsers.add_parser(
        "bulk-prepare",
        help="Prepare Etsy listings for all subfolders without uploading",
    )
    bulk_prepare_parser.add_argument(
        "--input_dir",
        required=True,
        help="Path to the input directory containing product subfolders",
    )
    bulk_prepare_parser.add_argument(
        "--product_type",
        required=True,
        choices=["pattern", "clipart"],
        help="Product type (pattern or clipart)",
    )
    bulk_prepare_parser.add_argument(
        "--output_file",
        default="prepared_listings.json",
        help="Output file to save prepared listings data (default: prepared_listings.json)",
    )
    bulk_prepare_parser.add_argument(
        "--provider",
        choices=["gemini", "openrouter"],
        help="AI provider to use for content generation (overrides environment variable)",
    )

    # Generate content command
    generate_parser = etsy_subparsers.add_parser(
        "generate", help="Generate listing content from mockup image"
    )
    generate_parser.add_argument(
        "--folder", required=True, help="Path to the product folder"
    )
    generate_parser.add_argument(
        "--product_type",
        required=True,
        choices=["pattern", "clipart", "wall_art", "brush_strokes"],
        help="Product type",
    )
    generate_parser.add_argument(
        "--instructions",
        default=DEFAULT_ETSY_INSTRUCTIONS,
        help="Instructions for the LLM. By default, uses the standard instructions from etsy/constants.py",
    )

    # Template commands
    template_parser = subparsers.add_parser("template", help="Manage listing templates")

    args = parser.parse_args()

    # Load environment variables from .env file
    load_env_from_file()

    # Get API keys from environment variables
    etsy_api_key = os.environ.get("ETSY_API_KEY")
    etsy_api_secret = os.environ.get("ETSY_API_SECRET")

    # Get AI provider settings
    provider_type = os.environ.get("AI_PROVIDER")
    api_key = None
    model_name = None

    # If provider is specified, get the corresponding API key and model
    if provider_type == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        model_name = os.environ.get("GEMINI_MODEL")
        if api_key:
            logger.info(f"Using Gemini model: {model_name}")
    elif provider_type == "openrouter":
        api_key = os.environ.get("OPEN_ROUTER_API_KEY")
        model_name = os.environ.get("OPEN_ROUTER_MODEL")
        if api_key:
            logger.info(f"Using OpenRouter model: {model_name}")
    else:
        # Try to get API keys for available providers
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        openrouter_api_key = os.environ.get("OPEN_ROUTER_API_KEY")

        if gemini_api_key:
            provider_type = "gemini"
            api_key = gemini_api_key
            model_name = os.environ.get("GEMINI_MODEL")
            logger.info(f"Using Gemini model: {model_name}")
        elif openrouter_api_key:
            provider_type = "openrouter"
            api_key = openrouter_api_key
            model_name = os.environ.get("OPEN_ROUTER_MODEL")
            logger.info(f"Using OpenRouter model: {model_name}")
        else:
            logger.warning(
                "No AI provider API keys found in environment. Some features may not work."
            )

    # Log API key status (without revealing the full key)
    if etsy_api_key:
        masked_key = (
            etsy_api_key[:4] + "*" * (len(etsy_api_key) - 8) + etsy_api_key[-4:]
        )
        logger.info(f"Using Etsy API key: {masked_key}")

    if not etsy_api_key or not etsy_api_secret:
        logger.error(
            "Etsy API key and secret are required. Set ETSY_API_KEY and ETSY_API_SECRET environment variables."
        )
        sys.exit(1)

    # Initialize Etsy integration
    etsy = EtsyIntegration(
        etsy_api_key=etsy_api_key,
        etsy_api_secret=etsy_api_secret,
        api_key=api_key,
        model_name=model_name,
        provider_type=provider_type,
    )

    if args.command == "etsy":
        # Handle Etsy commands
        if not hasattr(args, "etsy_command") or not args.etsy_command:
            # No etsy command specified
            etsy_parser.print_help()
            sys.exit(1)

        if args.etsy_command == "auth":
            # Authenticate with Etsy
            if etsy.authenticate():
                logger.info("Authentication successful.")
            else:
                logger.error("Authentication failed.")
                sys.exit(1)

        elif args.etsy_command == "create":
            # Authenticate with Etsy
            if not etsy.authenticate():
                logger.error("Authentication failed.")
                sys.exit(1)

            # Create a listing
            listing = etsy.create_listing_from_folder(
                folder_path=args.folder,
                product_type=args.product_type,
                product_name=args.name,
                custom_title=args.title,
                custom_description=args.description,
                custom_tags=args.tags.split(",") if args.tags else None,
                is_draft=args.draft,
            )

            if listing:
                logger.info(f"Listing created: {listing.get('listing_id')}")
                logger.info(
                    f"URL: https://www.etsy.com/listing/{listing.get('listing_id')}"
                )
            else:
                logger.error("Failed to create listing.")
                sys.exit(1)

        elif args.etsy_command == "bulk-create":
            # Authenticate with Etsy
            if not etsy.authenticate():
                logger.error("Authentication failed.")
                sys.exit(1)

            # Validate input directory
            if not os.path.exists(args.input_dir) or not os.path.isdir(args.input_dir):
                logger.error(f"Input directory not found: {args.input_dir}")
                sys.exit(1)

            # Step 0: Rename folders based on AI image analysis
            logger.info("Step 0: Renaming folders based on AI image analysis...")
            if api_key:
                process_input_directory(
                    input_dir=args.input_dir,
                    provider_type=provider_type,
                    api_key=api_key,
                    model_name=model_name,
                )
            else:
                logger.warning(
                    "No AI provider API key found in environment variables. Skipping folder renaming."
                )

            # Create listings in bulk
            logger.info(
                f"Starting bulk creation of listings for {args.product_type} in {args.input_dir}"
            )
            listings = etsy.create_listings_bulk(
                input_dir=args.input_dir,
                product_type=args.product_type,
                is_draft=args.draft,
            )

            # Log results
            if listings:
                logger.info(f"Successfully created {len(listings)} listings:")
                for listing in listings:
                    logger.info(
                        f"  - {listing.get('title')}: https://www.etsy.com/listing/{listing.get('listing_id')}"
                    )
            else:
                logger.error("Failed to create any listings.")
                sys.exit(1)

        elif args.etsy_command == "bulk-prepare":
            # Validate input directory
            if not os.path.exists(args.input_dir) or not os.path.isdir(args.input_dir):
                logger.error(f"Input directory not found: {args.input_dir}")
                sys.exit(1)

            # Override provider if specified in command line
            command_provider_type = provider_type
            command_api_key = api_key
            command_model_name = model_name

            if hasattr(args, "provider") and args.provider:
                command_provider_type = args.provider
                if args.provider == "gemini":
                    command_api_key = os.environ.get("GEMINI_API_KEY")
                    command_model_name = os.environ.get("GEMINI_MODEL")
                    if command_api_key:
                        logger.info(f"Using Gemini model: {command_model_name}")
                elif args.provider == "openrouter":
                    command_api_key = os.environ.get("OPEN_ROUTER_API_KEY")
                    command_model_name = os.environ.get("OPEN_ROUTER_MODEL")
                    if command_api_key:
                        logger.info(f"Using OpenRouter model: {command_model_name}")

            # Step 0: Rename folders based on AI image analysis
            logger.info("Step 0: Renaming folders based on AI image analysis...")
            if command_api_key:
                process_input_directory(
                    input_dir=args.input_dir,
                    provider_type=command_provider_type,
                    api_key=command_api_key,
                    model_name=command_model_name,
                )
            else:
                logger.warning(
                    "No AI provider API key found in environment variables. Skipping folder renaming."
                )

            # Prepare listings in bulk
            logger.info(
                f"Starting bulk preparation of listings for {args.product_type} in {args.input_dir}"
            )

            # Update the EtsyIntegration instance with the new provider if specified
            if hasattr(args, "provider") and args.provider:
                # Create a new EtsyIntegration instance with the specified provider
                etsy = EtsyIntegration(
                    etsy_api_key=etsy_api_key,
                    etsy_api_secret=etsy_api_secret,
                    api_key=command_api_key,
                    model_name=command_model_name,
                    provider_type=command_provider_type,
                )
                logger.info(
                    f"Updated EtsyIntegration to use provider: {command_provider_type}"
                )

            prepared_listings = etsy.prepare_bulk_listings(
                input_dir=args.input_dir,
                product_type=args.product_type,
            )

            # Save prepared listings to file
            if prepared_listings:
                import json

                try:
                    # Convert file paths to relative paths for better portability
                    for listing in prepared_listings:
                        # Convert mockup_images to relative paths
                        listing["mockup_images_rel"] = [
                            os.path.relpath(img)
                            for img in listing.get("mockup_images", [])
                        ]
                        # Convert zip_files to relative paths
                        listing["zip_files_rel"] = [
                            os.path.relpath(zip_file)
                            for zip_file in listing.get("zip_files", [])
                        ]

                    # Save to file
                    with open(args.output_file, "w") as f:
                        json.dump(prepared_listings, f, indent=2)

                    logger.info(
                        f"Successfully prepared {len(prepared_listings)} listings:"
                    )
                    for listing in prepared_listings:
                        logger.info(f"  - {listing['folder_name']}: {listing['title']}")
                    logger.info(f"Prepared listings saved to {args.output_file}")
                except Exception as e:
                    logger.error(f"Error saving prepared listings to file: {e}")
                    sys.exit(1)
            else:
                logger.error("Failed to prepare any listings.")
                sys.exit(1)

        elif args.etsy_command == "generate":
            # Check if folder exists
            if not os.path.exists(args.folder):
                logger.error(f"Folder not found: {args.folder}")
                sys.exit(1)

            # Generate content from mockup
            instructions = (
                args.instructions
                if hasattr(args, "instructions")
                else "Analyze this mockup image and generate content for an Etsy listing. The image shows a digital product that will be sold on Etsy."
            )
            content = etsy.generate_content_from_mockup(
                folder_path=args.folder,
                product_type=args.product_type,
                instructions=instructions,
            )

            if content and content["title"]:
                logger.info("\nGenerated content:")
                logger.info(f"\nTitle: {content['title']}")
                logger.info(f"\nDescription:\n{content['description']}")
                logger.info(f"\nTags: {', '.join(content['tags'])}")
            else:
                logger.error("Failed to generate content from mockup.")
                sys.exit(1)

        else:
            # Unknown etsy command
            logger.error(f"Unknown etsy command: {args.etsy_command}")
            etsy_parser.print_help()
            sys.exit(1)

    elif args.command == "template":
        if args.template_command == "list":
            # List templates
            templates = etsy.templates.list_templates()

            if templates:
                logger.info("Available templates:")
                for template in templates:
                    logger.info(f"  - {template}")
            else:
                logger.info("No templates found.")

        elif args.template_command == "create-defaults":
            # Create default templates
            if etsy.templates.create_default_templates():
                logger.info("Default templates created.")
            else:
                logger.error("Failed to create default templates.")
                sys.exit(1)

        else:
            template_parser.print_help()
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
