"""
Main module for Etsy integration.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Tuple

from utils.common import setup_logging
from etsy.auth import EtsyAuth
from etsy.listings import EtsyListings
from etsy.templates import ListingTemplate
from etsy.content import ContentGenerator

# Set up logging
logger = setup_logging(__name__)


class EtsyIntegration:
    """Main class for Etsy integration."""

    def __init__(
        self,
        etsy_api_key: str,
        etsy_api_secret: str,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-pro-exp-03-25",
        templates_dir: str = "templates",
    ):
        """
        Initialize the Etsy integration.

        Args:
            etsy_api_key: Etsy API key
            etsy_api_secret: Etsy API secret
            gemini_api_key: Gemini API key (optional)
            gemini_model: Gemini model name to use
            templates_dir: Directory to store templates
        """
        self.auth = EtsyAuth(etsy_api_key, etsy_api_secret)
        self.listings = EtsyListings(self.auth)
        self.templates = ListingTemplate(templates_dir)

        # Initialize content generator if API key is provided
        self.content_generator = None
        if gemini_api_key:
            self.content_generator = ContentGenerator(gemini_api_key, gemini_model)

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

        # Add additional info based on folder contents
        product_info.update(self._extract_product_info(folder_path, product_type))

        # Use custom values if provided, otherwise use template values
        if custom_title:
            title = custom_title
        else:
            # Use template with basic substitution
            title_template = template.get("title_template", "{name}")
            title = title_template.format(name=product_name, **product_info)

        if custom_description:
            description = custom_description
        else:
            description_template = template.get(
                "description_template", "# {name}\n\nDigital product for download."
            )
            description = description_template.format(name=product_name, **product_info)

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
            for i, image_path in enumerate(
                image_paths[:10]
            ):  # Etsy allows max 10 images
                image_result = self.listings.upload_listing_image(
                    listing_id=listing_id, image_path=image_path, rank=i + 1
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

    def generate_content_from_mockup(
        self, folder_path: str, product_type: str, instructions: str
    ) -> Dict[str, str]:
        """
        Generate listing content from a mockup image using Gemini API.

        Args:
            folder_path: Path to the product folder
            product_type: Product type
            instructions: Instructions for the LLM

        Returns:
            Dictionary with title, description, and tags
        """
        # Check if content generator is available
        if not self.content_generator:
            error_msg = "Content generator not available. Check if GEMINI_API_KEY is set in environment."
            logger.error(error_msg)
            # Print to stderr to ensure it's captured
            import sys

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

        # Generate content from the image
        content = self.content_generator.generate_content_from_image(
            main_mockup, instructions
        )
        logger.info(f"Generated content from mockup: {content['title']}")

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
