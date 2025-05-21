"""
Module for creating a dynamic main pattern mockup with colors extracted from the pattern.
"""

import os
import glob
from typing import Optional, Tuple, List, Dict
import colorsys
from PIL import Image, ImageDraw

from utils.common import (
    setup_logging,
    get_asset_path,
    ensure_dir_exists,
    get_font,
)
from utils.color_utils import (
    extract_colors_from_images,
    calculate_contrast_ratio,
    adjust_color_for_contrast,
)
from utils.text_utils import draw_text, calculate_text_dimensions, create_text_backdrop

# Import pattern configuration
from pattern import config

# Set up logging
logger = setup_logging(__name__)


def generate_color_palette(
    base_colors: List[Tuple[int, int, int]],
) -> Dict[str, Tuple[int, int, int, int]]:
    """Generate a color palette from base colors with improved contrast for text.

    Args:
        base_colors: List of base RGB color tuples

    Returns:
        Dictionary with color roles and RGB values
    """
    # Skip dynamic color generation if disabled in config
    if not config.FONT_CONFIG["USE_DYNAMIC_TITLE_COLORS"]:
        # Return a default palette with neutral colors and good contrast
        return {
            "background": (240, 240, 240),
            "divider": (180, 180, 180),
            "divider_border": (150, 150, 150),
            "text_bg": (240, 240, 240, 230),  # More opaque background (90%)
            "title_text": (20, 20, 20),  # Darker text for better contrast
            "subtitle_text": (50, 50, 50),  # Darker subtitle text
        }

    # Define contrast thresholds according to WCAG standards
    min_contrast_normal = max(
        5.5, config.FONT_CONFIG["DYNAMIC_TITLE_CONTRAST_THRESHOLD"]
    )
    min_contrast_large = 4.0  # Increased from 3.0 for large text (WCAG AA)

    if not base_colors:
        # Default palette if no colors provided - with better contrast
        return {
            "background": (222, 215, 211),
            "divider": (180, 180, 180),
            "divider_border": (150, 150, 150),
            "text_bg": (240, 240, 240, 230),  # More opaque background (90%)
            "title_text": (20, 20, 20),  # Darker text for better contrast
            "subtitle_text": (50, 50, 50),  # Darker subtitle text
        }

    # Sort colors by saturation (most saturated first)
    colors_with_hsv = []
    for color in base_colors:
        h, s, v = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)
        colors_with_hsv.append((color, h, s, v))

    colors_with_hsv.sort(key=lambda x: x[2], reverse=True)

    # Get the most saturated color for the divider
    divider_color = colors_with_hsv[0][0] if colors_with_hsv else (180, 180, 180)

    # Create a darker version for the border
    h, s, v = colorsys.rgb_to_hsv(
        divider_color[0] / 255, divider_color[1] / 255, divider_color[2] / 255
    )
    border_hsv = (h, s, max(0.1, v - 0.2))
    border_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(*border_hsv))

    # Create a text background that will provide good contrast with text
    # Start with a more neutral background color
    if v > 0.5:  # If the base color is light
        # Create a slightly darker, less saturated background
        text_bg_hsv = (h, min(0.15, s * 0.3), max(0.75, v - 0.15))
    else:  # If the base color is dark
        # Create a lighter, less saturated background
        text_bg_hsv = (h, min(0.15, s * 0.3), min(0.95, v + 0.6))

    text_bg_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(*text_bg_hsv))

    # Make the background more opaque (90% opacity) for better text contrast
    text_bg_with_alpha = text_bg_rgb + (230,)

    # Calculate relative luminance of the background color
    r, g, b = text_bg_rgb[:3]  # Use only RGB components
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Determine if background is light or dark (threshold at 0.5)
    is_light_bg = luminance > 0.5

    # Find colors from the extracted colors for the text elements
    title_text = None
    subtitle_text = None

    # Sort colors by contrast with background (highest contrast first)
    colors_by_contrast = []
    for color, h, s, v in colors_with_hsv:
        # Calculate contrast with the text background
        bg_contrast = calculate_contrast_ratio(text_bg_rgb, color)

        # If contrast is too low, adjust the color to improve contrast
        if bg_contrast < min_contrast_normal:
            adjusted_color = adjust_color_for_contrast(
                color, text_bg_rgb, min_contrast_normal
            )
            # Recalculate HSV values for the adjusted color
            adj_r, adj_g, adj_b = adjusted_color
            adj_h, adj_s, adj_v = colorsys.rgb_to_hsv(
                adj_r / 255, adj_g / 255, adj_b / 255
            )
            # Calculate new contrast with the adjusted color
            new_contrast = calculate_contrast_ratio(text_bg_rgb, adjusted_color)
            colors_by_contrast.append(
                (adjusted_color, adj_h, adj_s, adj_v, new_contrast)
            )
        else:
            colors_by_contrast.append((color, h, s, v, bg_contrast))

    colors_by_contrast.sort(key=lambda x: x[4], reverse=True)  # Sort by contrast

    # Try to find a color with good contrast for the title
    # First try: Find a vibrant color with good contrast for normal text
    for color, h, s, v, contrast in colors_by_contrast:
        if contrast >= min_contrast_normal and s >= 0.4 and 0.2 <= v <= 0.9:
            title_text = color
            # Create a slightly less saturated version for subtitle
            subtitle_hsv = (h, max(0.3, s - 0.1), v)  # Keep good saturation
            subtitle_rgb = tuple(
                int(x * 255) for x in colorsys.hsv_to_rgb(*subtitle_hsv)
            )
            subtitle_text = subtitle_rgb
            break

    # Second try: Find any color with good contrast for normal text
    if title_text is None and colors_by_contrast:
        for color, h, s, v, contrast in colors_by_contrast:
            if contrast >= min_contrast_normal:
                # Increase saturation to make the color pop more
                s = min(1.0, s * 1.3)

                # Adjust value based on background
                if is_light_bg and v > 0.5:
                    v = max(0.2, v - 0.2)  # Make darker on light backgrounds
                elif not is_light_bg and v < 0.5:
                    v = min(0.9, v + 0.2)  # Make lighter on dark backgrounds

                # Create more vibrant title color
                title_hsv = (h, s, v)
                title_text = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*title_hsv)
                )

                # Create a slightly adjusted version for subtitle
                if v > 0.5:  # If color is bright
                    subtitle_hsv = (h, s, max(0.2, v - 0.15))  # Make slightly darker
                else:  # If color is dark
                    subtitle_hsv = (h, s, min(0.9, v + 0.15))  # Make slightly lighter

                subtitle_rgb = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*subtitle_hsv)
                )
                subtitle_text = subtitle_rgb
                break

    # Third try: Find a vibrant color with acceptable contrast for large text
    if title_text is None and colors_by_contrast:
        for color, h, s, v, contrast in colors_by_contrast:
            if contrast >= min_contrast_large and s >= 0.4 and 0.2 <= v <= 0.9:
                # Increase saturation to make the color pop more
                s = min(1.0, s * 1.3)

                # Create more vibrant title color
                title_hsv = (h, s, v)
                title_text = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*title_hsv)
                )

                # Create a slightly less saturated version for subtitle
                subtitle_hsv = (h, max(0.3, s - 0.1), v)
                subtitle_rgb = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*subtitle_hsv)
                )
                subtitle_text = subtitle_rgb
                break

    # Fourth try: Find any color with acceptable contrast for large text
    if title_text is None and colors_by_contrast:
        for color, h, s, v, contrast in colors_by_contrast:
            if contrast >= min_contrast_large:
                # Increase saturation to make the color pop more
                s = min(1.0, s * 1.3)

                # Create more vibrant title color
                title_hsv = (h, s, v)
                title_text = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*title_hsv)
                )

                # Create a slightly adjusted version for subtitle
                if v > 0.5:  # If color is bright
                    subtitle_hsv = (h, s, max(0.2, v - 0.15))  # Make slightly darker
                else:  # If color is dark
                    subtitle_hsv = (h, s, min(0.9, v + 0.15))  # Make slightly lighter

                subtitle_rgb = tuple(
                    int(x * 255) for x in colorsys.hsv_to_rgb(*subtitle_hsv)
                )
                subtitle_text = subtitle_rgb
                break

    # If we still couldn't find a suitable color, use high-contrast fallback colors
    if title_text is None:
        # Choose contrasting colors based on background luminance
        if is_light_bg:
            # For light backgrounds, use a dark, saturated color
            # Start with a dark blue-ish color for better visual appeal than pure black
            h_value = 0.6  # Blue-ish hue
            title_text = tuple(
                int(x * 255) for x in colorsys.hsv_to_rgb(h_value, 0.7, 0.2)
            )
            subtitle_text = tuple(
                int(x * 255) for x in colorsys.hsv_to_rgb(h_value, 0.6, 0.3)
            )
        else:
            # For dark backgrounds, use a light, saturated color
            # Start with a yellow-ish color for better visual appeal than pure white
            h_value = 0.15  # Yellow-ish hue
            title_text = tuple(
                int(x * 255) for x in colorsys.hsv_to_rgb(h_value, 0.3, 0.95)
            )
            subtitle_text = tuple(
                int(x * 255) for x in colorsys.hsv_to_rgb(h_value, 0.25, 0.9)
            )

        # Use our adjustment function to ensure proper contrast
        title_text = adjust_color_for_contrast(
            title_text, text_bg_rgb, min_contrast_normal
        )
        subtitle_text = adjust_color_for_contrast(
            subtitle_text, text_bg_rgb, min_contrast_normal
        )

    # Use a neutral background color for the main canvas
    background = (240, 240, 240) if v < 0.5 else (220, 220, 220)

    return {
        "background": background,
        "divider": divider_color,
        "divider_border": border_rgb,
        "text_bg": text_bg_with_alpha,  # Now includes alpha channel
        "title_text": title_text,
        "subtitle_text": subtitle_text,
    }


