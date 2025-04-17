"""
Module for managing listing templates.
"""

import os
import json
from typing import Dict, List, Optional
import re

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)


class ListingTemplate:
    """Manage listing templates."""

    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize the listing template manager.

        Args:
            templates_dir: Directory to store templates
        """
        self.templates_dir = templates_dir

        # Create templates directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)

    def save_template(self, name: str, template_data: Dict) -> bool:
        """
        Save a template.

        Args:
            name: Template name
            template_data: Template data

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Sanitize the name
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

            # Add .json extension if not present
            if not safe_name.endswith(".json"):
                safe_name += ".json"

            file_path = os.path.join(self.templates_dir, safe_name)

            with open(file_path, "w") as f:
                json.dump(template_data, f, indent=2)

            logger.info(f"Template saved: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    def load_template(self, name: str) -> Optional[Dict]:
        """
        Load a template.

        Args:
            name: Template name

        Returns:
            Template data or None if not found
        """
        try:
            # Add .json extension if not present
            if not name.endswith(".json"):
                name += ".json"

            file_path = os.path.join(self.templates_dir, name)

            if not os.path.exists(file_path):
                logger.error(f"Template not found: {file_path}")
                return None

            with open(file_path, "r") as f:
                template_data = json.load(f)

            return template_data
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None

    def list_templates(self) -> List[str]:
        """
        List available templates.

        Returns:
            List of template names
        """
        try:
            templates = [
                f for f in os.listdir(self.templates_dir) if f.endswith(".json")
            ]
            return templates
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []

    def delete_template(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Add .json extension if not present
            if not name.endswith(".json"):
                name += ".json"

            file_path = os.path.join(self.templates_dir, name)

            if not os.path.exists(file_path):
                logger.error(f"Template not found: {file_path}")
                return False

            os.remove(file_path)
            logger.info(f"Template deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            return False

    def create_default_templates(self) -> bool:
        """
        Create default templates for different product types.

        Returns:
            True if creation was successful, False otherwise
        """
        try:
            # Pattern template
            pattern_template = {
                "product_type": "pattern",
                "title_template": "{pattern_name} | Seamless Pattern | Digital Paper | Commercial Use | {colors} | {style}",
                "description_template": "# {pattern_name} Seamless Pattern\n\n## INSTANT DOWNLOAD\n\nThis listing is for a digital download of a seamless pattern that you can use for various projects.\n\n## FEATURES\n\n- High-resolution seamless pattern (300 DPI)\n- {dimensions} dimensions\n- {file_formats} file format(s)\n- Commercial use allowed\n\n## WHAT YOU'LL RECEIVE\n\n- {num_files} seamless pattern file(s)\n- License for commercial use\n\n## HOW TO USE\n\nAfter purchase, you'll receive an instant download link. The files can be used with various design software like Photoshop, Illustrator, Canva, etc.\n\n## TERMS OF USE\n\n- Commercial use allowed\n- No redistribution of the original files\n- No reselling of the original files\n\nThank you for visiting my shop! If you have any questions, feel free to contact me.",
                "tags": [
                    "seamless pattern",
                    "digital paper",
                    "background",
                    "scrapbooking",
                    "commercial use",
                    "printable",
                    "digital download",
                    "surface pattern",
                    "fabric design",
                    "wallpaper",
                    "wrapping paper",
                    "craft supply",
                    "digital scrapbook",
                ],
                "taxonomy_id": 2078,  # Digital Prints
                "who_made": "i_did",
                "is_supply": True,
                "when_made": "made_to_order",
                "is_digital": True,
                "is_personalizable": False,
                "personalization_instructions": "",
                "price": 3.32,
                "quantity": 999,
            }

            # Clipart template
            clipart_template = {
                "product_type": "clipart",
                "title_template": "{clipart_name} | Digital Clipart | Commercial Use | PNG with Transparent Background | {style} | {theme}",
                "description_template": "# {clipart_name} Digital Clipart\n\n## INSTANT DOWNLOAD\n\nThis listing is for a digital download of clipart elements that you can use for various projects.\n\n## FEATURES\n\n- High-resolution PNG files with transparent backgrounds (300 DPI)\n- {dimensions} dimensions\n- Commercial use allowed\n\n## WHAT YOU'LL RECEIVE\n\n- {num_files} PNG file(s) with transparent backgrounds\n- License for commercial use\n\n## HOW TO USE\n\nAfter purchase, you'll receive an instant download link. The files can be used with various design software like Photoshop, Illustrator, Canva, etc.\n\n## TERMS OF USE\n\n- Commercial use allowed\n- No redistribution of the original files\n- No reselling of the original files\n\nThank you for visiting my shop! If you have any questions, feel free to contact me.",
                "tags": [
                    "digital clipart",
                    "clip art",
                    "transparent png",
                    "commercial use",
                    "digital download",
                    "printable",
                    "scrapbooking",
                    "digital sticker",
                    "craft supply",
                    "graphic design",
                    "illustration",
                    "digital art",
                    "design element",
                ],
                "materials": [
                    "digital file",
                    "digital download",
                    "digital clipart",
                    "transparent png",
                ],
                "taxonomy_id": 6844,  # Digital Clip Art
                "who_made": "i_did",
                "is_supply": True,
                "when_made": "made_to_order",
                "is_digital": True,
                "is_personalizable": False,
                "personalization_instructions": "",
                "price": 3.32,
                "quantity": 999,
            }

            # Wall art template
            wall_art_template = {
                "product_type": "wall_art",
                "title_template": "{art_name} | Printable Wall Art | Digital Download | {style} | {theme} | Home Decor",
                "description_template": "# {art_name} Printable Wall Art\n\n## INSTANT DOWNLOAD\n\nThis listing is for a digital download of printable wall art that you can print at home or at a local print shop.\n\n## FEATURES\n\n- High-resolution files (300 DPI)\n- {dimensions} dimensions\n- {file_formats} file format(s)\n\n## WHAT YOU'LL RECEIVE\n\n- {num_files} printable file(s)\n- Different sizes for easy printing\n\n## HOW TO USE\n\nAfter purchase, you'll receive an instant download link. You can print the files at home or at a local print shop.\n\n## TERMS OF USE\n\n- Personal use only\n- No redistribution of the original files\n- No reselling of the original files\n\nThank you for visiting my shop! If you have any questions, feel free to contact me.",
                "tags": [
                    "printable wall art",
                    "digital download",
                    "home decor",
                    "wall art",
                    "printable art",
                    "instant download",
                    "digital print",
                    "wall decor",
                    "art print",
                    "poster",
                    "modern art",
                    "minimalist art",
                    "gallery wall",
                ],
                "materials": [
                    "digital file",
                    "digital download",
                    "printable art",
                    "digital print",
                ],
                "taxonomy_id": 2429,  # Digital Prints
                "who_made": "i_did",
                "is_supply": False,
                "when_made": "made_to_order",
                "is_digital": True,
                "is_personalizable": False,
                "personalization_instructions": "",
                "price": 5.99,
                "quantity": 999,
            }

            # Save templates
            self.save_template("pattern", pattern_template)
            self.save_template("clipart", clipart_template)
            self.save_template("wall_art", wall_art_template)

            return True
        except Exception as e:
            logger.error(f"Error creating default templates: {e}")
            return False

    def get_template_for_product_type(self, product_type: str) -> Optional[Dict]:
        """
        Get a template for a specific product type.

        Args:
            product_type: Product type

        Returns:
            Template data or None if not found
        """
        try:
            # Try to load the template
            template = self.load_template(product_type)

            if template:
                return template

            # If not found, create default templates and try again
            self.create_default_templates()
            return self.load_template(product_type)
        except Exception as e:
            logger.error(f"Error getting template for product type: {e}")
            return None
