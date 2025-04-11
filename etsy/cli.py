"""
Command-line interface for Etsy integration.
"""

import os
import sys
import argparse

from utils.common import setup_logging
from utils.env_loader import load_env_from_file
from etsy.main import EtsyIntegration

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
        default="""Instruction: Before generating the listing components, perform a quick analysis of current, popular Etsy listings for products visually similar to the one in the provided image. Identify common keywords, effective structures, and potential weaknesses in those top listings. Use these insights and advanced SEO outranking strategies to create a Title, Description, and Tags for the provided product image that are optimized to potentially outperform existing popular listings in Etsy search.

Context: You are a sophisticated E-commerce Copywriter and Etsy SEO Strategist. Your expertise lies in analyzing product visuals and translating them into high-converting Etsy listings. You understand modern e-commerce search algorithms (like Etsy's 2025 predicted direction), focusing on user intent, semantic search, visual appeal, and listing quality factors. Your goal is to create a complete, optimized Etsy listing (Title, Description, Tags) based solely on the provided product image.
Input Requirements:
1. Analyze Product Image: You will be provided with a single Etsy listing image. Analyze this image thoroughly to identify:
    * Product Type: What is the product? (e.g., clip art, wall art, pattern set, etc.)
    * Core Subject/Theme: What is depicted, or what is the central concept or design element?
    * Style/Aesthetics: Describe the visual style (e.g., vintage, modern, minimalist, boho chic, watercolor, cartoonish, realistic, rustic, kawaii, gothic, etc).
    * Key Features/Details: Note any specific characteristics clearly visible or strongly implied
2. Infer Target Audience & Use Cases: Based only on the product identified in the image and its visual cues, deduce the likely target audience(s) (e.g., gift shoppers, DIY crafters, home decorators, fashion enthusiasts, specific hobbyists, parents, teachers) and primary applications/uses (e.g., home decor, apparel, gift-giving, crafting project, personal accessory, party supplies, digital design asset, journaling).
Output Structure: Generate the following components in this exact order and format:
Title (Target: 130-140 characters):
* Prioritize Clarity & Relevance: Start with the most important, customer-centric keywords describing the core product type, subject, and style identified from the image. Clearly state what the product is.
* Natural Language Longtail Keywords: Structure keywords to mimic real buyer searches. Seamlessly integrate multiple related longtail phrases (aim for ~6-8 keyword combinations relevant to the product).
* Focus on Solutions/Applications: Weave in terms related to how the product can be used or the benefit it provides, as inferred from the visual context (e.g., 'Wall Decor Print', 'Unique Coffee Mug', 'DIY Craft Kit', 'Funny T-shirt Gift', 'Boho Chic Accessory').
* Readability: Create a title that flows naturally without excessive punctuation or keyword stuffing. Avoid special characters.
* Efficiency: Aim for full character count utilization for maximum keyword exposure. Use singular/plural forms based on common search patterns for that specific product type.
* Accuracy: Ensure the title accurately reflects the product shown in the image.
Description:
* Hook with Benefits: Start immediately with a compelling sentence highlighting the primary benefit or appeal of the product based on its visual presentation.
* Structured & Scannable: Use clear paragraphs with emoji-prefixed headings (choose relevant emojis based on the product):
    * ✨ Product Highlights: Detail the key features and specifics inferred directly from the image or typically associated with this product type if clearly suggested.
    * 💡 Perfect For: List diverse potential applications, uses, or recipient ideas identified using bullet points. Use this specific emoji for list items: 🔘
    * ✅ What You Receive / Format: Explain the likely format based on visual cues. (e.g., "Instant Digital Download: Get your high-resolution file(s) immediately after purchase!"
    * 📝 Disclaimer: At the very end of the generated description add a disclaimer saying that all images were designed by me and brought to life with the assistance of ai tools.
* Readability & Tone: Maintain a Flesch Reading Ease score of 70+. Use clear, concise language and active voice. Avoid jargon. Keep the tone appropriate for the product's style (e.g., playful, elegant, professional, cozy) but always helpful and inspiring.
* Keyword Integration: Naturally weave primary and secondary keywords (including inferred synonyms like 'artwork', 'gift idea', 'home accessory', 'craft supply', 'clothing item', 'digital asset') throughout the description, mirroring conversational language and reflecting the image content.
Tags (Exactly 13):
* Format: Provide as a comma-separated list. Each tag must be under 20 characters.
* Longtail & Specific: Prioritize multi-word phrases (2-3+ words often best) that are highly relevant to the specific product's style, subject, type, and likely uses as seen in the image.
* Diverse Angles: Cover various search approaches based on the visual analysis:
    * Style/Aesthetic (e.g., Boho Wall Art, Minimalist Jewelry)
    * Subject/Theme (e.g., Cat Lover Gift, Floral Pattern)
    * Product Type (e.g., Ceramic Coffee Mug, Printable Planner, Crochet Pattern PDF)
    * Use Case/Occasion (e.g., Nursery Decor, Birthday Gift Idea, Office Accessory)
    * Target Audience (e.g., Gifts for Her, Teacher Present, Crafter Supply)
    * Materials/Format (if clear) (e.g., Wooden Sign Art, SVG Cutting File, Linen Pillow Case)
    * Problem/Solution/Benefit (e.g., Unique Home Decor, Easy Craft Project)
* Avoid Redundancy (where possible): While some overlap with the title is okay, try to introduce new relevant terms or variations drawn from the image.
* No Single Words: Avoid highly competitive single-word tags (e.g., "art", "gift", "mug", "shirt", "digital").
* Natural Language: Use phrases buyers actually type. Use singular/plural based on common searches for that product.
* Image-Derived: All tags MUST be directly relevant to the product depicted in the provided image.
Core SEO Philosophy (Internal Checklist for You):
* Emulate Modern Etsy Search: Focus on semantic understanding, user intent signals, and overall listing quality derived from visual appeal and accurate description.
* Outrank Competitors: Actively use insights from popular listings to improve keyword targeting, clarity, and appeal.
* Solve Buyer Problems/Needs: Frame the listing around the purpose, application, or aesthetic appeal of the product shown. Why does someone need this? What will it enhance?
* Target High-Intent Keywords: Use phrases indicating a buyer is looking for a specific item like the one pictured.
* Niche Down: Leverage specific style, subject, and use-case keywords apparent from the image to attract the right buyers.
* Optimize for Conversion: Create clear, compelling copy inspired by the visual that encourages clicks and purchases.
Required Output Format:
Title: [Generated Title following guidelines]
Description: [Generated Description following guidelines and structure]
Tags: [tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10, tag11, tag12, tag13]""",
        help="Instructions for the LLM",
    )

    # Template commands
    template_parser = subparsers.add_parser("template", help="Manage listing templates")

    args = parser.parse_args()

    # Load environment variables from .env file
    load_env_from_file()

    # Get API keys from environment variables
    etsy_api_key = os.environ.get("ETSY_API_KEY")
    etsy_api_secret = os.environ.get("ETSY_API_SECRET")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")

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

    if gemini_api_key:
        logger.info(f"Using Gemini model: {gemini_model}")
    else:
        logger.warning(
            "GEMINI_API_KEY not found in environment. Some features may not work."
        )

    # Initialize Etsy integration
    etsy = EtsyIntegration(
        etsy_api_key=etsy_api_key,
        etsy_api_secret=etsy_api_secret,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
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

            # Prepare listings in bulk
            logger.info(
                f"Starting bulk preparation of listings for {args.product_type} in {args.input_dir}"
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
