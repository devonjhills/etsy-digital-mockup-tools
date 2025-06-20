"""
Unified grid creation utilities for all product types.
"""

import os
import glob
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image

from src.utils.common import (
    setup_logging,
    get_resampling_filter,
    safe_load_image,
    apply_watermark,
    get_asset_path,
    ensure_dir_exists
)

logger = setup_logging(__name__)


class GridCreator:
    """Unified grid creator for different product types."""
    
    def __init__(self, background_image: Optional[Image.Image] = None):
        self.background_image = background_image
    
    def load_background(self, canvas_name: str = "canvas.png", size: Tuple[int, int] = None) -> Optional[Image.Image]:
        """
        Load a background image from assets.
        
        Args:
            canvas_name: Name of the canvas file
            size: Optional size to resize to
            
        Returns:
            Background image or None
        """
        canvas_path = get_asset_path(canvas_name)
        if not canvas_path:
            logger.warning(f"Background '{canvas_name}' not found in assets")
            return None
        
        try:
            bg = Image.open(canvas_path).convert("RGBA")
            if size:
                bg = bg.resize(size, get_resampling_filter())
            return bg
        except Exception as e:
            logger.error(f"Error loading background {canvas_name}: {e}")
            return None
    
    def create_fallback_background(self, size: Tuple[int, int], color: Tuple[int, int, int] = (248, 248, 248)) -> Image.Image:
        """Create a fallback solid color background."""
        return Image.new("RGBA", size, color)
    
    def calculate_cell_size(self, grid_size: Tuple[int, int], rows: int, cols: int, padding: int) -> Tuple[int, int]:
        """
        Calculate cell size for a grid.
        
        Args:
            grid_size: Total grid size (width, height)
            rows: Number of rows
            cols: Number of columns
            padding: Padding between cells
            
        Returns:
            Cell size (width, height)
        """
        grid_width, grid_height = grid_size
        cell_width = (grid_width - (cols + 1) * padding) // cols
        cell_height = (grid_height - (rows + 1) * padding) // rows
        return cell_width, cell_height
    
    def fit_image_to_cell(self, image: Image.Image, cell_size: Tuple[int, int]) -> Image.Image:
        """
        Resize an image to fit within a cell while maintaining aspect ratio.
        
        Args:
            image: The image to resize
            cell_size: Size of the cell (width, height)
            
        Returns:
            Resized image
        """
        cell_width, cell_height = cell_size
        img_aspect = image.width / image.height if image.height > 0 else 1
        
        if img_aspect >= 1:  # Wider than tall
            img_width = cell_width
            img_height = int(img_width / img_aspect)
            if img_height > cell_height:
                img_height = cell_height
                img_width = int(img_height * img_aspect)
        else:  # Taller than wide
            img_height = cell_height
            img_width = int(img_height * img_aspect)
            if img_width > cell_width:
                img_width = cell_width
                img_height = int(img_width / img_aspect)
        
        return image.resize((img_width, img_height), get_resampling_filter())
    
    def place_image_in_grid(self, canvas: Image.Image, image: Image.Image, 
                           position: Tuple[int, int], cell_size: Tuple[int, int]):
        """
        Place an image in the grid at a specific position.
        
        Args:
            canvas: The canvas to draw on
            image: The image to place
            position: Grid position (row, col)
            cell_size: Size of each cell
        """
        row, col = position
        cell_width, cell_height = cell_size
        
        # Calculate actual position on canvas
        x = col * (cell_width + 30) + 30  # 30 is default padding
        y = row * (cell_height + 30) + 30
        
        # Resize image to fit cell
        fitted_image = self.fit_image_to_cell(image, cell_size)
        
        # Center in cell
        x_centered = x + (cell_width - fitted_image.width) // 2
        y_centered = y + (cell_height - fitted_image.height) // 2
        
        # Paste image
        if fitted_image.mode == "RGBA":
            canvas.paste(fitted_image, (x_centered, y_centered), fitted_image)
        else:
            canvas.paste(fitted_image, (x_centered, y_centered))
    
    def create_2x2_grid(self, image_paths: List[str], grid_size: Tuple[int, int] = (2000, 2000), 
                       padding: int = 30, background: Optional[Image.Image] = None) -> Image.Image:
        """
        Create a 2x2 grid of images.
        
        Args:
            image_paths: List of image paths
            grid_size: Size of the grid
            padding: Padding between images
            background: Optional background image
            
        Returns:
            Grid image
        """
        logger.info("Creating 2x2 grid...")
        
        if not image_paths:
            logger.warning("No image paths provided for 2x2 grid")
            return self.create_fallback_background(grid_size)
        
        # Use provided background or create fallback
        if background:
            canvas = background.copy()
        else:
            canvas = self.create_fallback_background(grid_size)
        
        cell_width, cell_height = self.calculate_cell_size(grid_size, 2, 2, padding)
        
        for i, img_path in enumerate(image_paths[:4]):
            try:
                img = safe_load_image(img_path, "RGBA")
                if not img:
                    logger.warning(f"Failed to load image: {img_path}")
                    continue
                
                row = i // 2
                col = i % 2
                x = padding + col * (cell_width + padding)
                y = padding + row * (cell_height + padding)
                
                fitted_img = self.fit_image_to_cell(img, (cell_width, cell_height))
                x_centered = x + (cell_width - fitted_img.width) // 2
                y_centered = y + (cell_height - fitted_img.height) // 2
                
                canvas.paste(fitted_img, (x_centered, y_centered), fitted_img)
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
        
        return canvas
    
    def create_2x3_grid(self, image_paths: List[str], grid_size: Tuple[int, int] = (3000, 2250),
                       padding: int = 30, background: Optional[Image.Image] = None,
                       title_area: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """
        Create a 2x3 grid of images (6 images total).
        
        Args:
            image_paths: List of image paths
            grid_size: Size of the grid
            padding: Padding between images
            background: Optional background image
            title_area: Area to avoid for title (x1, y1, x2, y2)
            
        Returns:
            Grid image
        """
        logger.info("Creating 2x3 grid...")
        
        if not image_paths:
            logger.warning("No image paths provided for 2x3 grid")
            return self.create_fallback_background(grid_size)
        
        # Use provided background or create fallback
        if background:
            canvas = background.copy()
        else:
            canvas = self.create_fallback_background(grid_size)
        
        # Adjust for title area
        top_padding = padding
        available_height = grid_size[1] - (2 * padding)
        
        if title_area:
            _, _, _, y2 = title_area
            top_padding = y2 + padding
            available_height = grid_size[1] - top_padding - padding
        
        # Calculate cell dimensions for 2x3 grid
        cell_width = (grid_size[0] - (3 * padding)) // 2  # 2 columns
        cell_height = (available_height - (2 * padding)) // 3  # 3 rows
        
        for i, img_path in enumerate(image_paths[:6]):
            try:
                img = safe_load_image(img_path, "RGBA")
                if not img:
                    logger.warning(f"Failed to load image: {img_path}")
                    continue
                
                row = i // 2
                col = i % 2
                x = padding + col * (cell_width + padding)
                y = top_padding + row * (cell_height + padding)
                
                fitted_img = self.fit_image_to_cell(img, (cell_width, cell_height))
                x_centered = x + (cell_width - fitted_img.width) // 2
                y_centered = y + (cell_height - fitted_img.height) // 2
                
                canvas.paste(fitted_img, (x_centered, y_centered), fitted_img)
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
        
        return canvas
    
    def create_4x3_grid_with_borders(self, input_folder: str, border_width: int = 15,
                                   watermark_text: str = "© digital veil") -> Optional[str]:
        """
        Create a 4x3 grid with borders and watermark.
        
        Args:
            input_folder: Path to input folder with images
            border_width: Width of borders between images
            watermark_text: Text for watermark
            
        Returns:
            Path to created grid file or None if failed
        """
        logger.info("Creating 4x3 grid with borders...")
        
        output_folder = os.path.join(input_folder, "mocks")
        ensure_dir_exists(output_folder)
        
        images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
        if not images:
            logger.warning("No images found for grid mockup")
            return None
        
        images_to_place = images[:12]  # Limit to 12 images
        grid_rows, grid_cols = 3, 4
        
        # Calculate average aspect ratio
        avg_aspect = 1.0
        try:
            img_samples = [Image.open(img) for img in images_to_place[:3]]
            if img_samples:
                valid_aspects = [img.width / img.height for img in img_samples if img.height > 0]
                if valid_aspects:
                    avg_aspect = sum(valid_aspects) / len(valid_aspects)
        except Exception as e:
            logger.warning(f"Could not determine average aspect ratio: {e}")
        
        # Calculate grid dimensions
        grid_width = 3000
        cell_width = (grid_width - (grid_cols + 1) * border_width) // grid_cols
        cell_height = int(cell_width / avg_aspect) if avg_aspect > 0 else cell_width
        grid_height = (cell_height * grid_rows) + ((grid_rows + 1) * border_width)
        
        if cell_width <= 0 or cell_height <= 0:
            logger.error(f"Invalid cell dimensions: {cell_width}x{cell_height}")
            return None
        
        # Create background
        background = self.load_background("canvas.png", (grid_width, grid_height))
        if not background:
            logger.warning("Using white background")
            background = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))
        else:
            background = background.convert("RGB")
        
        # Place images
        for i, img_path in enumerate(images_to_place):
            try:
                img = Image.open(img_path).convert("RGB")
                img = img.resize((cell_width, cell_height), get_resampling_filter())
                row_index = i // grid_cols
                col_index = i % grid_cols
                x_pos = border_width + col_index * (cell_width + border_width)
                y_pos = border_width + row_index * (cell_height + border_width)
                background.paste(img, (x_pos, y_pos))
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
        
        # Add watermark using unified function
        try:
            background_rgba = background.convert("RGBA")
            watermarked = apply_watermark(
                image=background_rgba,
                text=watermark_text,
                font_name="DSMarkerFelt",
                font_size=80,
                text_color=(255, 255, 255),
                opacity=128,
                diagonal_spacing=400,
            )
            final_image = watermarked.convert("RGB")
        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            final_image = background
        
        # Save result
        try:
            output_path = os.path.join(output_folder, "grid_mockup_with_borders.jpg")
            final_image.save(output_path, "JPEG", quality=95)
            logger.info(f"Grid mockup saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving grid mockup: {e}")
            return None


def apply_watermark_to_grid(grid_path: str, logger=None) -> Optional[str]:
    """
    Apply watermark to a grid mockup using unified watermarking.
    
    This function was extracted to eliminate 100% duplication between
    clipart and border_clipart processors.
    
    Args:
        grid_path: Path to the grid image file
        logger: Optional logger instance
        
    Returns:
        Path to watermarked grid or None if failed
    """
    try:
        # Load the grid image
        grid_image = Image.open(grid_path)
        
        # Apply watermark using unified function
        watermarked_image = apply_watermark(
            image=grid_image,
            text="digital veil",
            font_name="Clattering",
            font_size=50,  # Larger font for better visibility
            text_color=(80, 80, 80),  # Darker color for better contrast
            opacity=110,   # Higher opacity for more visibility
            diagonal_spacing=400  # Closer spacing for better coverage
        )
        
        # Save watermarked version (overwrite original)
        watermarked_image.convert("RGB").save(grid_path, "PNG", quality=95, optimize=True)
        
        if logger:
            logger.info(f"Applied watermark to grid: {grid_path}")
        
        return grid_path
        
    except Exception as e:
        error_msg = f"Failed to apply watermark to grid {grid_path}: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        return None