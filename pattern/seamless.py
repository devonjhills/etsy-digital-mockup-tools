"""Module for creating seamless pattern mockups."""

import os
import glob
from typing import Optional, Tuple
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


def create_pattern(input_folder: str) -> Optional[str]:
    """
    Creates a simple 2x2 tiled seamless pattern image.

    Args:
        input_folder: Path to the input folder containing images

    Returns:
        Path to the created seamless pattern file, or None if creation failed
    """
    logger.info("Creating seamless pattern image...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    # Find JPG images in the input folder
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))
    if not images:
        logger.warning("No JPG images found for seamless pattern.")
        return None

    # Use the second image if available, otherwise use the first one
    # This ensures seamless_1.jpg uses a different image than the other seamless mockup
    if len(images) > 1:
        image_path = images[1]  # Use the second image
        logger.info(
            f"Using second image for seamless_1.jpg: {os.path.basename(image_path)}"
        )
    else:
        image_path = images[0]  # Fall back to the first image if only one is available
        logger.info(
            f"Only one image available, using it for seamless_1.jpg: {os.path.basename(image_path)}"
        )
    IMAGE_SIZE = 2048
    GRID_SIZE = 2

    try:
        output_image = Image.new("RGBA", (IMAGE_SIZE, IMAGE_SIZE))
        source_image = Image.open(image_path).convert("RGBA")

        cell_size = IMAGE_SIZE // GRID_SIZE
        source_image = source_image.resize(
            (cell_size, cell_size), get_resampling_filter()
        )

        # Create 2x2 grid
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                output_image.paste(
                    source_image, (col * cell_size, row * cell_size), source_image
                )

        # Add text overlay
        txt_layer = Image.new("RGBA", output_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # Get font - use GreatVibes-Regular for the seamless patterns text
        font = get_font("GreatVibes-Regular", 185)

        text = "Seamless Patterns"
        text_position = (IMAGE_SIZE // 2, IMAGE_SIZE // 2)

        # Calculate text size for backdrop
        try:
            # For newer Pillow versions
            text_bbox = draw.textbbox(
                text_position, text, font=font, anchor="mm", align="center"
            )
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            # For older Pillow versions
            text_width, text_height = draw.textsize(text, font=font)

        # Add padding around text
        padding = 40
        backdrop_width = text_width + padding * 2
        backdrop_height = text_height + padding * 2

        # Draw semi-transparent backdrop
        backdrop_position = (
            text_position[0] - backdrop_width // 2,
            text_position[1] - backdrop_height // 2,
            text_position[0] + backdrop_width // 2,
            text_position[1] + backdrop_height // 2,
        )
        draw.rounded_rectangle(
            backdrop_position,
            radius=20,
            fill=(255, 255, 255, 160),  # White with 60% opacity
        )

        # Draw main text
        draw.text(
            text_position,
            text,
            font=font,
            fill=(0, 0, 0, 230),  # Black with 90% opacity
            anchor="mm",
            align="center",
        )

        combined = Image.alpha_composite(output_image, txt_layer)

        # Save the result
        filename = "seamless_1.jpg"
        save_path = os.path.join(output_folder, filename)
        combined.convert("RGB").save(
            save_path,
            "JPEG",
            quality=85,
            optimize=True,
            subsampling="4:2:0",
        )

        logger.info(f"Seamless pattern saved: {save_path}")
        return save_path

    except Exception as e:
        logger.error(f"Error creating seamless pattern for {image_path}: {e}")
        return None


def create_seamless_mockup(input_folder: str) -> Optional[str]:
    """
    Creates a mockup showing a single tile next to a 2x2 seamless representation.

    Args:
        input_folder: Path to the input folder containing images

    Returns:
        Path to the created mockup file, or None if creation failed
    """
    logger.info("Creating original seamless comparison mockup...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    input_files = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not input_files:
        logger.warning("No image files found in input folder for seamless mockup.")
        return None

    # Always use the first image for the comparison mockup
    input_image_path = input_files[0]
    logger.info(
        f"Using first image for seamless comparison mockup: {os.path.basename(input_image_path)}"
    )

    try:
        input_img = Image.open(input_image_path)
        if input_img.mode != "RGBA":
            input_img = input_img.convert("RGBA")

        cell_max_size = (550, 550)
        scaled_img = input_img.copy()
        scaled_img.thumbnail(cell_max_size, get_resampling_filter())
        cell_width, cell_height = scaled_img.size

        # Load or create canvas
        canvas_path = get_asset_path("canvas2.png")
        if canvas_path:
            canvas = Image.open(canvas_path).convert("RGBA")
            canvas_target_size = (2000, 2000)
            canvas = canvas.resize(canvas_target_size, get_resampling_filter())
        else:
            logger.warning("Canvas background 'canvas2.png' not found. Using white.")
            canvas_target_size = (2000, 2000)
            canvas = Image.new("RGBA", canvas_target_size, (255, 255, 255, 255))

        _, canvas_height = canvas.size  # Only need canvas_height
        margin, arrow_gap = 100, 100

        # Paste single tile on the left
        left_x, left_y = margin, (canvas_height - cell_height) // 2
        canvas.paste(scaled_img, (left_x, left_y), scaled_img)

        # Paste 2x2 grid on the right
        grid_x = left_x + cell_width + arrow_gap
        grid_y = (canvas_height - (2 * cell_height)) // 2
        for i in range(2):
            for j in range(2):
                pos = (grid_x + j * cell_width, grid_y + i * cell_height)
                canvas.paste(scaled_img, pos, scaled_img)

        # Save the result
        output_image_path = os.path.join(output_folder, "output_mockup.png")
        canvas.save(output_image_path, "PNG")

        logger.info(f"Original seamless comparison mockup saved: {output_image_path}")
        return output_image_path

    except Exception as e:
        logger.error(
            f"Error creating original seamless comparison mockup for {input_image_path}: {e}"
        )
        return None
