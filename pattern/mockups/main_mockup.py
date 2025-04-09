"""
Module for creating the main pattern mockup.
"""

import os
import glob
from typing import Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont

from utils.common import (
    setup_logging,
    get_resampling_filter,
    get_asset_path,
    ensure_dir_exists,
    get_font,
)

# Set up logging
logger = setup_logging(__name__)


def create_main_mockup(input_folder: str, title: str) -> Optional[str]:
    """
    Creates the main 2x6 grid mockup.

    Args:
        input_folder: Path to the input folder containing images
        title: Title to display on the mockup

    Returns:
        Path to the created main mockup file, or None if creation failed
    """
    logger.info(f"Creating main mockup for '{title}'...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    GRID_ROWS, GRID_COLS = 2, 6

    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        logger.warning(f"No images found in {input_folder} for main mockup.")
        return None

    grid_width = 3000
    grid_height = 2250

    background_color = (222, 215, 211, 255)
    grid_canvas = Image.new("RGBA", (grid_width, grid_height), background_color)

    # Calculate cell dimensions and spacing
    cell_height = grid_height // GRID_ROWS
    avg_cell_width = grid_width // GRID_COLS

    total_spacing_x = grid_width - (avg_cell_width * GRID_COLS)
    spacing_between_x = total_spacing_x / (GRID_COLS + 1) if GRID_COLS > 0 else 0

    # Load shadow
    shadow_path = get_asset_path("shadow.png")
    shadow = None
    shadow_new_width = 0

    if shadow_path:
        try:
            shadow_img = Image.open(shadow_path).convert("RGBA")
            scale_factor = (
                cell_height / shadow_img.height if shadow_img.height > 0 else 1
            )
            shadow_new_width = int(shadow_img.width * scale_factor)

            if shadow_new_width > 0 and cell_height > 0:
                shadow = shadow_img.resize(
                    (shadow_new_width, cell_height), get_resampling_filter()
                )
        except Exception as e:
            logger.warning(f"Error loading or resizing shadow: {e}. Skipping shadow.")

    # First pass: Draw images
    image_positions_for_shadow = []
    images_to_place = images[: GRID_ROWS * GRID_COLS]

    for i, img_path in enumerate(images_to_place):
        try:
            img = Image.open(img_path).convert("RGBA")

            # Resize based on height, maintain aspect ratio
            img_aspect = img.width / img.height if img.height > 0 else 1
            img_new_width = int(cell_height * img_aspect)
            img_new_height = cell_height

            if img_new_width <= 0 or img_new_height <= 0:
                continue

            img_resized = img.resize(
                (img_new_width, img_new_height), get_resampling_filter()
            )

            row_index = i // GRID_COLS
            col_index = i % GRID_COLS

            # Calculate position
            x_pos = int(
                (col_index + 1) * spacing_between_x + col_index * avg_cell_width
            )
            y_pos = int(row_index * cell_height)

            # Store position for shadow placement
            image_positions_for_shadow.append((x_pos, y_pos))

            # Paste image
            grid_canvas.paste(img_resized, (x_pos, y_pos), img_resized)

        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")

    # Second pass: Add shadows
    if shadow:
        for x_pos, y_pos in image_positions_for_shadow:
            # Calculate shadow position
            shadow_x = x_pos - shadow_new_width + 5
            shadow_y = y_pos

            try:
                # Check if shadow is within bounds
                if (
                    shadow_x < grid_width
                    and shadow_y < grid_height
                    and shadow_x + shadow.width > 0
                    and shadow_y + shadow.height > 0
                ):
                    grid_canvas.paste(shadow, (shadow_x, shadow_y), shadow)
            except Exception as e:
                logger.error(f"Error pasting shadow at ({shadow_x},{shadow_y}): {e}")

    # Add overlay
    final_image = grid_canvas
    overlay_path = get_asset_path("overlay.png")

    if overlay_path:
        try:
            overlay = Image.open(overlay_path).convert("RGBA")
            overlay = overlay.resize((grid_width, grid_height), get_resampling_filter())
            final_image = Image.alpha_composite(grid_canvas, overlay)
        except Exception as e:
            logger.warning(
                f"Error loading or applying overlay: {e}. Using image without overlay."
            )

    final_image = final_image.convert("RGB")

    # Add title text
    try:
        draw = ImageDraw.Draw(final_image)

        # Use the get_font function from utils.common which handles fallbacks properly
        # and will use Angelina font by default
        initial_font_size, max_width = 200, 1380

        def get_font_and_size(font_name, size, text_to_draw):
            font = get_font(font_name, size)
            if not font:
                logger.warning(f"Failed to load font {font_name} at size {size}")
                font = ImageFont.load_default()

            try:
                bbox = draw.textbbox((0, 0), text_to_draw, font=font)
                return font, bbox[2] - bbox[0], bbox[3] - bbox[1]
            except AttributeError:
                text_width, text_height = draw.textsize(text_to_draw, font=font)
                return font, text_width, text_height

        # Adjust font size to fit
        font_size = initial_font_size
        font, text_width, text_height = get_font_and_size("Angelina", font_size, title)

        while text_width > max_width and font_size > 50:
            font_size -= 5
            font, text_width, text_height = get_font_and_size(
                "Angelina", font_size, title
            )

        # Calculate text position
        text_x = (grid_width - text_width) // 2
        text_y = (grid_height - text_height) // 2

        # Draw text
        draw.text((text_x, text_y), title, font=font, fill=(238, 186, 43), anchor="lt")

    except Exception as e:
        logger.error(f"Error adding title: {e}")

    # Save final image
    try:
        grid_filename = "main.png"
        save_path = os.path.join(output_folder, grid_filename)
        final_image.save(save_path, "PNG")
        logger.info(f"Main mockup saved: {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"Error saving main mockup: {e}")
        return None
