"""
Unified Etsy content generation to eliminate code duplication across processors.

This module extracts the common Etsy content generation logic that was duplicated
across all processor files with 90% redundancy.
"""

import os
from typing import Dict, Any, Optional
from src.utils.ai_utils import generate_content_with_ai, parse_etsy_listing_response
from src.services.etsy.constants import DEFAULT_ETSY_INSTRUCTIONS
from src.utils.file_operations import find_files_by_extension


class EtsyContentGenerator:
    """Centralized Etsy content generation for all product types."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def generate_content_for_product(
        self, 
        input_dir: str, 
        ai_provider: str, 
        product_type: str,
        category: str = "Digital",
        subcategory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Etsy listing content for any product type.
        
        Args:
            input_dir: Path to product input directory
            ai_provider: AI provider to use for content generation
            product_type: Type of product (pattern, clipart, etc.)
            category: Etsy category (default: "Digital")
            subcategory: Etsy subcategory (optional)
        
        Returns:
            Dictionary containing title, description, and tags
        """
        if not ai_provider:
            return {}
        
        try:
            # Find main mockup image
            main_mockup = self._find_main_mockup(input_dir)
            if not main_mockup:
                if self.logger:
                    self.logger.warning("No main mockup found for content generation")
                return {}
            
            # Generate AI content
            ai_response = generate_content_with_ai(
                ai_provider,
                DEFAULT_ETSY_INSTRUCTIONS,
                main_mockup
            )
            
            # Parse the response
            parsed_content = parse_etsy_listing_response(ai_response)
            title = parsed_content['title']
            description = parsed_content['description']
            tags_text = parsed_content['tags']
            
            # Convert tags to list (max 13 for Etsy)
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()][:13]
            
            # Count images in product
            image_count = self._count_product_images(input_dir)
            
            # Build result
            result = {
                "title": title,
                "description": description,
                "tags": tags,
                "category": category,
                "image_count": image_count,
                "image_analyzed": main_mockup,
            }
            
            # Add subcategory if provided
            if subcategory:
                result["subcategory"] = subcategory
            
            return result
            
        except Exception as e:
            error_msg = f"Content generation failed: {e}"
            if self.logger:
                self.logger.error(error_msg)
            return {"error": str(e)}
    
    def _find_main_mockup(self, input_dir: str) -> Optional[str]:
        """Find the main mockup image for content generation."""
        # Try main.png first
        main_mockup = os.path.join(input_dir, "mocks", "main.png")
        if os.path.exists(main_mockup):
            return main_mockup
        
        # Fallback to main.jpg
        main_mockup = os.path.join(input_dir, "mocks", "main.jpg")
        if os.path.exists(main_mockup):
            return main_mockup
        
        return None
    
    def _count_product_images(self, input_dir: str) -> int:
        """Count the number of product images (excluding mockups)."""
        try:
            image_files = find_files_by_extension(input_dir, ['.png', '.jpg', '.jpeg'])
            # Exclude files in mocks directory
            product_images = [
                f for f in image_files 
                if '/mocks/' not in f and '\\mocks\\' not in f
            ]
            return len(product_images)
        except Exception:
            return 0


def generate_etsy_content(
    input_dir: str, 
    ai_provider: str, 
    product_type: str,
    category: str = "Digital",
    subcategory: Optional[str] = None,
    logger=None
) -> Dict[str, Any]:
    """
    Convenience function for generating Etsy content.
    
    This is a simple wrapper around EtsyContentGenerator for backward compatibility
    and ease of use in processor files.
    """
    generator = EtsyContentGenerator(logger)
    return generator.generate_content_for_product(
        input_dir, ai_provider, product_type, category, subcategory
    )