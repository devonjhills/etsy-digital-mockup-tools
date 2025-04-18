"""
Module for creating grid mockups.
"""

import os
import glob
from typing import Optional
from PIL import Image

from utils.common import (
    setup_logging,
    get_resampling_filter,
    get_asset_path,
    ensure_dir_exists,
    apply_watermark,
)

# Set up logging
logger = setup_logging(__name__)


def create_grid_mockup_with_borders(
    input_folder: str, border_width: int = 15, watermark_text: str = "© digital veil"
) -> Optional[str]:
    """
    Creates a 4x3 grid mockup with white borders and watermark.

    Args:
        input_folder: Path to the input folder containing images
        border_width: Width of the borders between images
        watermark_text: Text to use for the watermark

    Returns:
        Path to the created grid mockup file, or None if creation failed
    """
    logger.info("Creating grid mockup with borders...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        logger.warning("No images found for grid mockup.")
        return None

    images_to_place = images[:12]  # Limit to 12 images
    grid_rows, grid_cols = 3, 4

    # Calculate average aspect ratio
    avg_aspect = 1.0
    try:
        img_samples = [Image.open(img) for img in images_to_place[:3]]
        if img_samples:
            valid_aspects = [
                img.width / img.height for img in img_samples if img.height > 0
            ]
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
        logger.error(
            f"Calculated cell dimensions invalid ({cell_width}x{cell_height})."
        )
        return None

    # Create grid canvas with canvas.png background instead of solid color
    canvas_path = get_asset_path("canvas.png")
    if canvas_path:
        try:
            canvas_bg = Image.open(canvas_path).convert("RGB")
            # Resize to fit our grid dimensions
            canvas_bg = canvas_bg.resize(
                (grid_width, grid_height), get_resampling_filter()
            )
            grid_canvas = canvas_bg
        except Exception as e:
            logger.warning(f"Error loading canvas.png: {e}. Using white background.")
            grid_canvas = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))
    else:
        logger.warning(
            "Canvas background 'canvas.png' not found. Using white background."
        )
        grid_canvas = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))

    # Place images
    for i, img_path in enumerate(images_to_place):
        try:
            img = Image.open(img_path).convert("RGB")
            img = img.resize((cell_width, cell_height), get_resampling_filter())
            row_index = i // grid_cols
            col_index = i % grid_cols
            x_pos = border_width + col_index * (cell_width + border_width)
            y_pos = border_width + row_index * (cell_height + border_width)
            grid_canvas.paste(img, (x_pos, y_pos))
        except Exception as e:
            logger.error(f"Error processing or pasting image {img_path}: {e}")

    # Add watermarks
    try:
        # Use the consolidated watermarking function
        grid_canvas_rgba = grid_canvas.convert("RGBA")
        watermarked_image = apply_watermark(
            image=grid_canvas_rgba,
            watermark_type="text",
            text=watermark_text,
            font_name="DSMarkerFelt.ttf",
            font_size=80,
            text_color=(255, 255, 255),
            opacity=128,
            angle=-30,
            spacing_factor=3.0,
        )
        final_image = watermarked_image.convert("RGB")

    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        final_image = grid_canvas

    # Save the result
    try:
        output_path = os.path.join(output_folder, "grid_mockup_with_borders.jpg")
        final_image.save(output_path, "JPEG", quality=95)
        logger.info(f"Grid mockup with borders saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error saving grid mockup with borders: {e}")
        return None
