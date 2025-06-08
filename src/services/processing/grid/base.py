"""
Base grid processor that unifies clipart and pattern grid generation.
"""

import os
import glob
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image

from src.utils.common import setup_logging, ensure_dir_exists
from src.utils.grid_utils import GridCreator

logger = setup_logging(__name__)


class GridProcessor:
    """Unified grid processor for all product types."""
    
    def __init__(self, product_type: str = "generic"):
        self.product_type = product_type
        self.grid_creator = GridCreator()
    
    def create_2x2_grid(self, image_paths: List[str], output_path: str,
                       grid_size: Tuple[int, int] = (2000, 2000),
                       padding: int = 30, background_name: str = "canvas.png") -> Optional[str]:
        """
        Create a 2x2 grid suitable for clipart display.
        
        Args:
            image_paths: List of image paths to include
            output_path: Where to save the grid
            grid_size: Size of the output grid
            padding: Padding between images
            background_name: Name of background image
            
        Returns:
            Path to created grid or None if failed
        """
        try:
            # Load background
            background = self.grid_creator.load_background(background_name, grid_size)
            if not background:
                background = self.grid_creator.create_fallback_background(grid_size)
            
            # Create grid
            grid_image = self.grid_creator.create_2x2_grid(
                image_paths, grid_size, padding, background
            )
            
            # Ensure output directory exists
            ensure_dir_exists(os.path.dirname(output_path))
            
            # Save grid
            grid_image.save(output_path, "PNG")
            logger.info(f"2x2 grid saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating 2x2 grid: {e}")
            return None
    
    def create_2x3_grid(self, image_paths: List[str], output_path: str,
                       grid_size: Tuple[int, int] = (3000, 2250),
                       padding: int = 30, background_name: str = "canvas.png",
                       title_area: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
        """
        Create a 2x3 grid suitable for clipart with title area.
        
        Args:
            image_paths: List of image paths to include
            output_path: Where to save the grid
            grid_size: Size of the output grid
            padding: Padding between images
            background_name: Name of background image
            title_area: Area reserved for title (x1, y1, x2, y2)
            
        Returns:
            Path to created grid or None if failed
        """
        try:
            # Load background
            background = self.grid_creator.load_background(background_name, grid_size)
            if not background:
                background = self.grid_creator.create_fallback_background(grid_size)
            
            # Create grid
            grid_image = self.grid_creator.create_2x3_grid(
                image_paths, grid_size, padding, background, title_area
            )
            
            # Ensure output directory exists
            ensure_dir_exists(os.path.dirname(output_path))
            
            # Save grid
            grid_image.save(output_path, "PNG")
            logger.info(f"2x3 grid saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating 2x3 grid: {e}")
            return None
    
    def create_4x3_grid_with_borders(self, input_folder: str, 
                                   border_width: int = 15,
                                   watermark_text: str = "© digital veil") -> Optional[str]:
        """
        Create a 4x3 grid with borders suitable for patterns.
        
        Args:
            input_folder: Folder containing images
            border_width: Width of borders between images
            watermark_text: Text for watermark
            
        Returns:
            Path to created grid or None if failed
        """
        return self.grid_creator.create_4x3_grid_with_borders(
            input_folder, border_width, watermark_text
        )
    
    def create_adaptive_grid(self, image_paths: List[str], output_path: str,
                           max_images: int = 12, preferred_aspect: float = 1.0) -> Optional[str]:
        """
        Create an adaptive grid that chooses the best layout based on image count.
        
        Args:
            image_paths: List of image paths
            output_path: Where to save the grid
            max_images: Maximum number of images to include
            preferred_aspect: Preferred aspect ratio for the grid
            
        Returns:
            Path to created grid or None if failed
        """
        image_count = min(len(image_paths), max_images)
        
        if image_count <= 4:
            return self.create_2x2_grid(image_paths[:4], output_path)
        elif image_count <= 6:
            return self.create_2x3_grid(image_paths[:6], output_path)
        else:
            # For more images, use the bordered grid
            temp_folder = os.path.dirname(output_path)
            return self.create_4x3_grid_with_borders(temp_folder)
    
    def batch_create_grids(self, input_folder: str, grid_types: List[str] = None) -> Dict[str, List[str]]:
        """
        Create multiple grid types for a folder.
        
        Args:
            input_folder: Folder containing images
            grid_types: List of grid types to create ["2x2", "2x3", "4x3_borders"]
            
        Returns:
            Dictionary mapping grid type to list of created files
        """
        if grid_types is None:
            grid_types = ["2x2", "2x3"] if self.product_type == "clipart" else ["4x3_borders"]
        
        results = {}
        output_folder = os.path.join(input_folder, "mocks")
        ensure_dir_exists(output_folder)
        
        # Get image files
        image_extensions = ["*.png", "*.jpg", "*.jpeg"]
        image_paths = []
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(input_folder, ext)))
        
        if not image_paths:
            logger.warning(f"No images found in {input_folder}")
            return results
        
        for grid_type in grid_types:
            created_files = []
            
            if grid_type == "2x2":
                # Create multiple 2x2 grids if we have many images
                for i in range(0, len(image_paths), 4):
                    batch = image_paths[i:i+4]
                    if batch:
                        output_path = os.path.join(output_folder, f"grid_2x2_{i//4 + 1:02d}.png")
                        if self.create_2x2_grid(batch, output_path):
                            created_files.append(output_path)
            
            elif grid_type == "2x3":
                # Create multiple 2x3 grids if we have many images  
                for i in range(0, len(image_paths), 6):
                    batch = image_paths[i:i+6]
                    if batch:
                        output_path = os.path.join(output_folder, f"grid_2x3_{i//6 + 1:02d}.png")
                        if self.create_2x3_grid(batch, output_path):
                            created_files.append(output_path)
            
            elif grid_type == "4x3_borders":
                result = self.create_4x3_grid_with_borders(input_folder)
                if result:
                    created_files.append(result)
            
            results[grid_type] = created_files
        
        return results