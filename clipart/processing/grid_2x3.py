"""
Module for creating a 2x3 grid layout (2 columns, 3 rows).
"""

from typing import List, Tuple
from PIL import Image

from utils.common import (
    setup_logging,
    get_resampling_filter,
    safe_load_image,
)

# Set up logging
logger = setup_logging(__name__)


def create_2x3_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = (2000, 2000),
    padding: int = 30,
) -> Image.Image:
    """
    Create a 2x3 grid of images (2 columns, 3 rows).

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        grid_size: Size of the grid (width, height)
        padding: Padding between images

    Returns:
        The grid image
    """
    logger.info("Creating 2x3 grid (2 columns, 3 rows)...")

    if not input_image_paths:
        logger.warning("No input images provided for 2x3 grid.")
        return canvas_bg_image

    # Ensure we have a copy of the background
    canvas = canvas_bg_image.copy()

    # Calculate cell size
    grid_width, grid_height = grid_size
    cell_width = (grid_width - (3 * padding)) // 2  # 2 columns
    cell_height = (grid_height - (4 * padding)) // 3  # 3 rows

    # Load and place images
    for i, img_path in enumerate(input_image_paths[:6]):  # Limit to 6 images
        try:
            # Load image
            img = safe_load_image(img_path, "RGBA")
            if not img:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            # Calculate position
            row = i // 2  # 2 columns
            col = i % 2
            x = padding + col * (cell_width + padding)
            y = padding + row * (cell_height + padding)

            # Resize image to fit cell while maintaining aspect ratio
            img_aspect = img.width / img.height if img.height > 0 else 1

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

            img_resized = img.resize((img_width, img_height), get_resampling_filter())

            # Center in cell
            x_centered = x + (cell_width - img_width) // 2
            y_centered = y + (cell_height - img_height) // 2

            # Shadow removed as requested

            # Paste image
            canvas.paste(img_resized, (x_centered, y_centered), img_resized)

            logger.info(f"Placed image {i+1} at position ({col}, {row}): {img_path}")

        except Exception as e:
            logger.error(f"Error processing image {img_path} for 2x3 grid: {e}")

    return canvas
