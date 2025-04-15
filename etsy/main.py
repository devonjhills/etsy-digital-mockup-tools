"""
Main module for Etsy integration.
"""

import os
from typing import Dict, List, Optional

from utils.common import setup_logging
from etsy.auth import EtsyAuth
from etsy.listings import EtsyListings
from etsy.templates import ListingTemplate
from etsy.content import ContentGenerator
from etsy.constants import DEFAULT_ETSY_INSTRUCTIONS

# Set up logging
logger = setup_logging(__name__)


class EtsyIntegration:
    """Main class for Etsy integration."""

    def __init__(
        self,
        etsy_api_key: str,
        etsy_api_secret: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider_type: str = "gemini",
        templates_dir: str = "templates",
    ):
        """
        Initialize the Etsy integration.

        Args:
            etsy_api_key: Etsy API key
            etsy_api_secret: Etsy API secret
            api_key: API key for the AI provider (optional)
            model_name: Model name to use (optional)
            provider_type: Type of AI provider to use (only 'gemini' is supported)
            templates_dir: Directory to store templates
        """
        self.auth = EtsyAuth(etsy_api_key, etsy_api_secret)
        self.listings = EtsyListings(self.auth)
        self.templates = ListingTemplate(templates_dir)

        # Initialize content generator
        self.content_generator = ContentGenerator(api_key, model_name, provider_type)

    def authenticate(self) -> bool:
        """
        Authenticate with Etsy.

        Returns:
            True if authentication was successful, False otherwise
        """
        if self.auth.is_authenticated():
            logger.info("Already authenticated with Etsy.")
            return True

        logger.info("Starting OAuth flow...")
        return self.auth.start_oauth_flow()

    def create_listing_from_folder(
        self,
        folder_path: str,
        product_type: str,
        product_name: Optional[str] = None,
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        custom_tags: Optional[List[str]] = None,
        is_draft: bool = False,
    ) -> Optional[Dict]:
        """
        Create an Etsy listing from a product folder.

        Args:
            folder_path: Path to the product folder
            product_type: Product type
            product_name: Product name (optional, defaults to folder name)
            custom_title: Custom title for the listing (optional)
            custom_description: Custom description for the listing (optional)
            custom_tags: Custom tags for the listing (optional, max 13)
            is_draft: Whether to create the listing as a draft

        Returns:
            Listing data or None if creation failed
        """
        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return None

        # Get product name from folder name if not provided
        if not product_name:
            product_name = (
                os.path.basename(folder_path)
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )

        # Get template
        template = self.templates.get_template_for_product_type(product_type)
        if not template:
            logger.error(f"Template not found for product type: {product_type}")
            return None

        # For digital products, we don't need a shipping profile
        shipping_profile_id = None

        # Only get shipping profiles for physical products
        if not template.get("is_digital", True):
            shipping_profiles = self.listings.get_shipping_profiles()
            if not shipping_profiles:
                logger.error("No shipping profiles found for physical product.")
                return None

            # Find a physical shipping profile
            for profile in shipping_profiles:
                if profile.get("type") != "digital":
                    shipping_profile_id = profile.get("shipping_profile_id")
                    break

            if not shipping_profile_id:
                logger.error("No physical shipping profile found.")
                return None

        # Prepare product info
        product_info = {
            "name": product_name,
            "folder_path": folder_path,
            "product_type": product_type,
        }

        # Add product-specific name field based on product type
        if product_type == "pattern" or product_type == "patterns":
            product_info["pattern_name"] = product_name
            # Add default values for pattern template variables
            product_info.update(
                {
                    "colors": "Multicolor",
                    "style": "Modern",
                    "dimensions": "3000x3000 pixels",
                    "file_formats": "JPG",
                    "num_files": "12",
                }
            )
        elif product_type == "clipart":
            product_info["clipart_name"] = product_name
            # Add default values for clipart template variables
            product_info.update(
                {
                    "style": "Modern",
                    "theme": "Decorative",
                    "dimensions": "3000x3000 pixels",
                    "num_files": "12",
                }
            )

        # Add additional info based on folder contents
        product_info.update(self._extract_product_info(folder_path, product_type))

        # Use custom values if provided, otherwise use template values
        if custom_title:
            title = custom_title
        else:
            # Use template with basic substitution
            title_template = template.get("title_template", "{name}")
            # Use product_info['name'] to avoid duplicate name parameter
            title = title_template.format(**product_info)

        if custom_description:
            description = custom_description
        else:
            description_template = template.get(
                "description_template", "# {name}\n\nDigital product for download."
            )
            # Use product_info['name'] to avoid duplicate name parameter
            description = description_template.format(**product_info)

        if custom_tags:
            tags = custom_tags[:13]  # Ensure max 13 tags
        else:
            tags = template.get("tags", [])[:13]

        # Create the listing
        is_digital = template.get("is_digital", True)  # Default to digital listing

        listing_data = {
            "title": title,
            "description": description,
            "price": float(template.get("price", 3.32)),
            "quantity": int(template.get("quantity", 999)),
            "tags": tags[:13],  # Etsy allows max 13 tags
            "materials": template.get("materials", [])[
                :13
            ],  # Etsy allows max 13 materials
            "taxonomy_id": int(
                template.get("taxonomy_id", 6844)
            ),  # Default to Digital Patterns & Textures (6844 for clipart and patterns)
            "who_made": template.get("who_made", "i_did"),
            "is_supply": template.get("is_supply", False),
            "when_made": template.get("when_made", "2020_2024"),
            "is_digital": is_digital,
            "is_personalizable": template.get("is_personalizable", False),
            "personalization_instructions": template.get(
                "personalization_instructions", ""
            ),
            "is_draft": is_draft,
        }

        # Only add shipping_profile_id for physical products
        if not is_digital and shipping_profile_id:
            listing_data["shipping_profile_id"] = shipping_profile_id

        # Add shop section ID based on product type
        shop_section_mapping = {
            "pattern": 42625767,  # Support both singular and plural
            "patterns": 42625767,
            "clipart": 42698827,
        }

        # First try to get from the mapping based on product type
        shop_section_id = shop_section_mapping.get(product_type)

        # If not found in mapping, try to get from template
        if shop_section_id is None:
            shop_section_id = template.get("shop_section_id")

        if shop_section_id:
            listing_data["shop_section_id"] = int(shop_section_id)

        listing = self.listings.create_listing(**listing_data)

        if not listing:
            logger.error("Failed to create listing.")
            return None

        # Upload images
        listing_id = listing.get("listing_id")

        # Find images in the mocks folder
        mocks_folder = os.path.join(folder_path, "mocks")
        if os.path.exists(mocks_folder):
            import glob

            image_paths = sorted(
                glob.glob(os.path.join(mocks_folder, "*.jpg"))
                + glob.glob(os.path.join(mocks_folder, "*.png"))
            )
        else:
            # Find images in the main folder
            import glob

            image_paths = sorted(
                glob.glob(os.path.join(folder_path, "*.jpg"))
                + glob.glob(os.path.join(folder_path, "*.png"))
            )

        if not image_paths:
            logger.warning(f"No images found in {folder_path}")
        else:
            # Upload images
            # Reorder images to put main.png first
            main_image_paths = []
            other_image_paths = []

            for image_path in image_paths:
                if os.path.basename(image_path) == "main.png":
                    main_image_paths.append(image_path)
                else:
                    other_image_paths.append(image_path)

            # Combine lists with main.png first
            ordered_image_paths = main_image_paths + other_image_paths

            # Upload images (max 10)
            for i, image_path in enumerate(ordered_image_paths[:10]):
                # Set rank based on image name
                rank = i + 1

                # Log the image being uploaded
                logger.info(
                    f"Uploading image {os.path.basename(image_path)} with rank {rank}"
                )

                image_result = self.listings.upload_listing_image(
                    listing_id=listing_id, image_path=image_path, rank=rank
                )

                if not image_result:
                    logger.warning(f"Failed to upload image {image_path}")

        # Upload digital files if applicable
        if template.get("is_digital", True):
            # Find zip files in the zipped folder
            zipped_folder = os.path.join(folder_path, "zipped")
            if os.path.exists(zipped_folder):
                import glob

                zip_paths = sorted(glob.glob(os.path.join(zipped_folder, "*.zip")))

                for i, zip_path in enumerate(zip_paths):
                    file_result = self.listings.upload_digital_file(
                        listing_id=listing_id, file_path=zip_path, rank=i
                    )

                    if not file_result:
                        logger.warning(f"Failed to upload digital file {zip_path}")

        # Upload videos if available
        videos_folder = os.path.join(folder_path, "videos")
        if os.path.exists(videos_folder):
            import glob

            video_paths = sorted(glob.glob(os.path.join(videos_folder, "*.mp4")))

            for i, video_path in enumerate(
                video_paths[:1]
            ):  # Etsy allows only 1 video per listing
                video_result = self.listings.upload_video(
                    listing_id=listing_id, video_path=video_path, rank=1
                )

                if not video_result:
                    logger.warning(f"Failed to upload video {video_path}")

        logger.info(f"Created listing {listing_id} for {product_name}")
        return listing

    def create_listings_bulk(
        self, input_dir: str, product_type: str, is_draft: bool = False
    ) -> List[Dict]:
        """
        Create Etsy listings for all subfolders in the input directory.

        Args:
            input_dir: Path to the input directory containing product subfolders
            product_type: Product type (pattern or clipart)
            is_draft: Whether to create the listings as drafts

        Returns:
            List of created listings
        """
        if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return []

        # Get all subfolders in the input directory
        subfolders = [
            f
            for f in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, f))
        ]

        if not subfolders:
            logger.error(f"No subfolders found in {input_dir}")
            return []

        logger.info(f"Found {len(subfolders)} subfolders in {input_dir}")

        # Create listings for each subfolder
        created_listings = []
        failed_folders = []

        for subfolder in subfolders:
            folder_path = os.path.join(input_dir, subfolder)
            logger.info(f"Processing folder: {folder_path}")

            try:
                # Step 1: Resize and rename images
                logger.info(f"Resizing and renaming images for {subfolder}...")
                self._resize_and_rename(folder_path, product_type)

                # Step 2: Generate mockups based on product type
                logger.info(f"Generating mockups for {subfolder}...")
                self._generate_mockups(folder_path, product_type)

                # Step 3: Create zip files
                logger.info(f"Creating zip files for {subfolder}...")
                self._create_zip_files(folder_path)

                # Step 4: Generate content using Gemini API
                logger.info(f"Generating content for {subfolder}...")
                # Use the standard instructions from constants
                content = self.generate_content_from_mockup(
                    folder_path=folder_path,
                    product_type=product_type,
                    instructions=DEFAULT_ETSY_INSTRUCTIONS,
                )

                # Step 4: Create listing with generated content
                if content and content["title"]:
                    logger.info(f"Creating Etsy listing for {subfolder}...")
                    listing = self.create_listing_from_folder(
                        folder_path=folder_path,
                        product_type=product_type,
                        custom_title=content["title"],
                        custom_description=content["description"],
                        custom_tags=content["tags"],
                        is_draft=is_draft,
                    )

                    if listing:
                        created_listings.append(listing)
                        logger.info(f"Successfully created listing for {subfolder}")
                    else:
                        failed_folders.append(subfolder)
                        logger.error(f"Failed to create listing for {subfolder}")
                else:
                    failed_folders.append(subfolder)
                    logger.error(f"Failed to generate content for {subfolder}")
            except Exception as e:
                failed_folders.append(subfolder)
                logger.error(f"Error processing {subfolder}: {e}")

        # Log summary
        logger.info(
            f"Bulk processing complete. Created {len(created_listings)} listings."
        )
        if failed_folders:
            logger.error(
                f"Failed to create listings for {len(failed_folders)} folders: {', '.join(failed_folders)}"
            )

        return created_listings

    def prepare_bulk_listings(self, input_dir: str, product_type: str) -> List[Dict]:
        """
        Prepare Etsy listings for all subfolders in the input directory without uploading.

        Args:
            input_dir: Path to the input directory containing product subfolders
            product_type: Product type (pattern or clipart)

        Returns:
            List of prepared listings data
        """
        if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
            logger.error(f"Input directory not found: {input_dir}")
            return []

        # Get all subfolders in the input directory
        subfolders = [
            f
            for f in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, f))
        ]

        if not subfolders:
            logger.error(f"No subfolders found in {input_dir}")
            return []

        logger.info(f"Found {len(subfolders)} subfolders in {input_dir}")

        # Prepare listings for each subfolder
        prepared_listings = []
        failed_folders = []

        for subfolder in subfolders:
            folder_path = os.path.join(input_dir, subfolder)
            logger.info(f"Processing folder: {folder_path}")

            try:
                # Step 1: Resize and rename images
                logger.info(f"Resizing and renaming images for {subfolder}...")
                self._resize_and_rename(folder_path, product_type)

                # Step 2: Generate mockups based on product type
                logger.info(f"Generating mockups for {subfolder}...")
                self._generate_mockups(folder_path, product_type)

                # Step 3: Create zip files
                logger.info(f"Creating zip files for {subfolder}...")
                self._create_zip_files(folder_path)

                # Step 4: Generate content using Gemini API
                logger.info(f"Generating content for {subfolder}...")
                # Import the default instructions from constants
                from etsy.constants import DEFAULT_ETSY_INSTRUCTIONS

                content = self.generate_content_from_mockup(
                    folder_path=folder_path,
                    product_type=product_type,
                    instructions=DEFAULT_ETSY_INSTRUCTIONS,
                )

                # If title is empty but we have content, use folder name as fallback title
                if content and not content["title"] and subfolder:
                    logger.warning(
                        f"No title extracted from Gemini API response. Using folder name as fallback."
                    )
                    content["title"] = subfolder

                if content:
                    # Get mockup images
                    mocks_folder = os.path.join(folder_path, "mocks")
                    mockup_images = []
                    if os.path.exists(mocks_folder):
                        import glob

                        mockup_images = sorted(
                            glob.glob(os.path.join(mocks_folder, "*.jpg"))
                            + glob.glob(os.path.join(mocks_folder, "*.png"))
                        )

                    # Get zip files
                    zipped_folder = os.path.join(folder_path, "zipped")
                    zip_files = []
                    if os.path.exists(zipped_folder):
                        import glob

                        zip_files = sorted(
                            glob.glob(os.path.join(zipped_folder, "*.zip"))
                        )

                    # Get video files (only from videos folder)
                    videos_folder = os.path.join(folder_path, "videos")
                    video_files = []
                    if os.path.exists(videos_folder):
                        import glob

                        video_files = sorted(
                            glob.glob(os.path.join(videos_folder, "*.mp4"))
                        )

                    # Prepare listing data
                    listing_data = {
                        "folder_path": folder_path,
                        "folder_name": subfolder,
                        "product_type": product_type,
                        "title": content["title"],
                        "description": content["description"],
                        "tags": content["tags"],
                        "mockup_images": mockup_images,
                        "zip_files": zip_files,
                        "video_files": video_files,
                    }

                    prepared_listings.append(listing_data)
                    logger.info(f"Successfully prepared listing for {subfolder}")
                else:
                    failed_folders.append(subfolder)
                    logger.error(f"Failed to generate content for {subfolder}")
            except Exception as e:
                failed_folders.append(subfolder)
                logger.error(f"Error processing {subfolder}: {e}")

        # Log summary
        logger.info(
            f"Bulk preparation complete. Prepared {len(prepared_listings)} listings."
        )
        if failed_folders:
            logger.error(
                f"Failed to prepare listings for {len(failed_folders)} folders: {', '.join(failed_folders)}"
            )

        return prepared_listings

    def upload_prepared_listing(
        self, listing_data: Dict, is_draft: bool = False
    ) -> Optional[Dict]:
        """
        Upload a prepared listing to Etsy.

        Args:
            listing_data: Prepared listing data
            is_draft: Whether to create the listing as a draft

        Returns:
            Uploaded listing data or None if upload failed
        """
        try:
            # Create listing
            listing = self.create_listing_from_folder(
                folder_path=listing_data["folder_path"],
                product_type=listing_data["product_type"],
                custom_title=listing_data["title"],
                custom_description=listing_data["description"],
                custom_tags=listing_data["tags"],
                is_draft=is_draft,
            )

            if listing:
                logger.info(
                    f"Successfully uploaded listing for {listing_data['folder_name']}"
                )
                return listing
            else:
                logger.error(
                    f"Failed to upload listing for {listing_data['folder_name']}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Error uploading listing for {listing_data['folder_name']}: {e}"
            )
            return None

    def _resize_and_rename(self, folder_path: str, product_type: str) -> None:
        """
        Resize and rename images in a product folder based on product type.
        Skips processing if files are already properly named and sized.

        Args:
            folder_path: Path to the product folder
            product_type: Product type (pattern or clipart)
        """
        try:
            # Get the folder name (last part of the path)
            folder_name = os.path.basename(folder_path)
            logger.info(f"Checking images in {folder_name}...")

            # Create a safe folder name for renaming files
            import re

            safe_folder_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name).lower()

            # Get all image files in the folder (excluding mocks and zipped folders)
            image_files = []
            properly_named_files = []

            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and file.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif")
                ):
                    # Skip files in mocks or zipped folders
                    if "mocks" in file_path or "zipped" in file_path:
                        continue

                    # Check if the file is already properly named (follows the pattern safe_folder_name_X.jpg or safe_folder_name_X.png)
                    if re.match(
                        f"{safe_folder_name}_\d+\.jpe?g$", file.lower()
                    ) or re.match(f"{safe_folder_name}_\d+\.png$", file.lower()):
                        properly_named_files.append(file_path)
                    else:
                        image_files.append(file_path)

            # If no image files found, check if we have properly named files
            if not image_files and not properly_named_files:
                logger.warning(f"No image files found in {folder_path}")
                return

            # If all files are already properly named, skip processing
            if not image_files and properly_named_files:
                logger.info(
                    f"All images in {folder_path} are already properly named. Skipping processing."
                )
                return

            logger.info(
                f"Found {len(image_files)} images to process and {len(properly_named_files)} already processed images in {folder_path}"
            )

            # Process each image file that needs processing
            from PIL import Image
            from utils.common import get_resampling_filter

            # Start numbering from the highest existing number + 1
            next_index = 1
            if properly_named_files:
                # Extract numbers from existing properly named files
                numbers = []
                for file_path in properly_named_files:
                    file_name = os.path.basename(file_path)
                    # Check for both jpg and png files
                    match = re.search(
                        f"{safe_folder_name}_(\d+)\.(jpe?g|png)$", file_name.lower()
                    )
                    if match:
                        numbers.append(int(match.group(1)))

                if numbers:
                    next_index = max(numbers) + 1

            for i, image_file in enumerate(sorted(image_files), start=next_index):
                try:
                    logger.info(f"Processing image: {image_file}")

                    with Image.open(image_file) as img:
                        # Get original dimensions
                        original_width, original_height = img.size
                        original_filename = os.path.basename(image_file)

                        # Determine max size based on product type
                        if product_type == "pattern" or product_type == "patterns":
                            max_size = (3600, 3600)
                        else:  # clipart
                            max_size = (1500, 1500)

                        # Determine if resizing is needed
                        needs_resize = (
                            original_width > max_size[0]
                            or original_height > max_size[1]
                        )

                        # Create new filename with appropriate extension based on product type
                        file_extension = (
                            "jpg"
                            if product_type == "pattern" or product_type == "patterns"
                            else "png"
                        )
                        new_filename = f"{safe_folder_name}_{i}.{file_extension}"
                        new_file_path = os.path.join(folder_path, new_filename)

                        # Check if the file already exists with the target name
                        if (
                            os.path.exists(new_file_path)
                            and new_file_path != image_file
                        ):
                            logger.info(
                                f"  File {new_filename} already exists. Skipping."
                            )
                            continue

                        logger.info(
                            f"  Processing: {original_filename} -> {new_filename}"
                        )

                        # Resize if needed
                        if needs_resize:
                            # Calculate new dimensions
                            width_ratio = max_size[0] / original_width
                            height_ratio = max_size[1] / original_height
                            ratio = min(width_ratio, height_ratio)

                            new_width = int(original_width * ratio)
                            new_height = int(original_height * ratio)

                            # Resize the image
                            img_to_save = img.resize(
                                (new_width, new_height), get_resampling_filter()
                            )

                            # Set DPI
                            if hasattr(img_to_save, "info"):
                                img_to_save.info["dpi"] = (300, 300)

                            logger.info(
                                f"  Resized: {original_width}x{original_height} -> {new_width}x{new_height}"
                            )
                        else:
                            img_to_save = img
                            logger.info(
                                f"  No resizing needed. Image is already within size limits."
                            )

                        # Save the image only if it's not already in the correct format
                        if image_file != new_file_path or needs_resize:
                            # For clipart, ensure we preserve transparency by converting to RGBA
                            if product_type == "clipart":
                                # Convert to RGBA to preserve transparency
                                img_to_save = img_to_save.convert("RGBA")
                                img_to_save.save(
                                    new_file_path, format="PNG", dpi=(300, 300)
                                )
                            else:
                                # For patterns, save as JPEG
                                img_to_save.save(
                                    new_file_path,
                                    format="JPEG",
                                    dpi=(300, 300),
                                    quality=85,
                                    optimize=True,
                                )
                            logger.info(f"  Saved as: {new_filename}")

                            # Delete the original file if it's different from the new file
                            if image_file != new_file_path:
                                try:
                                    os.remove(image_file)
                                    logger.info(
                                        f"  Deleted original: {original_filename}"
                                    )
                                except Exception as e:
                                    logger.error(f"  Error deleting {image_file}: {e}")
                        else:
                            logger.info(
                                f"  File is already in the correct format. No changes needed."
                            )
                except Exception as e:
                    logger.error(f"Error processing image {image_file}: {e}")

            logger.info(f"Images processed successfully in {folder_path}")

        except Exception as e:
            logger.error(f"Error resizing and renaming images: {e}")
            raise

    def _generate_mockups(self, folder_path: str, product_type: str) -> None:
        """
        Generate mockups for a product folder based on product type.

        Args:
            folder_path: Path to the product folder
            product_type: Product type (pattern or clipart)
        """
        try:
            # Get product name from folder name
            product_name = (
                os.path.basename(folder_path)
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )

            # Import mockup modules dynamically to avoid circular imports
            import importlib

            # Create mocks directory if it doesn't exist
            mocks_dir = os.path.join(folder_path, "mocks")
            os.makedirs(mocks_dir, exist_ok=True)

            if product_type == "pattern" or product_type == "patterns":
                # Import pattern mockup modules
                dynamic_main_mockup = importlib.import_module(
                    "pattern.mockups.dynamic_main_mockup"
                )
                seamless = importlib.import_module("pattern.seamless")
                layered = importlib.import_module("pattern.mockups.layered")
                grid = importlib.import_module("pattern.mockups.grid")
                pattern_video = importlib.import_module("pattern.video")

                # Generate pattern mockups
                logger.info(f"Creating main mockup for {product_name}...")
                dynamic_main_mockup.create_main_mockup(folder_path, product_name)

                logger.info(f"Creating seamless mockup for {product_name}...")
                seamless_pattern_file = seamless.create_pattern(folder_path)
                seamless.create_seamless_mockup(folder_path)

                logger.info(f"Creating layered mockup for {product_name}...")
                layered.create_large_grid(folder_path)

                logger.info(f"Creating grid mockup for {product_name}...")
                grid.create_grid_mockup_with_borders(folder_path)

                # Create video mockup
                logger.info(f"Creating video mockup for {product_name}...")
                pattern_video.create_seamless_zoom_video(
                    folder_path, seamless_pattern_file
                )

            elif product_type == "clipart":
                # Import clipart modules directly
                from clipart.processing.collage import create_collage_layout
                from clipart.processing.grid import create_2x2_grid, apply_watermark
                from clipart.processing.transparency import create_transparency_demo
                from clipart.processing.title import add_title_bar_and_text
                import clipart.config as clipart_config
                from utils.common import (
                    get_asset_path,
                    safe_load_image,
                    get_resampling_filter,
                )

                clipart_video = importlib.import_module("clipart.video")

                # Create mocks directory
                mocks_folder = os.path.join(folder_path, "mocks")
                os.makedirs(mocks_folder, exist_ok=True)

                # Find PNG images in the folder
                import glob

                input_image_paths = sorted(
                    glob.glob(os.path.join(folder_path, "*.png"))
                )

                if not input_image_paths:
                    logger.warning(
                        f"No PNG images found in {folder_path}. Skipping mockup generation."
                    )
                else:
                    num_images = len(input_image_paths)
                    logger.info(f"Found {num_images} PNG images for mockup generation.")

                    # Import PIL for image processing
                    from PIL import Image, ImageDraw, ImageFont

                    # Load canvas backgrounds
                    canvas_bg_main = None
                    canvas_bg_2x2 = None

                    # Try to load canvas.png from assets
                    canvas_path = get_asset_path("canvas.png")
                    if canvas_path:
                        try:
                            canvas_bg = Image.open(canvas_path).convert("RGBA")
                            # Create copies for different mockups
                            canvas_bg_main = canvas_bg.copy().resize(
                                (3000, 2250), get_resampling_filter()
                            )
                            canvas_bg_2x2 = canvas_bg.copy().resize(
                                (2000, 2000), get_resampling_filter()
                            )
                            logger.info(f"Loaded canvas background from {canvas_path}")
                        except Exception as e:
                            logger.warning(
                                f"Error loading canvas.png: {e}. Using white background."
                            )

                    # If canvas loading failed, create white backgrounds
                    if not canvas_bg_main:
                        canvas_bg_main = Image.new(
                            "RGBA", (3000, 2250), (255, 255, 255, 255)
                        )
                    if not canvas_bg_2x2:
                        canvas_bg_2x2 = Image.new(
                            "RGBA", (2000, 2000), (255, 255, 255, 255)
                        )

                    # 1. Create collage layout for main mockup
                    logger.info(f"Creating collage layout for {product_name}...")

                    # Create title block
                    title_text = product_name
                    subtitle_text_top = "Commercial Use"

                    # Skip the complex title block generation

                    # Create a simplified collage layout
                    # Instead of using the complex collage layout function, we'll create a simpler layout
                    # that's more reliable for our needs

                    # Create a copy of the canvas for the layout
                    layout_canvas = canvas_bg_main.copy()

                    # Load images directly
                    loaded_images = []
                    for path in input_image_paths:
                        try:
                            img = Image.open(path).convert("RGBA")
                            loaded_images.append(img)
                        except Exception as e:
                            logger.warning(f"Failed to load image {path}: {e}")

                    if not loaded_images:
                        logger.warning("No images loaded for collage")
                        layout_with_images = layout_canvas
                    else:
                        # Select a centerpiece (just use the first image)
                        centerpiece = loaded_images[0]

                        # Calculate centerpiece size (65% of canvas width)
                        centerpiece_scale_factor = 0.65
                        centerpiece_max_width = int(
                            layout_canvas.width * centerpiece_scale_factor
                        )
                        centerpiece_max_height = int(
                            layout_canvas.height * centerpiece_scale_factor
                        )

                        # Resize centerpiece
                        centerpiece_aspect = (
                            centerpiece.width / centerpiece.height
                            if centerpiece.height > 0
                            else 1
                        )
                        if centerpiece_aspect >= 1:  # Wider than tall
                            centerpiece_width = centerpiece_max_width
                            centerpiece_height = int(
                                centerpiece_width / centerpiece_aspect
                            )
                            if centerpiece_height > centerpiece_max_height:
                                centerpiece_height = centerpiece_max_height
                                centerpiece_width = int(
                                    centerpiece_height * centerpiece_aspect
                                )
                        else:  # Taller than wide
                            centerpiece_height = centerpiece_max_height
                            centerpiece_width = int(
                                centerpiece_height * centerpiece_aspect
                            )
                            if centerpiece_width > centerpiece_max_width:
                                centerpiece_width = centerpiece_max_width
                                centerpiece_height = int(
                                    centerpiece_width / centerpiece_aspect
                                )

                        centerpiece_resized = centerpiece.resize(
                            (centerpiece_width, centerpiece_height),
                            get_resampling_filter(),
                        )

                        # Calculate centerpiece position (centered, but avoid title)
                        centerpiece_x = (layout_canvas.width - centerpiece_width) // 2
                        centerpiece_y = (layout_canvas.height - centerpiece_height) // 2

                        # Center the image vertically
                        # No title adjustment needed

                        # Paste centerpiece
                        layout_canvas.paste(
                            centerpiece_resized,
                            (centerpiece_x, centerpiece_y),
                            centerpiece_resized,
                        )

                        # Place a few surrounding images if we have more than one image
                        if len(loaded_images) > 1:
                            # Use a few images for the surrounding (up to 4 more)
                            surrounding_images = loaded_images[
                                1 : min(5, len(loaded_images))
                            ]

                            # Define positions for surrounding images (fixed positions for reliability)
                            positions = [
                                (50, 50),  # Top left
                                (layout_canvas.width - 300, 50),  # Top right
                                (50, layout_canvas.height - 300),  # Bottom left
                                (
                                    layout_canvas.width - 300,
                                    layout_canvas.height - 300,
                                ),  # Bottom right
                            ]

                            # Calculate size for surrounding images (30% of canvas width)
                            surround_width = int(layout_canvas.width * 0.3)

                            # Place each surrounding image
                            for i, img in enumerate(surrounding_images):
                                if i >= len(positions):
                                    break

                                # Resize image
                                img_aspect = (
                                    img.width / img.height if img.height > 0 else 1
                                )
                                if img_aspect >= 1:  # Wider than tall
                                    img_width = surround_width
                                    img_height = int(img_width / img_aspect)
                                else:  # Taller than wide
                                    img_height = surround_width
                                    img_width = int(img_height * img_aspect)

                                img_resized = img.resize(
                                    (img_width, img_height), get_resampling_filter()
                                )

                                # Paste image
                                layout_canvas.paste(
                                    img_resized, positions[i], img_resized
                                )

                        layout_with_images = layout_canvas

                    # Create a proper collage layout for the main mockup
                    # This uses the same implementation as in clipart/main.py

                    # Create title text for the mockup
                    title = product_name
                    subtitle_bottom_text = (
                        f"{num_images} clip arts • 300 DPI • Transparent PNG"
                    )

                    # Create the title layer
                    logger.info("Creating title layer...")
                    title_layer_canvas = Image.new("RGBA", (3000, 2250), (0, 0, 0, 0))

                    # Add title bar and text
                    title_style_args = {
                        "title_font_name": "Angelina",
                        "title_font_size": 170,
                        "title_text_color": (50, 50, 50, 255),
                        "subtitle_font_name": "MarkerFelt",
                        "subtitle_font_size": 70,
                        "subtitle_text_color": (80, 80, 80, 255),
                        "title_backdrop_color": (255, 255, 255, 255),
                        "title_backdrop_border_color": (218, 165, 32, 255),
                        "title_backdrop_border_width": 5,
                        "title_backdrop_corner_radius": 40,
                    }

                    image_with_title_block_only, title_backdrop_bounds = (
                        add_title_bar_and_text(
                            image=title_layer_canvas,
                            background_image=canvas_bg_main,
                            title=title,
                            subtitle_top="Commercial Use",
                            subtitle_bottom=subtitle_bottom_text,
                            **title_style_args,
                        )
                    )

                    if not title_backdrop_bounds:
                        logger.warning(
                            "Title bounds calculation failed. Collage placement might be affected."
                        )

                    # Create collage layout
                    logger.info("Creating collage layout...")
                    collage_style_args = {
                        "centerpiece_scale_factor": 0.65,
                        "surround_min_width_factor": 0.20,
                        "surround_max_width_factor": 0.30,
                        "placement_step": 5,
                        "title_avoid_padding": 20,
                        "centerpiece_avoid_padding": 20,
                        "rescale_factor": 0.95,
                        "rescale_attempts": 3,
                        "max_acceptable_overlap_ratio": 0.10,
                        "min_scale_abs": 0.30,
                    }

                    layout_with_images = create_collage_layout(
                        image_paths=input_image_paths,
                        canvas=canvas_bg_main.copy(),
                        title_backdrop_bounds=title_backdrop_bounds,
                        **collage_style_args,
                    )

                    # Composite title onto collage
                    logger.info("Compositing title block...")
                    final_main_mockup = Image.alpha_composite(
                        layout_with_images.convert("RGBA"),
                        image_with_title_block_only.convert("RGBA"),
                    )

                    # Save main mockup
                    main_mockup_path = os.path.join(mocks_folder, "main.png")
                    final_main_mockup.save(main_mockup_path)
                    logger.info(f"Saved main collage mockup: {main_mockup_path}")

                    # 2. Create 2x2 Grid Mockups
                    logger.info("Generating 2x2 Grid Mockups...")
                    grid_count = 0
                    for i in range(0, num_images, 4):
                        batch_paths = input_image_paths[i : i + 4]
                        if not batch_paths:
                            continue

                        grid_count += 1
                        logger.info(
                            f"Creating grid {grid_count} (images {i+1}-{i+len(batch_paths)})..."
                        )

                        # Create a proper 2x2 grid mockup using the clipart module
                        try:
                            # Create the grid mockup
                            grid_mockup = create_2x2_grid(
                                input_image_paths=batch_paths,
                                canvas_bg_image=canvas_bg_2x2.copy(),
                                grid_size=(2000, 2000),
                                padding=30,
                            )

                            # Apply watermark
                            grid_mockup = apply_watermark(grid_mockup)

                            # Save the grid mockup
                            output_filename = os.path.join(
                                mocks_folder, f"{grid_count+1:02d}_grid_mockup.png"
                            )
                            grid_mockup.save(output_filename)
                            logger.info(f"Saved grid mockup: {output_filename}")
                        except Exception as e:
                            logger.error(f"Error creating grid mockup: {e}")

                    # 3. Create transparency demo
                    logger.info("Creating transparency demo...")
                    try:
                        if input_image_paths:
                            # Use the proper transparency demo function from clipart module
                            transparency_demo = create_transparency_demo(
                                image_path=input_image_paths[0],
                                checkerboard_size=30,
                                checkerboard_color1=(255, 255, 255),
                                checkerboard_color2=(200, 200, 200),
                                scale=0.7,
                            )

                            # Save the transparency demo
                            transparency_output = os.path.join(
                                mocks_folder, "transparency_demo.png"
                            )
                            transparency_demo.save(transparency_output)
                            logger.info(
                                f"Saved transparency demo: {transparency_output}"
                            )
                    except Exception as e:
                        logger.error(f"Error creating transparency demo: {e}")

                # Create video mockup
                logger.info(f"Creating clipart video mockup for {product_name}...")
                # Create videos folder for Etsy integration
                videos_folder = os.path.join(folder_path, "videos")
                os.makedirs(videos_folder, exist_ok=True)

                # Find mockup images to use for video
                mocks_folder = os.path.join(folder_path, "mocks")
                if os.path.exists(mocks_folder):
                    import glob

                    mockup_images = sorted(
                        glob.glob(os.path.join(mocks_folder, "*.jpg"))
                        + glob.glob(os.path.join(mocks_folder, "*.png"))
                    )

                    if mockup_images:
                        # Create a video output path in the videos folder
                        video_output_path = os.path.join(
                            videos_folder, "mockup_video.mp4"
                        )
                        try:
                            # Create video in the videos folder
                            clipart_video.create_video_mockup(
                                image_paths=mockup_images,
                                output_path=video_output_path,
                                fps=30,
                                transition_frames=20,
                                display_frames=50,
                            )
                            logger.info(f"Created video mockup: {video_output_path}")
                        except Exception as e:
                            logger.error(f"Error creating video mockup: {e}")

            logger.info(f"Mockups generated successfully for {product_name}")

        except Exception as e:
            logger.error(f"Error generating mockups: {e}")
            raise

    def _create_zip_files(self, folder_path: str) -> None:
        """
        Create zip files for a product folder.

        Args:
            folder_path: Path to the product folder
        """
        try:
            import zipfile
            import os

            # Get the folder name
            folder_name = os.path.basename(folder_path)
            logger.info(f"Creating zip files for {folder_name}...")

            # Create zipped directory if it doesn't exist
            zipped_dir = os.path.join(folder_path, "zipped")
            os.makedirs(zipped_dir, exist_ok=True)

            # Get all image files in the folder
            image_files = []
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and file.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif")
                ):
                    # Skip files in mocks or zipped folders
                    if "mocks" in file_path or "zipped" in file_path:
                        continue
                    image_files.append(file_path)

            if not image_files:
                logger.warning(f"No image files found in {folder_path} for zipping")
                return

            logger.info(f"Found {len(image_files)} image files to zip in {folder_path}")

            # Create a safe folder name for the zip file
            import re

            safe_folder_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name).lower()

            # Calculate total size of all images
            total_size_bytes = sum(os.path.getsize(f) for f in image_files)
            total_size_mb = total_size_bytes / (1024 * 1024)

            # Determine how many zip files we need (max 20MB per zip)
            max_size_mb = 20.0
            import math

            # Use math.ceil to properly round up the number of zips needed
            num_zips = max(1, math.ceil(total_size_mb / max_size_mb))

            if num_zips > 1:
                logger.info(
                    f"Total size: {total_size_mb:.2f} MB, splitting into {num_zips} zip files"
                )

                # Sort files by size (largest first) for better distribution
                image_files_with_size = [(f, os.path.getsize(f)) for f in image_files]
                image_files_with_size.sort(key=lambda x: x[1], reverse=True)

                # Distribute files across zips using a greedy approach
                zip_contents = [[] for _ in range(num_zips)]
                zip_sizes = [0] * num_zips

                # Assign each file to the zip with the smallest current size
                for file_path, file_size in image_files_with_size:
                    smallest_zip_idx = zip_sizes.index(min(zip_sizes))
                    zip_contents[smallest_zip_idx].append(file_path)
                    zip_sizes[smallest_zip_idx] += file_size

                logger.info(
                    f"Estimated zip sizes after distribution: {[size/(1024*1024) for size in zip_sizes]}"
                )

                # Replace image_files with the distributed contents
                image_files = zip_contents
            else:
                # Just one zip file needed
                image_files = [image_files]

            # Create the zip files
            zip_files_created = []

            for i, files_for_this_zip in enumerate(image_files):
                # Skip if no files for this zip
                if not files_for_this_zip:
                    continue

                # Create zip filename
                if num_zips > 1:
                    zip_filename = f"{safe_folder_name}_part{i+1}.zip"
                else:
                    zip_filename = f"{safe_folder_name}.zip"

                zip_path = os.path.join(zipped_dir, zip_filename)

                # Create the zip file
                logger.info(
                    f"Creating zip file: {zip_filename} with {len(files_for_this_zip)} files"
                )

                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in files_for_this_zip:
                        file_name = os.path.basename(file_path)
                        zipf.write(file_path, file_name)
                        logger.info(f"  Added {file_name} to {zip_filename}")

                # Verify the zip size is under the limit
                zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                logger.info(f"  Created {zip_filename}: {zip_size_mb:.2f} MB")

                if zip_size_mb > max_size_mb:
                    logger.warning(
                        f"  Warning: {zip_filename} is {zip_size_mb:.2f} MB, which exceeds the {max_size_mb} MB limit"
                    )

                zip_files_created.append(zip_path)
                logger.info(f"Created zip file: {zip_path}")

            if zip_files_created:
                logger.info(
                    f"Created {len(zip_files_created)} zip files for {folder_name}"
                )
            else:
                logger.warning(f"No zip files were created for {folder_name}")

            return zip_files_created

        except Exception as e:
            logger.error(f"Error creating zip files: {e}")
            raise

    def generate_content_from_mockup(
        self,
        folder_path: str,
        product_type: str,
        instructions: str,
        max_retries: int = 2,
    ) -> Dict[str, str]:
        # product_type parameter is kept for future use when we might customize prompts by product type
        """
        Generate listing content from a mockup image using AI.

        Args:
            folder_path: Path to the product folder
            product_type: Product type
            instructions: Instructions for the LLM
            max_retries: Maximum number of retries with different providers

        Returns:
            Dictionary with title, description, and tags
        """
        # Import sys at the top level to avoid reference errors
        import sys

        # Check if content generator is available
        if not self.content_generator:
            error_msg = "Content generator not available. Check if API keys are set in environment."
            logger.error(error_msg)
            # Print to stderr to ensure it's captured
            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        # Check if the content generator has the required method
        if not hasattr(self.content_generator, "generate_content_from_image"):
            error_msg = "Content generator doesn't support image analysis. Check implementation."
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        # Find the main mockup image in the mocks folder
        mocks_folder = os.path.join(folder_path, "mocks")
        if not os.path.exists(mocks_folder):
            error_msg = f"Mocks folder not found: {mocks_folder}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return {"title": "", "description": "", "tags": []}

        # Look specifically for main.png
        main_mockup = os.path.join(mocks_folder, "main.png")

        # If main.png doesn't exist, look for any main.jpg
        if not os.path.exists(main_mockup):
            main_mockup = os.path.join(mocks_folder, "main.jpg")

        # If neither exists, fall back to any image
        if not os.path.exists(main_mockup):
            import glob

            mockup_images = sorted(
                glob.glob(os.path.join(mocks_folder, "*.jpg"))
                + glob.glob(os.path.join(mocks_folder, "*.png"))
            )

            if not mockup_images:
                error_msg = f"No mockup images found in {mocks_folder}"
                logger.error(error_msg)
                print(error_msg, file=sys.stderr)
                return {"title": "", "description": "", "tags": []}

            # Use the first available image as fallback
            main_mockup = mockup_images[0]
            logger.info(f"main.png not found, using fallback image: {main_mockup}")
        else:
            logger.info(f"Using mockup image: {main_mockup}")

        # Log that we're using the DEFAULT_ETSY_INSTRUCTIONS for Etsy listings
        if instructions == DEFAULT_ETSY_INSTRUCTIONS:
            logger.info("Using DEFAULT_ETSY_INSTRUCTIONS for Etsy listing generation")
        else:
            logger.info("Using custom instructions for Etsy listing generation")

        # Try with the current provider first
        content = self.content_generator.generate_content_from_image(
            main_mockup, instructions
        )

        # Check if we got valid content
        if content and content["title"] and content["description"] and content["tags"]:
            logger.info(
                f"Successfully generated content from mockup: {content['title']}"
            )
            return content

        # If we didn't get valid content, try with alternative providers
        logger.warning(
            "Failed to generate content with primary provider. Trying alternatives..."
        )

        # No alternative providers to try, just log the error
        logger.warning("Content generation failed with Gemini provider")

        # If we get here, all attempts failed
        logger.error("All content generation attempts failed")

        # Return whatever we got from the primary provider, even if incomplete
        return content

    def _extract_product_info(self, folder_path: str, product_type: str) -> Dict:
        """
        Extract product information from a folder.

        Args:
            folder_path: Path to the product folder
            product_type: Product type

        Returns:
            Product information
        """
        info = {}

        try:
            # Count files
            import glob

            # Count images
            image_count = len(
                glob.glob(os.path.join(folder_path, "*.jpg"))
                + glob.glob(os.path.join(folder_path, "*.png"))
            )
            info["num_files"] = image_count

            # Get dimensions of first image
            image_paths = glob.glob(os.path.join(folder_path, "*.jpg")) + glob.glob(
                os.path.join(folder_path, "*.png")
            )
            if image_paths:
                from PIL import Image

                with Image.open(image_paths[0]) as img:
                    info["dimensions"] = f"{img.width}x{img.height}"

            # Get file formats
            formats = set()
            for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
                if glob.glob(os.path.join(folder_path, f"*{ext}")):
                    formats.add(ext.upper().replace(".", ""))

            info["file_formats"] = ", ".join(formats)

            # Extract colors and style from folder name
            folder_name = os.path.basename(folder_path).lower()

            # Common colors
            colors = [
                "red",
                "blue",
                "green",
                "yellow",
                "orange",
                "purple",
                "pink",
                "black",
                "white",
                "gray",
                "brown",
                "teal",
                "turquoise",
                "gold",
                "silver",
            ]
            found_colors = []

            for color in colors:
                if color in folder_name:
                    found_colors.append(color.title())

            if found_colors:
                info["colors"] = ", ".join(found_colors)

            # Common styles
            styles = [
                "abstract",
                "floral",
                "geometric",
                "vintage",
                "modern",
                "minimalist",
                "boho",
                "rustic",
                "tropical",
                "watercolor",
                "hand drawn",
                "digital",
                "vector",
            ]
            found_styles = []

            for style in styles:
                if style in folder_name:
                    found_styles.append(style.title())

            if found_styles:
                info["style"] = ", ".join(found_styles)

            # Common themes
            themes = [
                "nature",
                "animal",
                "flower",
                "plant",
                "landscape",
                "food",
                "holiday",
                "christmas",
                "halloween",
                "easter",
                "birthday",
                "wedding",
                "baby",
                "kids",
                "school",
                "office",
                "home",
                "travel",
                "beach",
                "mountain",
                "forest",
                "ocean",
                "space",
                "science",
                "music",
                "sport",
                "fashion",
                "beauty",
                "health",
                "fitness",
                "yoga",
                "meditation",
                "spiritual",
                "religious",
                "christian",
                "buddhist",
                "hindu",
                "muslim",
                "jewish",
            ]
            found_themes = []

            for theme in themes:
                if theme in folder_name:
                    found_themes.append(theme.title())

            if found_themes:
                info["theme"] = ", ".join(found_themes)

            # Product-specific info
            if product_type == "brush_strokes":
                # Software compatibility
                software = [
                    "procreate",
                    "photoshop",
                    "illustrator",
                    "affinity",
                    "clip studio",
                    "krita",
                    "gimp",
                ]
                found_software = []

                for sw in software:
                    if sw in folder_name:
                        found_software.append(sw.title())

                if found_software:
                    info["software_compatibility"] = ", ".join(found_software)
                else:
                    info["software_compatibility"] = "Procreate, Photoshop"

                # Number of brushes
                info["num_brushes"] = image_count

        except Exception as e:
            logger.error(f"Error extracting product info: {e}")

        return info
