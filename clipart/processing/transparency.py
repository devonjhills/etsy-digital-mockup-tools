"""
Module for creating transparency demonstrations.
"""

import os
from typing import Tuple, Optional
from PIL import Image, ImageDraw

from utils.common import setup_logging, get_resampling_filter, safe_load_image

# Set up logging
logger = setup_logging(__name__)


def create_transparency_demo(
    image_path: str,
    canvas_path: str = "assets/transparency_mock.png",
    scale: float = 0.7,
    checkerboard_size: int = 30,
    checkerboard_color1: Tuple[int, int, int] = (255, 255, 255),
    checkerboard_color2: Tuple[int, int, int] = (200, 200, 200),
) -> Optional[Image.Image]:
    """
    Create a demonstration of image transparency.

    Args:
        image_path: Path to the image
        canvas_path: Path to the canvas image
        scale: Scale factor for the image
        checkerboard_size: Size of the checkerboard squares
        checkerboard_color1: First color of the checkerboard
        checkerboard_color2: Second color of the checkerboard

    Returns:
        The transparency demo image, or None if creation failed
    """
    logger.info(f"Creating transparency demo for {os.path.basename(image_path)}...")

    # Load canvas
    canvas = safe_load_image(canvas_path, "RGBA")
    if not canvas:
        logger.error(f"Failed to load canvas {canvas_path}")
        return None

    # Load image
    img = safe_load_image(image_path, "RGBA")
    if not img:
        logger.warning(f"Could not load image {image_path}")
        return canvas.copy()

    # Calculate maximum dimensions
    canvas_w, canvas_h = canvas.size
    # Increase the scale by 15% to make the image larger
    adjusted_scale = scale * 1.15
    max_w = int(canvas_w * 0.5 * adjusted_scale)
    max_h = int(canvas_h * adjusted_scale)

    if max_w <= 0 or max_h <= 0:
        logger.warning("Invalid scale/canvas size.")
        return canvas.copy()

    try:
        # Resize image
        img_copy = img.copy()
        img_copy.thumbnail((max_w, max_h), get_resampling_filter())
        img_w, img_h = img_copy.size

        # Create checkerboard pattern
        checkerboard = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(checkerboard)

        for y in range(0, img_h, checkerboard_size):
            for x in range(0, img_w, checkerboard_size):
                color = (
                    checkerboard_color1
                    if ((x // checkerboard_size) + (y // checkerboard_size)) % 2 == 0
                    else checkerboard_color2
                )
                draw.rectangle(
                    [(x, y), (x + checkerboard_size - 1, y + checkerboard_size - 1)],
                    fill=color,
                )

        # Calculate positions
        center_x = canvas_w // 2
        center_y = canvas_h // 2

        # Left side: image on white background
        white_bg = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))
        white_composite = Image.alpha_composite(white_bg, img_copy)

        # Right side: image on checkerboard
        checker_composite = Image.alpha_composite(checkerboard, img_copy)

        # Paste only onto the left side of the canvas
        # Move the image more to the left by increasing the offset
        left_x = (
            center_x - img_w - 60
        )  # Increased from 20 to 60 to move more to the left
        top_y = center_y - img_h // 2

        # Ensure positions are valid
        left_x = max(0, left_x)
        top_y = max(0, top_y)

        # Use the alpha channel from the original image as a mask when pasting
        # This ensures transparency is preserved
        canvas.paste(white_composite, (left_x, top_y), img_copy)
        # We don't paste the right side image anymore

        return canvas

    except Exception as e:
        logger.error(f"Error creating transparency demo: {e}")
        return canvas.copy()
