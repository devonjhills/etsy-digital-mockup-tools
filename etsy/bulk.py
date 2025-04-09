"""
Module for bulk operations on Etsy listings.
"""

import os
import csv
import json
from typing import Dict, List, Optional, Any, Tuple
import time
import glob

from utils.common import setup_logging
from etsy.auth import EtsyAuth
from etsy.listings import EtsyListings
from etsy.templates import ListingTemplate
from etsy.content import ContentGenerator

# Set up logging
logger = setup_logging(__name__)


class BulkOperations:
    """Perform bulk operations on Etsy listings."""

    def __init__(
        self,
        auth: EtsyAuth,
        listings: EtsyListings,
        templates: ListingTemplate,
        content_generator: Optional[ContentGenerator] = None,
    ):
        """
        Initialize the bulk operations handler.

        Args:
            auth: Etsy authentication handler
            listings: Etsy listings handler
            templates: Listing template handler
            content_generator: Content generator (optional)
        """
        self.auth = auth
        self.listings = listings
        self.templates = templates
        self.content_generator = content_generator

    def create_listings_from_csv(
        self, csv_file: str, image_base_dir: str = "input", is_draft: bool = False
    ) -> Tuple[int, int, List[str]]:
        """
        Create listings from a CSV file.

        Args:
            csv_file: Path to the CSV file
            image_base_dir: Base directory for images
            is_draft: Whether to create listings as drafts

        Returns:
            Tuple of (success_count, error_count, error_messages)
        """
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return 0, 1, [f"CSV file not found: {csv_file}"]

        success_count = 0
        error_count = 0
        error_messages = []

        try:
            with open(csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(
                    reader, start=2
                ):  # Start at 2 to account for header row
                    try:
                        # Get required fields
                        product_type = row.get("product_type", "").strip()
                        product_name = row.get("name", "").strip()
                        folder_path = row.get("folder_path", "").strip()

                        if not product_type or not product_name or not folder_path:
                            error_message = f"Row {row_num}: Missing required fields (product_type, name, folder_path)"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Get full folder path
                        full_folder_path = os.path.join(image_base_dir, folder_path)
                        if not os.path.exists(full_folder_path):
                            error_message = (
                                f"Row {row_num}: Folder not found: {full_folder_path}"
                            )
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Get template
                        template = self.templates.get_template_for_product_type(
                            product_type
                        )
                        if not template:
                            error_message = f"Row {row_num}: Template not found for product type: {product_type}"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Get shipping profile ID
                        shipping_profile_id = row.get("shipping_profile_id")
                        if not shipping_profile_id:
                            # Get shipping profiles
                            shipping_profiles = self.listings.get_shipping_profiles()
                            if shipping_profiles:
                                # Find a digital shipping profile
                                for profile in shipping_profiles:
                                    if profile.get("type") == "digital":
                                        shipping_profile_id = profile.get(
                                            "shipping_profile_id"
                                        )
                                        break

                        if not shipping_profile_id:
                            error_message = f"Row {row_num}: No shipping profile ID provided or found"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Get taxonomy ID
                        taxonomy_id = row.get("taxonomy_id") or template.get(
                            "taxonomy_id"
                        )
                        if not taxonomy_id:
                            error_message = f"Row {row_num}: No taxonomy ID provided or found in template"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Prepare product info
                        product_info = {
                            "name": product_name,
                            "folder_path": full_folder_path,
                            "product_type": product_type,
                        }

                        # Add additional fields from the CSV
                        for key, value in row.items():
                            if key not in product_info and value:
                                product_info[key] = value

                        # Generate content if content generator is available
                        title = row.get("title", "").strip()
                        description = row.get("description", "").strip()
                        tags = (
                            row.get("tags", "").strip().split(",")
                            if row.get("tags")
                            else []
                        )

                        if self.content_generator:
                            if not title:
                                title = self.content_generator.generate_title(
                                    product_info, template
                                )

                            if not description:
                                description = (
                                    self.content_generator.generate_description(
                                        product_info, template
                                    )
                                )

                            if not tags:
                                tags = self.content_generator.generate_tags(
                                    product_info, template
                                )
                        else:
                            # Use template with basic substitution
                            if not title:
                                title_template = template.get(
                                    "title_template", "{name}"
                                )
                                title = title_template.format(
                                    name=product_name, **product_info
                                )

                            if not description:
                                description_template = template.get(
                                    "description_template",
                                    "# {name}\n\nDigital product for download.",
                                )
                                description = description_template.format(
                                    name=product_name, **product_info
                                )

                            if not tags:
                                tags = template.get("tags", [])[:13]

                        # Get materials
                        materials = (
                            row.get("materials", "").strip().split(",")
                            if row.get("materials")
                            else template.get("materials", [])
                        )

                        # Get price
                        price = float(row.get("price", 0)) or float(
                            template.get("price", 4.99)
                        )

                        # Get quantity
                        quantity = int(row.get("quantity", 0)) or int(
                            template.get("quantity", 999)
                        )

                        # Get other fields
                        who_made = row.get("who_made") or template.get(
                            "who_made", "i_did"
                        )
                        is_supply = (
                            row.get("is_supply", "").lower() == "true"
                            if row.get("is_supply")
                            else template.get("is_supply", False)
                        )
                        when_made = row.get("when_made") or template.get(
                            "when_made", "made_to_order"
                        )
                        is_digital = (
                            row.get("is_digital", "").lower() == "true"
                            if row.get("is_digital")
                            else template.get("is_digital", True)
                        )
                        is_personalizable = (
                            row.get("is_personalizable", "").lower() == "true"
                            if row.get("is_personalizable")
                            else template.get("is_personalizable", False)
                        )
                        personalization_instructions = row.get(
                            "personalization_instructions"
                        ) or template.get("personalization_instructions", "")

                        # Prepare listing data
                        listing_data = {
                            "title": title,
                            "description": description,
                            "price": price,
                            "quantity": quantity,
                            "tags": tags[:13],  # Etsy allows max 13 tags
                            "materials": materials[:13],  # Etsy allows max 13 materials
                            "shipping_profile_id": int(shipping_profile_id),
                            "taxonomy_id": int(taxonomy_id),
                            "who_made": who_made,
                            "is_supply": is_supply,
                            "when_made": when_made,
                            "is_digital": is_digital,
                            "is_personalizable": is_personalizable,
                            "personalization_instructions": personalization_instructions,
                            "is_draft": is_draft,
                        }

                        # Add shop section ID if available
                        shop_section_id = row.get("shop_section_id") or template.get(
                            "shop_section_id"
                        )
                        if shop_section_id:
                            listing_data["shop_section_id"] = int(shop_section_id)

                        # Create the listing
                        listing = self.listings.create_listing(**listing_data)

                        if not listing:
                            error_message = f"Row {row_num}: Failed to create listing"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Upload images
                        listing_id = listing.get("listing_id")

                        # Find images in the mocks folder
                        mocks_folder = os.path.join(full_folder_path, "mocks")
                        if os.path.exists(mocks_folder):
                            image_paths = sorted(
                                glob.glob(os.path.join(mocks_folder, "*.jpg"))
                                + glob.glob(os.path.join(mocks_folder, "*.png"))
                            )
                        else:
                            # Find images in the main folder
                            image_paths = sorted(
                                glob.glob(os.path.join(full_folder_path, "*.jpg"))
                                + glob.glob(os.path.join(full_folder_path, "*.png"))
                            )

                        if not image_paths:
                            error_message = (
                                f"Row {row_num}: No images found in {full_folder_path}"
                            )
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Upload images
                        for i, image_path in enumerate(
                            image_paths[:10]
                        ):  # Etsy allows max 10 images
                            image_result = self.listings.upload_listing_image(
                                listing_id=listing_id, image_path=image_path, rank=i + 1
                            )

                            if not image_result:
                                logger.warning(
                                    f"Row {row_num}: Failed to upload image {image_path}"
                                )

                        # Upload digital files if applicable
                        if is_digital:
                            # Find zip files in the zipped folder
                            zipped_folder = os.path.join(full_folder_path, "zipped")
                            if os.path.exists(zipped_folder):
                                zip_paths = sorted(
                                    glob.glob(os.path.join(zipped_folder, "*.zip"))
                                )

                                for i, zip_path in enumerate(zip_paths):
                                    file_result = self.listings.upload_digital_file(
                                        listing_id=listing_id,
                                        file_path=zip_path,
                                        rank=i,
                                    )

                                    if not file_result:
                                        logger.warning(
                                            f"Row {row_num}: Failed to upload digital file {zip_path}"
                                        )

                        # Upload videos if available
                        videos_folder = os.path.join(full_folder_path, "videos")
                        if os.path.exists(videos_folder):
                            video_paths = sorted(
                                glob.glob(os.path.join(videos_folder, "*.mp4"))
                            )

                            for i, video_path in enumerate(
                                video_paths[:1]
                            ):  # Etsy allows only 1 video per listing
                                video_result = self.listings.upload_video(
                                    listing_id=listing_id, video_path=video_path, rank=1
                                )

                                if not video_result:
                                    logger.warning(
                                        f"Row {row_num}: Failed to upload video {video_path}"
                                    )

                        logger.info(
                            f"Row {row_num}: Created listing {listing_id} for {product_name}"
                        )
                        success_count += 1

                        # Sleep to avoid rate limiting
                        time.sleep(1)

                    except Exception as e:
                        error_message = f"Row {row_num}: Error processing row: {e}"
                        logger.error(error_message)
                        error_count += 1
                        error_messages.append(error_message)
        except Exception as e:
            error_message = f"Error processing CSV file: {e}"
            logger.error(error_message)
            error_count += 1
            error_messages.append(error_message)

        return success_count, error_count, error_messages

    def update_listings_from_csv(self, csv_file: str) -> Tuple[int, int, List[str]]:
        """
        Update listings from a CSV file.

        Args:
            csv_file: Path to the CSV file

        Returns:
            Tuple of (success_count, error_count, error_messages)
        """
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return 0, 1, [f"CSV file not found: {csv_file}"]

        success_count = 0
        error_count = 0
        error_messages = []

        try:
            with open(csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(
                    reader, start=2
                ):  # Start at 2 to account for header row
                    try:
                        # Get listing ID
                        listing_id = row.get("listing_id", "").strip()

                        if not listing_id:
                            error_message = f"Row {row_num}: Missing listing_id"
                            logger.error(error_message)
                            error_count += 1
                            error_messages.append(error_message)
                            continue

                        # Prepare update data
                        update_data = {}

                        # Add fields to update
                        for field in [
                            "title",
                            "description",
                            "price",
                            "quantity",
                            "tags",
                            "materials",
                            "shop_section_id",
                            "who_made",
                            "is_supply",
                            "when_made",
                            "is_personalizable",
                            "personalization_instructions",
                        ]:
                            if field in row and row[field]:
                                if field in ["tags", "materials"]:
                                    update_data[field] = row[field].split(",")
                                elif field in ["price", "quantity", "shop_section_id"]:
                                    if field == "price":
                                        update_data[field] = float(row[field])
                                    else:
                                        update_data[field] = int(row[field])
                                elif field in ["is_supply", "is_personalizable"]:
                                    update_data[field] = row[field].lower() == "true"
                                else:
                                    update_data[field] = row[field]

                        # Update the listing
                        if update_data:
                            result = self.listings.update_listing(
                                int(listing_id), **update_data
                            )

                            if result:
                                logger.info(
                                    f"Row {row_num}: Updated listing {listing_id}"
                                )
                                success_count += 1
                            else:
                                error_message = f"Row {row_num}: Failed to update listing {listing_id}"
                                logger.error(error_message)
                                error_count += 1
                                error_messages.append(error_message)
                        else:
                            logger.warning(
                                f"Row {row_num}: No fields to update for listing {listing_id}"
                            )
                            success_count += 1

                        # Sleep to avoid rate limiting
                        time.sleep(1)

                    except Exception as e:
                        error_message = f"Row {row_num}: Error processing row: {e}"
                        logger.error(error_message)
                        error_count += 1
                        error_messages.append(error_message)
        except Exception as e:
            error_message = f"Error processing CSV file: {e}"
            logger.error(error_message)
            error_count += 1
            error_messages.append(error_message)

        return success_count, error_count, error_messages

    def create_csv_template(self, output_file: str, operation: str = "create") -> bool:
        """
        Create a CSV template for bulk operations.

        Args:
            output_file: Path to the output file
            operation: Operation type ("create" or "update")

        Returns:
            True if creation was successful, False otherwise
        """
        try:
            if operation == "create":
                # Fields for creating listings
                fields = [
                    "product_type",
                    "name",
                    "folder_path",
                    "title",
                    "description",
                    "price",
                    "quantity",
                    "tags",
                    "materials",
                    "shipping_profile_id",
                    "taxonomy_id",
                    "shop_section_id",
                    "category",
                    "who_made",
                    "is_supply",
                    "when_made",
                    "is_digital",
                    "is_personalizable",
                    "personalization_instructions",
                ]
            else:
                # Fields for updating listings
                fields = [
                    "listing_id",
                    "title",
                    "description",
                    "price",
                    "quantity",
                    "tags",
                    "materials",
                    "shop_section_id",
                    "who_made",
                    "is_supply",
                    "when_made",
                    "is_personalizable",
                    "personalization_instructions",
                ]

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fields)

                # Add a sample row
                if operation == "create":
                    writer.writerow(
                        [
                            "pattern",
                            "Sample Pattern",
                            "input/sample_pattern",
                            "",
                            "",
                            "4.99",
                            "999",
                            "seamless pattern,digital paper,background,scrapbooking,commercial use",
                            "digital file,digital download,digital pattern,digital paper",
                            "",
                            "2427",
                            "42625767",
                            "patterns",
                            "i_did",
                            "true",
                            "2020_2024",
                            "true",
                            "false",
                            "",
                        ]
                    )
                else:
                    writer.writerow(
                        [
                            "123456789",
                            "Updated Title",
                            "Updated Description",
                            "5.99",
                            "999",
                            "seamless pattern,digital paper,background,scrapbooking,commercial use",
                            "digital file,digital download,digital pattern,digital paper",
                            "42625767",
                            "i_did",
                            "true",
                            "2020_2024",
                            "false",
                            "",
                        ]
                    )

            logger.info(f"CSV template created: {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error creating CSV template: {e}")
            return False
