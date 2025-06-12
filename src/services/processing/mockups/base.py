"""
Base mockup processor that unifies clipart and pattern mockup generation.
"""

import os
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image

from src.utils.common import setup_logging, ensure_dir_exists

logger = setup_logging(__name__)


class MockupProcessor:
    """Unified mockup processor for all product types."""
    
    def __init__(self, product_type: str = "generic"):
        self.product_type = product_type
    
    def create_main_mockup(self, input_folder: str, title: str) -> Optional[str]:
        """
        Create a main mockup based on product type.
        
        Args:
            input_folder: Folder containing source images
            title: Title for the mockup
            
        Returns:
            Path to created mockup or None if failed
        """
        if self.product_type == "clipart":
            return self._create_clipart_main_mockup(input_folder, title)
        elif self.product_type == "pattern":
            return self._create_pattern_main_mockup(input_folder, title)
        else:
            return self._create_generic_main_mockup(input_folder, title)
    
    def _create_clipart_main_mockup(self, input_folder: str, title: str) -> Optional[str]:
        """Create main mockup for clipart."""
        try:
            from src.products.clipart.mockups import create_square_mockup
            
            mockup_dir = os.path.join(input_folder, "mocks")
            ensure_dir_exists(mockup_dir)
            
            # Find images
            image_files = []
            for ext in ['.png', '.jpg', '.jpeg']:
                image_files.extend([
                    os.path.join(input_folder, f)
                    for f in os.listdir(input_folder)
                    if f.lower().endswith(ext) and os.path.isfile(os.path.join(input_folder, f))
                ])
            
            if not image_files:
                logger.warning("No images found for clipart main mockup")
                return None
            
            # Create background
            canvas_bg = Image.new("RGB", (3000, 2250), "white")
            
            # Generate subtitles
            subtitle_top = f"{len(image_files)} clip arts • Commercial Use"
            subtitle_bottom = "300 DPI • Transparent PNG"
            
            # Create mockup
            result = create_square_mockup(
                input_image_paths=image_files,
                canvas_bg_image=canvas_bg,
                title=title,
                subtitle_top=subtitle_top,
                subtitle_bottom=subtitle_bottom,
                grid_size=(3000, 2250),
                padding=30
            )
            
            # Handle the return value
            if isinstance(result, tuple):
                mockup_image, _ = result
            else:
                mockup_image = result
            
            # Save the mockup
            output_path = os.path.join(mockup_dir, "main.png")
            mockup_image.save(output_path)
            
            logger.info(f"Clipart main mockup created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating clipart main mockup: {e}")
            return None
    
    def _create_pattern_main_mockup(self, input_folder: str, title: str) -> Optional[str]:
        """Create main mockup for patterns."""
        try:
            from src.products.pattern.dynamic_main_mockup import create_main_mockup
            
            result_file = create_main_mockup(input_folder, title)
            if result_file:
                logger.info(f"Pattern main mockup created: {result_file}")
            return result_file
            
        except Exception as e:
            logger.error(f"Error creating pattern main mockup: {e}")
            return None
    
    def _create_generic_main_mockup(self, input_folder: str, title: str) -> Optional[str]:
        """Create a generic main mockup."""
        try:
            mockup_dir = os.path.join(input_folder, "mocks")
            ensure_dir_exists(mockup_dir)
            
            # Find images
            image_files = []
            for ext in ['.png', '.jpg', '.jpeg']:
                image_files.extend([
                    os.path.join(input_folder, f)
                    for f in os.listdir(input_folder)
                    if f.lower().endswith(ext) and os.path.isfile(os.path.join(input_folder, f))
                ])
            
            if not image_files:
                logger.warning("No images found for generic main mockup")
                return None
            
            # Create a simple collage
            from src.utils.grid_utils import GridCreator
            grid_creator = GridCreator()
            
            output_path = os.path.join(mockup_dir, "main.png")
            
            # Create a simple 2x2 grid as fallback
            background = grid_creator.load_background("canvas.png", (2000, 2000))
            grid_image = grid_creator.create_2x2_grid(
                image_paths=image_files[:4],
                grid_size=(2000, 2000),
                background=background
            )
            grid_image.save(output_path, "PNG")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating generic main mockup: {e}")
            return None