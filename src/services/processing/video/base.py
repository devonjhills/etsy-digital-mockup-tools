"""
Unified video processor for all product types.
"""

import os
from typing import List, Optional

from utils.common import setup_logging, ensure_dir_exists
from utils.video_utils import VideoCreator

logger = setup_logging(__name__)


class VideoProcessor:
    """Unified video processor for all product types."""
    
    def __init__(self, product_type: str = "generic"):
        self.product_type = product_type
        self.video_creator = VideoCreator()
    
    def create_product_showcase_video(self, input_folder: str) -> Optional[str]:
        """
        Create a product showcase video based on product type.
        
        Args:
            input_folder: Folder containing images
            
        Returns:
            Path to created video or None if failed
        """
        # Ensure videos folder exists
        videos_folder = os.path.join(input_folder, "videos")
        ensure_dir_exists(videos_folder)
        
        if self.product_type == "clipart":
            return self._create_clipart_showcase(input_folder, videos_folder)
        elif self.product_type == "pattern":
            return self._create_pattern_showcase(input_folder, videos_folder)
        else:
            return self._create_generic_showcase(input_folder, videos_folder)
    
    def _create_clipart_showcase(self, input_folder: str, videos_folder: str) -> Optional[str]:
        """Create a clipart showcase video from grid mockups."""
        # Look for grid mockups in mocks folder
        mocks_folder = os.path.join(input_folder, "mocks")
        if not os.path.exists(mocks_folder):
            logger.warning(f"Mocks folder not found: {mocks_folder}")
            return None
        
        # Find grid mockups
        grid_files = []
        for filename in os.listdir(mocks_folder):
            if "grid" in filename.lower() and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                grid_files.append(os.path.join(mocks_folder, filename))
        
        if not grid_files:
            logger.warning("No grid mockups found for clipart showcase")
            return None
        
        output_path = os.path.join(videos_folder, "clipart_showcase.mp4")
        success = self.video_creator.create_slideshow_video(sorted(grid_files), output_path)
        return output_path if success else None
    
    def _create_pattern_showcase(self, input_folder: str, videos_folder: str) -> Optional[str]:
        """Create a pattern showcase video using progressive tiling animation."""
        # Look for a pattern image to tile
        import glob
        
        # Try to find pattern images in input folder
        pattern_files = glob.glob(os.path.join(input_folder, "*.jpg"))
        if not pattern_files:
            logger.warning(f"No pattern images found in {input_folder}")
            return None
        
        # Use the first pattern image
        pattern_path = pattern_files[0]
        logger.info(f"Using pattern for tiling video: {os.path.basename(pattern_path)}")
        
        output_path = os.path.join(videos_folder, "pattern_tiling.mp4")
        success = self.video_creator.create_tiling_video(pattern_path, output_path)
        return output_path if success else None
    
    def _create_generic_showcase(self, input_folder: str, videos_folder: str) -> Optional[str]:
        """Create a generic showcase video from available images."""
        # Get all image files
        image_extensions = ["*.png", "*.jpg", "*.jpeg"]
        image_paths = []
        
        import glob
        for ext in image_extensions:
            image_paths.extend(glob.glob(os.path.join(input_folder, ext)))
        
        if not image_paths:
            logger.warning(f"No images found in {input_folder}")
            return None
        
        output_path = os.path.join(videos_folder, "product_showcase.mp4")
        success = self.video_creator.create_slideshow_video(sorted(image_paths)[:8], output_path)
        return output_path if success else None