def create_dynamic_overlay(
    width: int,
    height: int,
    palette: Dict[str, Tuple],
    title: str,
    num_images: int = 12,
    sample_image: Optional[Image.Image] = None,
) -> Image.Image:
    """
    Create a dynamic overlay with colors from the palette.

    Args:
        width: Width of the overlay
        height: Height of the overlay
        palette: Color palette to use
        title: Title text to display
        num_images: Number of images in the pattern set
        sample_image: Optional image to use as a semi-transparent overlay on the backdrop

    Returns:
        RGBA image with the overlay
    """
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

    # Load fonts and prepare text elements using the font configuration
    # Calculate default font sizes based on divider height if not specified in config
    top_subtitle_font_size = config.FONT_CONFIG["TOP_SUBTITLE_FONT_SIZE"]
    if top_subtitle_font_size <= 0:
        # Make top subtitle larger - the number part will be made larger separately
        top_subtitle_font_size = int(
            divider_height * 0.5
        )  # Larger size for "Seamless Patterns" text

    bottom_subtitle_font_size = config.FONT_CONFIG["BOTTOM_SUBTITLE_FONT_SIZE"]
    if bottom_subtitle_font_size <= 0:
        bottom_subtitle_font_size = int(
            divider_height * 0.4
        )  # Larger size for bottom subtitle

    title_font_size = config.FONT_CONFIG["TITLE_FONT_SIZE"]
    if title_font_size <= 0:
        title_font_size = divider_height // 1.0

    # Get font names from configuration
    title_font_name = config.FONT_CONFIG["TITLE_FONT"]
    subtitle_font_name = config.FONT_CONFIG["SUBTITLE_FONT"]

    # Load the fonts
    top_subtitle_font = get_font(subtitle_font_name, size=top_subtitle_font_size)
    bottom_subtitle_font = get_font(subtitle_font_name, size=bottom_subtitle_font_size)
    title_font = get_font(title_font_name, size=title_font_size)

    # Top subtitle - only make the number larger, not the text
    subtitle_text = f"{num_images} Seamless Patterns"
    subtitle_width, subtitle_height = calculate_text_dimensions(
        draw, subtitle_text, top_subtitle_font
    )

    # Main title - adjust font size to fit
    max_title_width = width // 2 - 80  # Maximum width with some margin
    title_width, title_height = calculate_text_dimensions(draw, title, title_font)
    while title_width > max_title_width and title_font_size > 20:
        title_font_size -= 5
        title_font = get_font(title_font_name, size=title_font_size)
        title_width, title_height = calculate_text_dimensions(draw, title, title_font)

    # Bottom subtitle
    bottom_subtitle_text = f"commercial use  |  300 dpi  |  12x12in jpg"
    bottom_subtitle_width, bottom_subtitle_height = calculate_text_dimensions(
        draw, bottom_subtitle_text, bottom_subtitle_font
    )

    # Calculate text dimensions and padding
    padding_x = 40  # Horizontal padding
    padding_y = 30  # Vertical padding

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
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2

    # Create text backdrop with sample image overlay if provided
    text_backdrop = create_text_backdrop(
        width=text_width,
        height=text_height,
        background_color=palette["text_bg"],
        border_color=palette["divider_border"],
        border_thickness=border_thickness,
        border_radius=15,
        sample_image=sample_image,
        sample_opacity=60,
    )

    # Paste the text backdrop onto the overlay
    overlay.paste(text_backdrop, (text_x, text_y), text_backdrop)

    # Add text
    # Position text elements with perfect centering

    # Center the title horizontally and position it slightly lower than center vertically
    # to be more evenly spaced between the top and bottom subtitles
    title_x = (width - title_width) // 2

    # Calculate a position that's shifted down from the center by a small amount
    # This creates more even spacing between the title and both subtitles
    vertical_offset = 20  # Pixels to move the title down from center
    title_y = text_y + (text_height - title_height) // 2 + vertical_offset

    # Position top subtitle at the absolute top of the backdrop
    # Move it to the very top with almost no padding
    # Add just enough padding to prevent text from touching the border
    top_padding = 5  # Absolute minimum padding from the top of the backdrop
    subtitle_y = text_y + top_padding + (subtitle_height // 2)

    # Position bottom subtitle near the bottom of the backdrop
    bottom_subtitle_x = (width - bottom_subtitle_width) // 2
    # Calculate position from the bottom of the backdrop with minimal padding
    bottom_padding = 15  # Minimal padding from the bottom of the backdrop
    bottom_subtitle_y = text_y + text_height - bottom_subtitle_height - bottom_padding

    # Draw text elements with dynamic color selection for readability
    # Top subtitle - split into number and text with different font sizes
    number_part = f"{num_images}"
    text_part = " Seamless Patterns"

    # Create a much larger font just for the number
    number_font_size = int(
        top_subtitle_font_size * 2.2
    )  # 120% larger than the regular subtitle font
    number_font = get_font(subtitle_font_name, size=number_font_size)

    # Calculate the width of the number part
    number_width, number_height = calculate_text_dimensions(
        draw, number_part, number_font
    )

    # Calculate the width of the text part
    text_width, text_height = calculate_text_dimensions(
        draw, text_part, top_subtitle_font
    )

    # Calculate the total width to center properly
    total_width = number_width + text_width

    # Calculate the starting position to center the whole text
    start_x = (width - total_width) // 2

    # Draw the number part with the larger font
    # Calculate baseline alignment more precisely for better vertical alignment
    # Get the descent value for both fonts to align them properly
    try:
        # For newer Pillow versions that support font metrics
        number_metrics = number_font.getmetrics()
        text_metrics = top_subtitle_font.getmetrics()
        number_descent = number_metrics[1]
        text_descent = text_metrics[1]

        # Adjust position to align baselines and move number up
        number_y_offset = (number_height - text_height) - (
            number_descent - text_descent
        )
        # Move the number up by adding an additional vertical offset
        vertical_offset = 25  # Pixels to move the number up
        number_y = subtitle_y - number_y_offset // 2 - vertical_offset
    except (AttributeError, IndexError):
        # Fallback for older Pillow versions
        vertical_offset = 25  # Same offset as above
        number_y = subtitle_y - (number_height - text_height) // 2 - vertical_offset

    draw_text(
        draw=draw,
        position=(start_x, number_y),
        text=number_part,
        font=number_font,
        text_color=palette["subtitle_text"],
    )

    # Draw the "Seamless Patterns" part with the regular font
    draw_text(
        draw=draw,
        position=(start_x + number_width, subtitle_y),
        text=text_part,
        font=top_subtitle_font,
        text_color=palette["subtitle_text"],
    )

    # Main title
    draw_text(
        draw=draw,
        position=(title_x, title_y),
        text=title,
        font=title_font,
        text_color=palette["title_text"],
    )

    # Bottom subtitle
    draw_text(
        draw=draw,
        position=(bottom_subtitle_x, bottom_subtitle_y),
        text=bottom_subtitle_text,
        font=bottom_subtitle_font,
        text_color=palette["subtitle_text"],
    )

    return overlay


def create_main_mockup(
    input_folder: str,
    title: str,
    title_font: str = None,
    subtitle_font: str = None,
    title_font_size: int = None,
    top_subtitle_font_size: int = None,
    bottom_subtitle_font_size: int = None,
    use_dynamic_title_colors: bool = None,
    top_subtitle_padding: int = None,
    bottom_subtitle_padding: int = None,
) -> Optional[str]:
    """
    Creates the main 2x6 grid mockup with a dynamic overlay.

    Args:
        input_folder: Path to the input folder containing images
        title: Title to display on the mockup
        title_font: Optional custom title font
        subtitle_font: Optional custom subtitle font
        title_font_size: Optional custom title font size
        top_subtitle_font_size: Optional custom top subtitle font size
        bottom_subtitle_font_size: Optional custom bottom subtitle font size
        use_dynamic_title_colors: Whether to use dynamic title colors
        top_subtitle_padding: Optional custom top subtitle padding
        bottom_subtitle_padding: Optional custom bottom subtitle padding

    Returns:
        Path to the created main mockup file, or None if creation failed
    """
    logger.info(f"Creating dynamic main mockup for '{title}'...")

    # Update font, color, and spacing configuration if custom settings are provided
    if (
        title_font
        or subtitle_font
        or title_font_size is not None
        or top_subtitle_font_size is not None
        or bottom_subtitle_font_size is not None
        or use_dynamic_title_colors is not None
        or top_subtitle_padding is not None
        or bottom_subtitle_padding is not None
    ):
        config.update_font_config(
            title_font=title_font,
            subtitle_font=subtitle_font,
            title_font_size=title_font_size,
            top_subtitle_font_size=top_subtitle_font_size,
            bottom_subtitle_font_size=bottom_subtitle_font_size,
            use_dynamic_title_colors=use_dynamic_title_colors,
            top_subtitle_padding=top_subtitle_padding,
            bottom_subtitle_padding=bottom_subtitle_padding,
        )

    # Log whether dynamic title colors are enabled
    if config.FONT_CONFIG["USE_DYNAMIC_TITLE_COLORS"]:
        logger.info("Using dynamic title colors based on input image")
    else:
        logger.info("Using default title colors (dynamic colors disabled)")

    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    # Define grid dimensions
    GRID_ROWS, GRID_COLS = 2, 6
    grid_width = 3000
    grid_height = 2250

    # Find all images in the input folder
    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        logger.warning(f"No images found in {input_folder} for main mockup.")
        return None

    # Extract colors from the images
    extracted_colors = extract_colors_from_images(images)
    color_palette = generate_color_palette(extracted_colors)

    # Import image utilities here to avoid circular imports
    from utils.image_utils import resize_image

    # Create background
    background_color = color_palette["background"]
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
                shadow = resize_image(shadow_img, shadow_new_width, cell_height)
        except Exception as e:
            logger.warning(f"Error loading or resizing shadow: {e}. Skipping shadow.")

    # First pass: Draw images
    image_positions_for_shadow = []
    images_to_place = images[: GRID_ROWS * GRID_COLS]
    num_images = len(images)

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
            row_index = i // GRID_COLS
            col_index = i % GRID_COLS
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

    # Create and add dynamic overlay
    try:
        dynamic_overlay = create_dynamic_overlay(
            width=grid_width,
            height=grid_height,
            palette=color_palette,
            title=title,
            num_images=num_images,
            sample_image=sample_image,
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
        grid_filename = "main.png"
        save_path = os.path.join(output_folder, grid_filename)
        final_image.save(save_path, "PNG")
        logger.info(f"Dynamic main mockup saved: {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"Error saving dynamic main mockup: {e}")
        return None
