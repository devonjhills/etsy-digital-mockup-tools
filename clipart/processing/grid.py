"""
Module for creating grid layouts.
"""

from typing import List, Tuple
from PIL import Image, ImageDraw

from utils.common import (
    setup_logging,
    get_resampling_filter,
    safe_load_image,
    apply_watermark,
)
from clipart.config import WATERMARK_TEXT_SPACING_FACTOR

# Set up logging
logger = setup_logging(__name__)


def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = (2000, 2000),
    padding: int = 30,
    shadow_color: Tuple[int, int, int, int] = (100, 100, 100, 80),
    shadow_offset: Tuple[int, int] = (8, 8),
) -> Image.Image:
    """
    Create a 2x2 grid of images.

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        grid_size: Size of the grid (width, height)
        padding: Padding between images
        shadow_color: Color of the shadow
        shadow_offset: Offset of the shadow (x, y)

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

            # Draw shadow
            shadow_img = Image.new("RGBA", img_resized.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            shadow_draw.rectangle([(0, 0), img_resized.size], fill=shadow_color)

            # Paste shadow
            canvas.paste(
                shadow_img,
                (x_centered + shadow_offset[0], y_centered + shadow_offset[1]),
                img_resized,
            )

            # Paste image
            canvas.paste(img_resized, (x_centered, y_centered), img_resized)

        except Exception as e:
            logger.error(f"Error processing image {img_path} for 2x2 grid: {e}")

    return canvas


def apply_watermark(
    image: Image.Image,
    text: str = "digital veil",
    font_name: str = "Clattering",
    font_size: int = 50,
    text_color: Tuple[int, int, int] = (150, 150, 150),
    opacity: int = 100,
    angle: float = 45.0,
    spacing_factor: float = WATERMARK_TEXT_SPACING_FACTOR,
) -> Image.Image:
    """
    Apply a watermark to an image.

    Args:
        image: The image to watermark
        text: The watermark text
        font_name: The font name
        font_size: The font size
        text_color: The text color
        opacity: The opacity of the watermark
        angle: The angle of the watermark
        spacing_factor: The spacing factor between watermarks (default: WATERMARK_TEXT_SPACING_FACTOR from config)

    Returns:
        The watermarked image
    """
    # Use the consolidated watermarking function from utils.common
    return apply_watermark(
        image=image,
        watermark_type="text",
        text=text,
        font_name=font_name,
        font_size=font_size,
        text_color=text_color,
        opacity=opacity,
        angle=angle,
        spacing_factor=spacing_factor,
    )
