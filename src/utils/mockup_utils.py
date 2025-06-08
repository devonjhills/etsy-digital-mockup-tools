"""
Shared utilities for creating main mockups across different product types.
"""

import os
import glob
from typing import Optional, Dict, Tuple
from PIL import Image

from src.utils.common import setup_logging, ensure_dir_exists
from src.utils.common import get_project_root
from src.utils.color_utils import extract_colors_from_images
from src.utils.image_utils import resize_image
from src.products.pattern.dynamic_main_mockup import (
    generate_color_palette,
    PatternConfig,
)
from src.utils.text_utils import create_text_backdrop
from PIL import ImageDraw
from src.utils.text_utils import draw_text, calculate_text_dimensions, get_font

logger = setup_logging(__name__)


def create_shared_main_mockup(
    input_folder: str,
    title: str,
    top_subtitle_text: str,
    bottom_subtitle_text: str,
    output_filename: str = "main.png",
    grid_rows: int = 2,
    grid_cols: int = 6,
    grid_width: int = 3000,
    grid_height: int = 2250,
    config_type: str = "pattern",
) -> Optional[str]:
    """
    Creates a main mockup with customizable subtitle text.
    This is the shared function used by both patterns and journal papers.

    Args:
        input_folder: Path to the input folder containing images
        title: Title to display on the mockup
        top_subtitle_text: Text for the top subtitle (e.g., "12 Seamless Patterns")
        bottom_subtitle_text: Text for the bottom subtitle (e.g., "commercial use | 300 dpi | 12x12in jpg")
        output_filename: Name of the output file (default: "main.png")
        grid_rows: Number of rows in the grid (default: 2)
        grid_cols: Number of columns in the grid (default: 6)
        grid_width: Width of the grid in pixels (default: 3000)
        grid_height: Height of the grid in pixels (default: 2250)
        config_type: Product type for configuration (default: "pattern")

    Returns:
        Path to the created main mockup file, or None if creation failed
    """
    logger.info(f"Creating shared main mockup for '{title}' with custom subtitles...")

    # Get configuration for the product type
    from src.core.config_manager import get_config_manager

    config_manager = get_config_manager()
    product_config = config_manager.get_config(config_type)
    logger.info(
        f"Loading config for type: {config_type}, found config: {product_config is not None}"
    )

    # Use pattern config structure for compatibility
    config = PatternConfig()
    if product_config:
        font_settings = product_config.font_settings
        layout_settings = product_config.layout_settings
        color_settings = product_config.color_settings

        # Update font config with product-specific settings
        config.FONT_CONFIG.update(
            {
                "USE_DYNAMIC_TITLE_COLORS": color_settings.get(
                    "use_dynamic_title_colors", True
                ),
                "TOP_SUBTITLE_FONT_SIZE": font_settings.get(
                    "top_subtitle_font_size", 48
                ),
                "BOTTOM_SUBTITLE_FONT_SIZE": font_settings.get(
                    "bottom_subtitle_font_size", 48
                ),
                "TITLE_FONT_SIZE": font_settings.get("title_font_size", 250),
                "TITLE_FONT": font_settings.get("title_font", "GreatVibes-Regular"),
                "SUBTITLE_FONT": font_settings.get(
                    "subtitle_font", "LibreBaskerville-Italic"
                ),
                "TOP_SUBTITLE_PADDING": layout_settings.get("top_subtitle_padding", 75),
                "BOTTOM_SUBTITLE_PADDING": layout_settings.get(
                    "bottom_subtitle_padding", 75
                ),
            }
        )

    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    # Find all images in the input folder
    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        logger.warning(f"No images found in {input_folder} for main mockup.")
        return None

    # Extract colors from the images
    extracted_colors = extract_colors_from_images(images)
    color_palette = generate_color_palette(extracted_colors)

    # Create background
    background_color = color_palette["background"]
    grid_canvas = Image.new("RGBA", (grid_width, grid_height), background_color)

    # Calculate cell dimensions and spacing
    cell_height = grid_height // grid_rows
    avg_cell_width = grid_width // grid_cols
    total_spacing_x = grid_width - (avg_cell_width * grid_cols)
    spacing_between_x = total_spacing_x / (grid_cols + 1) if grid_cols > 0 else 0

    # Load shadow - use correct path to assets
    # This file is in src/utils/, so we go up two levels to get to project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    shadow_path = os.path.join(project_root, "assets", "shadow.png")
    shadow = None
    shadow_new_width = 0

    if os.path.exists(shadow_path):
        try:
            shadow_img = Image.open(shadow_path).convert("RGBA")
            scale_factor = (
                cell_height / shadow_img.height if shadow_img.height > 0 else 1
            )
            shadow_new_width = int(shadow_img.width * scale_factor)

            if shadow_new_width > 0 and cell_height > 0:
                shadow = resize_image(shadow_img, shadow_new_width, cell_height)
        except Exception as e:
            logger.warning(f"Error loading or resizing shadow: {e}. Skipping shadow.")

    # First pass: Draw images
    image_positions_for_shadow = []
    images_to_place = images[: grid_rows * grid_cols]

    for i, img_path in enumerate(images_to_place):
        try:
            img = Image.open(img_path).convert("RGBA")

            # Resize based on height, maintain aspect ratio
            img_aspect = img.width / img.height if img.height > 0 else 1
            img_new_width = int(cell_height * img_aspect)
            img_new_height = cell_height

            if img_new_width <= 0 or img_new_height <= 0:
                continue

            img_resized = resize_image(img, img_new_width, img_new_height)

            # Calculate position
            row_index = i // grid_cols
            col_index = i % grid_cols
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

    # Load a sample image for the backdrop overlay
    sample_image = None
    if images:
        try:
            # Use the first image as a sample for the backdrop
            sample_image_path = images[0]
            sample_image = Image.open(sample_image_path).convert("RGBA")
            logger.info(
                f"Using {os.path.basename(sample_image_path)} as semi-transparent overlay"
            )
        except Exception as e:
            logger.warning(
                f"Error loading sample image: {e}. Will use solid color background."
            )

    # Create and add dynamic overlay with custom subtitle text
    try:
        dynamic_overlay = create_shared_dynamic_overlay(
            width=grid_width,
            height=grid_height,
            palette=color_palette,
            title=title,
            top_subtitle_text=top_subtitle_text,
            bottom_subtitle_text=bottom_subtitle_text,
            sample_image=sample_image,
            config=config,
        )
        final_image = Image.alpha_composite(grid_canvas, dynamic_overlay)
    except Exception as e:
        logger.warning(
            f"Error creating or applying dynamic overlay: {e}. Using image without overlay."
        )
        final_image = grid_canvas

    final_image = final_image.convert("RGB")

    # Save final image
    try:
        save_path = os.path.join(output_folder, output_filename)
        final_image.save(save_path, "PNG")
        logger.info(f"Shared main mockup saved: {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"Error saving shared main mockup: {e}")
        return None


def create_shared_dynamic_overlay(
    width: int,
    height: int,
    palette: Dict[str, Tuple],
    title: str,
    top_subtitle_text: str,
    bottom_subtitle_text: str,
    sample_image: Optional[Image.Image] = None,
    config: PatternConfig = None,
) -> Image.Image:
    """
    Create a dynamic overlay with custom subtitle text.
    Based on the original create_dynamic_overlay but with configurable subtitles.

    Args:
        width: Width of the overlay
        height: Height of the overlay
        palette: Color palette to use
        title: Title text to display
        top_subtitle_text: Custom top subtitle text
        bottom_subtitle_text: Custom bottom subtitle text
        sample_image: Optional image to use as a semi-transparent overlay on the backdrop
        config: Configuration object for fonts and layout

    Returns:
        RGBA image with the overlay
    """

    # Use default config if none provided
    if config is None:
        config = PatternConfig()

    # Create a transparent base image
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate dimensions
    divider_height = height // 15
    divider_y = (height - divider_height) // 2
    border_thickness = max(2, divider_height // 20)

    # Draw the divider
    draw.rectangle(
        [(0, divider_y), (width, divider_y + divider_height)], fill=palette["divider"]
    )

    # Draw top and bottom borders
    draw.rectangle(
        [(0, divider_y), (width, divider_y + border_thickness)],
        fill=palette["divider_border"],
    )
    draw.rectangle(
        [
            (0, divider_y + divider_height - border_thickness),
            (width, divider_y + divider_height),
        ],
        fill=palette["divider_border"],
    )

    # Calculate font sizes
    top_subtitle_font_size = config.FONT_CONFIG["TOP_SUBTITLE_FONT_SIZE"]
    if top_subtitle_font_size <= 0:
        top_subtitle_font_size = int(divider_height * 0.5)

    bottom_subtitle_font_size = config.FONT_CONFIG["BOTTOM_SUBTITLE_FONT_SIZE"]
    if bottom_subtitle_font_size <= 0:
        bottom_subtitle_font_size = int(divider_height * 0.4)

    title_font_size = config.FONT_CONFIG["TITLE_FONT_SIZE"]
    if title_font_size <= 0:
        title_font_size = int(divider_height * 1.0)

    # Get font names from configuration
    title_font_name = config.FONT_CONFIG["TITLE_FONT"]
    subtitle_font_name = config.FONT_CONFIG["SUBTITLE_FONT"]

    # Load the fonts
    top_subtitle_font = get_font(subtitle_font_name, size=top_subtitle_font_size)
    bottom_subtitle_font = get_font(subtitle_font_name, size=bottom_subtitle_font_size)
    title_font = get_font(title_font_name, size=title_font_size)

    # Calculate text dimensions
    try:
        subtitle_width, subtitle_height = calculate_text_dimensions(
            draw, top_subtitle_text, top_subtitle_font
        )
    except Exception as e:
        logger.error(f"Error calculating subtitle dimensions: {e}")
        subtitle_width, subtitle_height = 200, 30  # Fallback values

    # Main title - adjust font size to fit
    max_title_width = width // 2 - 80  # Maximum width with some margin
    try:
        title_width, title_height = calculate_text_dimensions(draw, title, title_font)
        while title_width > max_title_width and title_font_size > 20:
            title_font_size -= 5
            title_font = get_font(title_font_name, size=title_font_size)
            title_width, title_height = calculate_text_dimensions(
                draw, title, title_font
            )
    except Exception as e:
        logger.error(f"Error calculating title dimensions: {e}")
        title_width, title_height = 400, 50  # Fallback values

    # Bottom subtitle
    try:
        bottom_subtitle_width, bottom_subtitle_height = calculate_text_dimensions(
            draw, bottom_subtitle_text, bottom_subtitle_font
        )
    except Exception as e:
        logger.error(f"Error calculating bottom subtitle dimensions: {e}")
        bottom_subtitle_width, bottom_subtitle_height = 300, 25  # Fallback values

    # Calculate text dimensions and padding
    padding_x = 50  # Horizontal padding
    padding_y = 45  # Vertical padding

    # Get padding values from configuration
    top_subtitle_padding = config.FONT_CONFIG["TOP_SUBTITLE_PADDING"]
    bottom_subtitle_padding = config.FONT_CONFIG["BOTTOM_SUBTITLE_PADDING"]

    # Calculate total text height with padding
    total_text_height = (
        top_subtitle_padding  # Padding above top subtitle
        + subtitle_height  # Top subtitle height
        + title_height  # Title height (centered)
        + bottom_subtitle_height  # Bottom subtitle height
        + bottom_subtitle_padding  # Padding below bottom subtitle
    )

    # Calculate text backdrop dimensions based on text content
    text_width = max(subtitle_width, title_width, bottom_subtitle_width) + (
        padding_x * 2
    )
    text_height = total_text_height + (padding_y * 2)

    # Create text backdrop with sample image overlay if provided
    extra_padding = 20
    backdrop_width = text_width + extra_padding
    backdrop_height = text_height + extra_padding
    text_backdrop = create_text_backdrop(
        width=backdrop_width,
        height=backdrop_height,
        background_color=palette["text_bg"],
        border_color=palette["divider_border"],
        border_thickness=border_thickness,
        border_radius=15,
        sample_image=sample_image,
        sample_opacity=60,
    )

    # Center the backdrop on the overlay
    backdrop_x = (width - backdrop_width) // 2
    backdrop_y = (height - backdrop_height) // 2
    overlay.paste(text_backdrop, (backdrop_x, backdrop_y), text_backdrop)

    # Use palette colors for text
    title_color = palette.get("title_text", (255, 255, 255))
    subtitle_color = palette.get("subtitle_text", (255, 255, 255))

    # Position subtitles closer to backdrop edges and center the title between them

    # Top subtitle - position near the top of the backdrop
    top_margin = 25  # Close to backdrop top
    subtitle_x = backdrop_x + (backdrop_width - subtitle_width) // 2
    subtitle_y = backdrop_y + top_margin
    draw_text(
        draw=draw,
        position=(subtitle_x, subtitle_y),
        text=top_subtitle_text,
        font=top_subtitle_font,
        text_color=subtitle_color,
    )

    # Bottom subtitle - position near the bottom of the backdrop
    bottom_margin = 25  # Close to backdrop bottom
    bottom_subtitle_x = backdrop_x + (backdrop_width - bottom_subtitle_width) // 2
    bottom_subtitle_y = (
        backdrop_y + backdrop_height - bottom_subtitle_height - bottom_margin
    )
    draw_text(
        draw=draw,
        position=(bottom_subtitle_x, bottom_subtitle_y),
        text=bottom_subtitle_text,
        font=bottom_subtitle_font,
        text_color=subtitle_color,
    )

    # Center the title vertically between the two subtitles
    available_space_top = subtitle_y + subtitle_height
    available_space_bottom = bottom_subtitle_y
    title_center_y = (
        available_space_top
        + (available_space_bottom - available_space_top - title_height) // 2
    )

    title_x = backdrop_x + (backdrop_width - title_width) // 2
    draw_text(
        draw=draw,
        position=(title_x, title_center_y),
        text=title,
        font=title_font,
        text_color=title_color,
    )

    return overlay
