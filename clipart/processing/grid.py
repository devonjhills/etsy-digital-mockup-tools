"""
Module for creating grid layouts.
"""

from typing import List, Tuple
from PIL import Image

from utils.common import (
    setup_logging,
    get_resampling_filter,
    safe_load_image,
)

# Configuration constants
WATERMARK_TEXT_SPACING_FACTOR = 0.3

# Set up logging
logger = setup_logging(__name__)


def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = (2000, 2000),
    padding: int = 30,
) -> Image.Image:
    """
    Create a 2x2 grid of images.

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        grid_size: Size of the grid (width, height)
        padding: Padding between images

    Returns:
        The grid image
    """
    logger.info("Creating 2x2 grid...")

    if not input_image_paths:
        logger.warning("No input images provided for 2x2 grid.")
        return canvas_bg_image

    # Ensure we have a copy of the background
    canvas = canvas_bg_image.copy()

    # Calculate cell size
    grid_width, grid_height = grid_size
    cell_width = (grid_width - (3 * padding)) // 2
    cell_height = (grid_height - (3 * padding)) // 2

    # Load and place images
    for i, img_path in enumerate(input_image_paths[:4]):  # Limit to 4 images
        try:
            # Load image
            img = safe_load_image(img_path, "RGBA")
            if not img:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            # Calculate position
            row = i // 2
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

        except Exception as e:
            logger.error(f"Error processing image {img_path} for 2x2 grid: {e}")

    return canvas


def create_2x3_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = (3000, 2250),
    padding: int = 30,
    title_area: Tuple[int, int, int, int] = None,
) -> Image.Image:
    """
    Create a 2x3 grid of images (6 images total).

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        grid_size: Size of the grid (width, height)
        padding: Padding between images
        title_area: Area to avoid for title (x1, y1, x2, y2)

    Returns:
        The grid image
    """
    logger.info("Creating 2x3 grid...")

    if not input_image_paths:
        logger.warning("No input images provided for 2x3 grid.")
        return canvas_bg_image

    # Ensure we have a copy of the background
    canvas = canvas_bg_image.copy()

    # Calculate cell size
    grid_width, grid_height = grid_size

    # Adjust grid area if title area is provided
    top_padding = padding
    if title_area:
        # Extract title area coordinates - only using y2 for padding
        _, _, _, y2 = title_area
        # Adjust top padding to avoid title area
        top_padding = y2 + padding
        # Adjust available height for grid
        available_height = grid_height - top_padding - padding
    else:
        available_height = grid_height - (2 * padding)

    # Calculate cell dimensions for a 2x3 grid
    cell_width = (grid_width - (3 * padding)) // 2  # 2 columns
    cell_height = (available_height - (2 * padding)) // 3  # 3 rows

    # Load and place images
    for i, img_path in enumerate(input_image_paths[:6]):  # Limit to 6 images
        try:
            # Load image
            img = safe_load_image(img_path, "RGBA")
            if not img:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            # Calculate position
            row = i // 2
            col = i % 2
            x = padding + col * (cell_width + padding)
            y = top_padding + row * (cell_height + padding)

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

        except Exception as e:
            logger.error(f"Error processing image {img_path} for 2x3 grid: {e}")

    return canvas


# Removed duplicate watermarking function - use utils.common.apply_watermark() directly instead
