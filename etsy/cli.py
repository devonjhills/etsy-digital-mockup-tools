"""
Command-line interface for Etsy integration.
"""
import os
import sys
import argparse

from utils.common import setup_logging
from etsy.main import EtsyIntegration

# Set up logging
logger = setup_logging(__name__)

def main():
    """
    Main entry point for the Etsy CLI.
    """
    parser = argparse.ArgumentParser(description="Etsy integration tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Authenticate with Etsy")
    
    # Create listing command
    create_parser = subparsers.add_parser("create", help="Create an Etsy listing")
    create_parser.add_argument(
        "--folder", 
        required=True,
        help="Path to the product folder"
    )
    create_parser.add_argument(
        "--product_type", 
        required=True,
        choices=["pattern", "clipart", "wall_art", "brush_strokes"],
        help="Product type"
    )
    create_parser.add_argument(
        "--name", 
        help="Product name (defaults to folder name)"
    )
    create_parser.add_argument(
        "--draft", 
        action="store_true",
        help="Create as draft instead of publishing immediately"
    )
    
    # Bulk create command
    bulk_create_parser = subparsers.add_parser("bulk-create", help="Create multiple Etsy listings from a CSV file")
    bulk_create_parser.add_argument(
        "--csv", 
        required=True,
        help="Path to the CSV file"
    )
    bulk_create_parser.add_argument(
        "--image_base_dir", 
        default="input",
        help="Base directory for images"
    )
    bulk_create_parser.add_argument(
        "--draft", 
        action="store_true",
        help="Create as draft instead of publishing immediately"
    )
    
    # Bulk update command
    bulk_update_parser = subparsers.add_parser("bulk-update", help="Update multiple Etsy listings from a CSV file")
    bulk_update_parser.add_argument(
        "--csv", 
        required=True,
        help="Path to the CSV file"
    )
    
    # Create CSV template command
    csv_template_parser = subparsers.add_parser("csv-template", help="Create a CSV template for bulk operations")
    csv_template_parser.add_argument(
        "--output", 
        required=True,
        help="Path to the output file"
    )
    csv_template_parser.add_argument(
        "--operation", 
        choices=["create", "update"],
        default="create",
        help="Operation type"
    )
    
    # Template commands
    template_parser = subparsers.add_parser("template", help="Manage listing templates")
    template_subparsers = template_parser.add_subparsers(dest="template_command", help="Template command to run")
    
    # List templates command
    template_list_parser = template_subparsers.add_parser("list", help="List available templates")
    
    # Create default templates command
    template_create_defaults_parser = template_subparsers.add_parser("create-defaults", help="Create default templates")
    
    args = parser.parse_args()
    
    # Get API keys from environment variables
    etsy_api_key = os.environ.get("ETSY_API_KEY")
    etsy_api_secret = os.environ.get("ETSY_API_SECRET")
    llm_api_key = os.environ.get("LLM_API_KEY")
    llm_api_url = os.environ.get("LLM_API_URL")
    
    if not etsy_api_key or not etsy_api_secret:
        logger.error("Etsy API key and secret are required. Set ETSY_API_KEY and ETSY_API_SECRET environment variables.")
        sys.exit(1)
    
    # Initialize Etsy integration
    etsy = EtsyIntegration(
        etsy_api_key=etsy_api_key,
        etsy_api_secret=etsy_api_secret,
        llm_api_key=llm_api_key,
        llm_api_url=llm_api_url
    )
    
    if args.command == "auth":
        # Authenticate with Etsy
        if etsy.authenticate():
            logger.info("Authentication successful.")
        else:
            logger.error("Authentication failed.")
            sys.exit(1)
    
    elif args.command == "create":
        # Authenticate with Etsy
        if not etsy.authenticate():
            logger.error("Authentication failed.")
            sys.exit(1)
        
        # Create a listing
        listing = etsy.create_listing_from_folder(
            folder_path=args.folder,
            product_type=args.product_type,
            product_name=args.name,
            is_draft=args.draft
        )
        
        if listing:
            logger.info(f"Listing created: {listing.get('listing_id')}")
            logger.info(f"URL: https://www.etsy.com/listing/{listing.get('listing_id')}")
        else:
            logger.error("Failed to create listing.")
            sys.exit(1)
    
    elif args.command == "bulk-create":
        # Authenticate with Etsy
        if not etsy.authenticate():
            logger.error("Authentication failed.")
            sys.exit(1)
        
        # Create listings from CSV
        success_count, error_count, error_messages = etsy.bulk.create_listings_from_csv(
            csv_file=args.csv,
            image_base_dir=args.image_base_dir,
            is_draft=args.draft
        )
        
        logger.info(f"Bulk create completed: {success_count} successful, {error_count} failed")
        
        if error_count > 0:
            logger.info("Errors:")
            for error in error_messages:
                logger.info(f"  - {error}")
    
    elif args.command == "bulk-update":
        # Authenticate with Etsy
        if not etsy.authenticate():
            logger.error("Authentication failed.")
            sys.exit(1)
        
        # Update listings from CSV
        success_count, error_count, error_messages = etsy.bulk.update_listings_from_csv(
            csv_file=args.csv
        )
        
        logger.info(f"Bulk update completed: {success_count} successful, {error_count} failed")
        
        if error_count > 0:
            logger.info("Errors:")
            for error in error_messages:
                logger.info(f"  - {error}")
    
    elif args.command == "csv-template":
        # Create CSV template
        if etsy.bulk.create_csv_template(
            output_file=args.output,
            operation=args.operation
        ):
            logger.info(f"CSV template created: {args.output}")
        else:
            logger.error("Failed to create CSV template.")
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
