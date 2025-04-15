#!/usr/bin/env python3
"""
Test script for setting Etsy listing attributes.
"""

import os
import sys
import logging
import dotenv
from etsy.main import EtsyIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
    datefmt="%I:%M:%S %p",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Load environment variables
dotenv.load_dotenv()

# Get API keys from environment
ETSY_API_KEY = os.environ.get("ETSY_API_KEY")
ETSY_API_SECRET = os.environ.get("ETSY_API_SECRET")

if not ETSY_API_KEY or not ETSY_API_SECRET:
    logger.error("Error: ETSY_API_KEY and ETSY_API_SECRET must be set in .env file")
    sys.exit(1)


def main():
    """Main function."""
    # Initialize Etsy integration
    etsy = EtsyIntegration(etsy_api_key=ETSY_API_KEY, etsy_api_secret=ETSY_API_SECRET)

    # Authenticate with Etsy
    if not etsy.authenticate():
        logger.error("Authentication failed.")
        sys.exit(1)

    # Get folder path from command line
    if len(sys.argv) < 3:
        logger.error("Usage: python test_attributes.py <folder_path> <product_type>")
        logger.error("Example: python test_attributes.py input/my_pattern pattern")
        sys.exit(1)

    folder_path = sys.argv[1]
    product_type = sys.argv[2]

    logger.info(
        f"Creating listing from folder: {folder_path} with product type: {product_type}"
    )

    # Create a listing with attributes
    listing = etsy.create_listing_from_folder(
        folder_path=folder_path,
        product_type=product_type,
        is_draft=True,  # Create as draft to avoid publishing test listings
    )

    if listing:
        logger.info(f"Listing created: {listing.get('listing_id')}")
        logger.info(f"URL: https://www.etsy.com/listing/{listing.get('listing_id')}")

        # Test setting attributes directly
        logger.info("Testing direct attribute setting...")
        attributes = {
            "craft_types": ["Scrapbooking", "Card Making & Stationery"],
            "primary_color": "Blue",
            "length": 12,
            "width": 12,
        }

        result = etsy.listings.set_listing_attributes(
            listing_id=listing.get("listing_id"),
            product_type=product_type,
            attributes=attributes,
        )

        if result:
            logger.info("Successfully set attributes directly.")
        else:
            logger.warning("Failed to set attributes directly.")
    else:
        logger.error("Failed to create listing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
