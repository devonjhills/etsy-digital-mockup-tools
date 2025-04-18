"""
Module for adding titles to images.
"""

import textwrap
from typing import Tuple, Optional
from PIL import Image, ImageDraw

from utils.common import setup_logging, get_resampling_filter, get_font

# Set up logging
logger = setup_logging(__name__)


def add_title_bar_and_text(
    image: Image.Image,
    background_image: Image.Image,
    title: str,
    subtitle_top: str = "",
    subtitle_bottom: str = "",
    title_font_name: str = "Angelina",
    subtitle_font_name: str = "MarkerFelt",
    title_max_font_size: int = 200,
    title_min_font_size: int = 40,
    title_font_step: int = 5,
    subtitle_font_size: int = 70,
    title_max_lines: int = 3,
    title_line_spacing: int = 8,
    subtitle_spacing: int = 15,
    title_padding_x: int = 80,
    text_color: Tuple = (50, 50, 50, 255),
    subtitle_text_color: Tuple = (80, 80, 80, 255),
) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    """
    Add centered text directly on the background image.

    Args:
        image: The image to add the title to
        background_image: The background image to sample colors from
        title: The title text
        subtitle_top: The top subtitle text
        subtitle_bottom: The bottom subtitle text
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
        title_padding_y: The vertical padding for the title
        backdrop_padding_x: The horizontal padding for the backdrop
        backdrop_padding_y: The vertical padding for the backdrop
        backdrop_corner_radius: The corner radius for the backdrop
        backdrop_opacity: The opacity for the backdrop
        border_width: The width of the border
        border_color: The color of the border
        text_color: The color of the title text
        subtitle_text_color: The color of the subtitle text

    Returns:
        Tuple of (modified image, backdrop bounds)
    """
    if not isinstance(image, Image.Image):
        logger.error("Invalid image input.")
        return None, None

    if not isinstance(background_image, Image.Image):
        logger.error("Invalid background_image input.")
        return image, None

    output_image = image.copy().convert("RGBA")
    canvas_w, canvas_h = output_image.size
    bg_w, bg_h = background_image.size

    if canvas_w <= 0 or canvas_h <= 0:
        logger.error("Input image has zero dimensions.")
        return output_image, None

    if bg_w != canvas_w or bg_h != canvas_h:
        try:
            background_image = background_image.resize(
                (canvas_w, canvas_h), get_resampling_filter()
            )
        except Exception as resize_err:
            logger.error(f"Error resizing background image: {resize_err}.")

    # Create a draw object
    draw = ImageDraw.Draw(output_image)

    # Get fonts using the provided font names
    title_font = get_font(title_font_name, title_max_font_size)
    subtitle_font = get_font(subtitle_font_name, subtitle_font_size)

    # Calculate title text dimensions and wrap if needed
    title_lines = []
    title_font_size = title_max_font_size
    max_title_width = canvas_w - (2 * title_padding_x)

    while title_font_size >= title_min_font_size:
        # Use the specified title font
        title_font = get_font(title_font_name, title_font_size)

        # Try to wrap the text
        wrapped_lines = textwrap.wrap(
            title, width=int(max_title_width / (title_font_size * 0.5))
        )

        # Limit to max lines
        if len(wrapped_lines) <= title_max_lines:
            # Calculate total width and height
            max_line_width = 0
            total_height = 0

            for line in wrapped_lines:
                try:
                    bbox = draw.textbbox((0, 0), line, font=title_font)
                    line_width = bbox[2] - bbox[0]
                    line_height = bbox[3] - bbox[1]
                except AttributeError:
                    line_width, line_height = draw.textsize(line, font=title_font)

                max_line_width = max(max_line_width, line_width)
                total_height += line_height

            # Add line spacing
            if len(wrapped_lines) > 1:
                total_height += title_line_spacing * (len(wrapped_lines) - 1)

            # Check if it fits
            if max_line_width <= max_title_width:
                title_lines = wrapped_lines
                break

        # Reduce font size and try again
        title_font_size -= title_font_step

    # If we couldn't fit the text, use the smallest font size
    if not title_lines:
        title_font = get_font(title_font_name, title_min_font_size)
        title_lines = textwrap.wrap(
            title, width=int(max_title_width / (title_min_font_size * 0.5))
        )[:title_max_lines]

    # Calculate subtitle dimensions
    subtitle_top_height = 0
    subtitle_top_width = 0

    if subtitle_top:
        try:
            bbox = draw.textbbox((0, 0), subtitle_top, font=subtitle_font)
            subtitle_top_width = bbox[2] - bbox[0]
            subtitle_top_height = bbox[3] - bbox[1]
        except AttributeError:
            subtitle_top_width, subtitle_top_height = draw.textsize(
                subtitle_top, font=subtitle_font
            )

    subtitle_bottom_height = 0
    subtitle_bottom_width = 0

    if subtitle_bottom:
        try:
            bbox = draw.textbbox((0, 0), subtitle_bottom, font=subtitle_font)
            subtitle_bottom_width = bbox[2] - bbox[0]
            subtitle_bottom_height = bbox[3] - bbox[1]
        except AttributeError:
            subtitle_bottom_width, subtitle_bottom_height = draw.textsize(
                subtitle_bottom, font=subtitle_font
            )

    # Calculate title block dimensions
    title_block_width = 0
    title_block_height = 0

    # Add subtitle top height if present
    if subtitle_top:
        title_block_height += subtitle_top_height + subtitle_spacing

    # Calculate title height
    title_height = 0
    for i, line in enumerate(title_lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
        except AttributeError:
            line_width, line_height = draw.textsize(line, font=title_font)

        title_block_width = max(title_block_width, line_width)
        title_height += line_height

        # Add line spacing for all but the last line
        if i < len(title_lines) - 1:
            title_height += title_line_spacing

    title_block_height += title_height

    # Add subtitle bottom height if present
    if subtitle_bottom:
        title_block_height += subtitle_spacing + subtitle_bottom_height

    # Calculate text area dimensions
    text_width = title_block_width + (2 * title_padding_x)

    # Calculate total height needed for all elements
    total_height = title_height  # Start with title height

    # Add subtitle heights if present
    if subtitle_top:
        total_height += subtitle_top_height + subtitle_spacing
    if subtitle_bottom:
        total_height += subtitle_bottom_height + subtitle_spacing

    # Add some padding to ensure text doesn't overlap
    padding_factor = 1.2  # 20% extra space
    text_height = int(total_height * padding_factor)

    # Calculate text position (centered)
    text_x = (canvas_w - text_width) // 2
    text_y = (canvas_h - text_height) // 2

    # Sample background color from the center of the background image to determine text color
    bg_sample_x = canvas_w // 2
    bg_sample_y = canvas_h // 2
    bg_sample_size = 100

    bg_sample_box = (
        max(0, bg_sample_x - bg_sample_size // 2),
        max(0, bg_sample_y - bg_sample_size // 2),
        min(canvas_w, bg_sample_x + bg_sample_size // 2),
        min(canvas_h, bg_sample_y + bg_sample_size // 2),
    )

    bg_sample = background_image.crop(bg_sample_box)
    bg_sample = bg_sample.resize((1, 1), get_resampling_filter())
    bg_color = bg_sample.getpixel((0, 0))

    # Determine if we need light or dark text based on background brightness
    brightness = sum(bg_color[:3]) / 3 if len(bg_color) >= 3 else 127

    # Only override text colors if they weren't explicitly provided
    # This allows our color extraction to take precedence
    if text_color == (50, 50, 50, 255) and subtitle_text_color == (80, 80, 80, 255):
        # Use white text on dark backgrounds, black text on light backgrounds
        if brightness < 128:
            text_color = (255, 255, 255, 255)  # White text for dark backgrounds
            subtitle_text_color = (220, 220, 220, 255)  # Light gray for subtitles
        else:
            text_color = (0, 0, 0, 255)  # Black text for light backgrounds
            subtitle_text_color = (50, 50, 50, 255)  # Dark gray for subtitles

    # Calculate text positions - center vertically within the backdrop with a slight upward adjustment
    total_content_height = 0

    # Calculate total content height
    if subtitle_top:
        total_content_height += subtitle_top_height + subtitle_spacing

    # Add title height
    total_content_height += title_height

    # Add subtitle bottom height if present
    if subtitle_bottom:
        total_content_height += subtitle_spacing + subtitle_bottom_height

    # Create a draw object for the output image
    draw = ImageDraw.Draw(output_image)

    # Calculate vertical positions to center everything
    # First, determine the total height of all elements with spacing
    total_content_height = title_height
    if subtitle_top:
        total_content_height += subtitle_top_height + subtitle_spacing
    if subtitle_bottom:
        total_content_height += subtitle_bottom_height + subtitle_spacing

    # Calculate the starting y-position to center all content vertically
    start_y = text_y + (text_height - total_content_height) // 2
    current_y = start_y

    # Draw subtitle top
    if subtitle_top:
        subtitle_top_x = text_x + (text_width - subtitle_top_width) // 2
        draw.text(
            (subtitle_top_x, current_y),
            subtitle_top,
            font=subtitle_font,
            fill=subtitle_text_color,
        )
        current_y += subtitle_top_height + subtitle_spacing

    # Draw title lines
    for i, line in enumerate(title_lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
        except AttributeError:
            line_width, line_height = draw.textsize(line, font=title_font)

        line_x = text_x + (text_width - line_width) // 2

        # Add a subtle text shadow for better readability
        shadow_offset = 2
        draw.text(
            (line_x + shadow_offset, current_y + shadow_offset),
            line,
            font=title_font,
            fill=(0, 0, 0, 100),
        )

        # Draw the main text
        draw.text((line_x, current_y), line, font=title_font, fill=text_color)

        # Add spacing after each line except the last one
        if i < len(title_lines) - 1:
            current_y += line_height + title_line_spacing
        else:
            current_y += line_height + subtitle_spacing

    # Draw subtitle bottom
    if subtitle_bottom:
        subtitle_bottom_x = text_x + (text_width - subtitle_bottom_width) // 2

        # Add a subtle text shadow for better readability
        shadow_offset = 1
        draw.text(
            (subtitle_bottom_x + shadow_offset, current_y + shadow_offset),
            subtitle_bottom,
            font=subtitle_font,
            fill=(0, 0, 0, 100),
        )

        # Draw the main text
        draw.text(
            (subtitle_bottom_x, current_y),
            subtitle_bottom,
            font=subtitle_font,
            fill=subtitle_text_color,
        )

    # Return the modified image and text bounds
    text_bounds = (
        text_x,
        text_y,
        text_x + text_width,
        text_y + text_height,
    )

    return output_image, text_bounds
