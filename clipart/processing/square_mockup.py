"""
Module for creating square mockups with a 2x3 grid (2 columns, 3 rows) and title overlay.
"""

import os
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw

from utils.common import setup_logging, get_resampling_filter, safe_load_image
from clipart.processing.grid_2x3 import create_2x3_grid
from clipart.processing.title import add_title_bar_and_text

# Set up logging
logger = setup_logging(__name__)


def create_square_mockup(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    title: str,
    subtitle_top: str = "",
    subtitle_bottom: str = "",
    grid_size: Tuple[int, int] = (2000, 2000),
    padding: int = 30,
    shadow_color: Tuple[int, int, int, int] = (100, 100, 100, 80),
    shadow_offset: Tuple[int, int] = (8, 8),
    title_font_name: str = "Angelina",
    subtitle_font_name: str = "MarkerFelt",
    title_max_font_size: int = 140,  # Smaller than the default 170
    title_min_font_size: int = 40,
    title_font_step: int = 5,
    subtitle_font_size: int = 60,  # Smaller than the default 70
    title_max_lines: int = 3,
    title_line_spacing: int = 15,
    subtitle_spacing: int = 25,
    title_padding_x: int = 60,  # Smaller than the default 80
    backdrop_padding_x: int = 50,  # Smaller than the default 60
    backdrop_padding_y: int = 25,  # Smaller than the default 30
    backdrop_corner_radius: int = 40,
    backdrop_opacity: int = 180,  # Reduced from 255 to add transparency
    border_width: int = 5,
    border_color: Tuple = (218, 165, 32, 255),
    text_color: Tuple = (50, 50, 50, 255),
    subtitle_text_color: Tuple = (80, 80, 80, 255),
) -> Tuple[Optional[Image.Image], List[str]]:
    """
    Create a square mockup with a 2x3 grid (2 columns, 3 rows) and title overlay.

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        title: The title text
        subtitle_top: The top subtitle text
        subtitle_bottom: The bottom subtitle text
        grid_size: Size of the grid (width, height)
        padding: Padding between images
        shadow_color: Color of the shadow
        shadow_offset: Offset of the shadow (x, y)
        title_font_name: The font name for the title
        subtitle_font_name: The font name for the subtitle
        title_max_font_size: The maximum font size for the title
        title_min_font_size: The minimum font size for the title
        title_font_step: The step size for reducing the title font size
        subtitle_font_size: The font size for the subtitle
        title_max_lines: The maximum number of lines for the title
        title_line_spacing: The spacing between title lines
        subtitle_spacing: The spacing between title and subtitle
        title_padding_x: The horizontal padding for the title
        backdrop_padding_x: The horizontal padding for the backdrop
        backdrop_padding_y: The vertical padding for the backdrop
        backdrop_corner_radius: The corner radius for the backdrop
        backdrop_opacity: The opacity for the backdrop
        border_width: The width of the border
        border_color: The color of the border
        text_color: The color of the title text
        subtitle_text_color: The color of the subtitle text

    Returns:
        Tuple of (final mockup image, list of used image paths)
    """
    logger.info(
        "Creating square mockup with 2x3 grid (2 columns, 3 rows) and title overlay..."
    )

    if not input_image_paths:
        logger.warning("No input images provided for square mockup.")
        return None, []

    # Ensure we have a copy of the background
    canvas = canvas_bg_image.copy()

    # Resize canvas to the grid size if needed
    if canvas.size != grid_size:
        canvas = canvas.resize(grid_size, get_resampling_filter())

    # Create the 2x3 grid (2 columns, 3 rows)
    logger.info("Creating 2x3 grid layout (2 columns, 3 rows)...")
    grid_image = create_2x3_grid(
        input_image_paths=input_image_paths[:6],  # Use first 6 images
        canvas_bg_image=canvas,
        grid_size=grid_size,
        padding=padding,
        # Shadow parameters removed as requested
    )

    # Add title overlay
    logger.info("Adding title overlay...")
    title_style_args = {
        "title_font_name": title_font_name,
        "subtitle_font_name": subtitle_font_name,
        "title_max_font_size": title_max_font_size,
        "title_min_font_size": title_min_font_size,
        "title_font_step": title_font_step,
        "subtitle_font_size": subtitle_font_size,
        "title_max_lines": title_max_lines,
        "title_line_spacing": title_line_spacing,
        "subtitle_spacing": subtitle_spacing,
        "title_padding_x": title_padding_x,
        "backdrop_padding_x": backdrop_padding_x,
        "backdrop_padding_y": backdrop_padding_y,
        "backdrop_corner_radius": backdrop_corner_radius,
        "backdrop_opacity": backdrop_opacity,
        "border_width": border_width,
        "border_color": border_color,
        "text_color": text_color,
        "subtitle_text_color": subtitle_text_color,
    }

    # Create a blank layer for the title
    title_layer = Image.new("RGBA", grid_size, (0, 0, 0, 0))

    # Add title to the blank layer
    title_image, _ = add_title_bar_and_text(
        image=title_layer,
        background_image=grid_image,
        title=title,
        subtitle_top=subtitle_top,
        subtitle_bottom=subtitle_bottom,
        **title_style_args,
    )

    if title_image:
        # Composite title onto grid image
        final_image = Image.alpha_composite(grid_image.convert("RGBA"), title_image)
        return final_image, input_image_paths[:6]
    else:
        logger.warning("Failed to add title overlay. Returning grid image only.")
        return grid_image, input_image_paths[:6]
