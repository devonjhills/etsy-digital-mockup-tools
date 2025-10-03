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

# Import unified configuration
from core.config_manager import get_config_manager

# Get configuration manager
config_manager = get_config_manager()
pattern_config = config_manager.get_config("pattern")

# Legacy compatibility wrapper
class PatternConfig:
    @property
    def FONT_CONFIG(self):
        if pattern_config:
            font_settings = pattern_config.font_settings
            layout_settings = pattern_config.layout_settings
            color_settings = pattern_config.color_settings
            
            return {
                "USE_DYNAMIC_TITLE_COLORS": color_settings.get("use_dynamic_title_colors", True),
                "TOP_SUBTITLE_FONT_SIZE": font_settings.get("top_subtitle_font_size", 24),
                "BOTTOM_SUBTITLE_FONT_SIZE": font_settings.get("bottom_subtitle_font_size", 20),
                "TITLE_FONT_SIZE": font_settings.get("title_font_size", 250),
                "TITLE_FONT": font_settings.get("title_font", "GreatVibes-Regular"),
                "SUBTITLE_FONT": font_settings.get("subtitle_font", "LibreBaskerville-Italic"),
                "TOP_SUBTITLE_PADDING": layout_settings.get("top_subtitle_padding", 60),
                "BOTTOM_SUBTITLE_PADDING": layout_settings.get("bottom_subtitle_padding", 55),
            }
        else:
            # Fallback configuration
            return {
                "USE_DYNAMIC_TITLE_COLORS": True,
                "TOP_SUBTITLE_FONT_SIZE": 24,
                "BOTTOM_SUBTITLE_FONT_SIZE": 20,
                "TITLE_FONT_SIZE": 250,
                "TITLE_FONT": "GreatVibes-Regular",
                "SUBTITLE_FONT": "LibreBaskerville-Italic",
                "TOP_SUBTITLE_PADDING": 60,
                "BOTTOM_SUBTITLE_PADDING": 55,
            }
    
    @classmethod
    def update_font_config(cls, updates):
        """Update font configuration - legacy compatibility."""
        # This would need to update the config manager in the future
        pass

config = PatternConfig()

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
            "text_bg": (40, 40, 40, 220),  # Darker background with opacity
            "title_text": (255, 255, 255),  # White text for contrast
            "subtitle_text": (255, 255, 255),  # White subtitle text
        }

    # Use a fixed dark backdrop color with opacity for text background
    text_bg_rgb = (40, 40, 40)
    text_bg_with_alpha = text_bg_rgb + (220,)  # Dark backdrop with opacity

    # Calculate relative luminance of the background color
    r, g, b = text_bg_rgb[:3]  # Use only RGB components
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Determine if background is light or dark (threshold at 0.5)
    is_light_bg = luminance > 0.5

    # Choose text colors based on backdrop luminance
    if is_light_bg:
        title_text = (0, 0, 0)  # Black text on light background
        subtitle_text = (0, 0, 0)
    else:
        title_text = (255, 255, 255)  # White text on dark background
        subtitle_text = (255, 255, 255)

    # Get the most saturated color for the divider
    colors_with_hsv = []
    for color in base_colors:
        h, s, v = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)
        colors_with_hsv.append((color, h, s, v))

    colors_with_hsv.sort(key=lambda x: x[2], reverse=True)
    divider_color = colors_with_hsv[0][0] if colors_with_hsv else (180, 180, 180)

    # Create a darker version for the border
    h, s, v = colorsys.rgb_to_hsv(
        divider_color[0] / 255, divider_color[1] / 255, divider_color[2] / 255
    )
    border_hsv = (h, s, max(0.1, v - 0.2))
    border_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(*border_hsv))

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
    # Add extra padding to the text backdrop for more space around subtitles
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

    # Adjust the position to center the larger backdrop
    backdrop_x = (width - backdrop_width) // 2
    backdrop_y = (height - backdrop_height) // 2

    # Paste the text backdrop onto the overlay
    overlay.paste(text_backdrop, (backdrop_x, backdrop_y), text_backdrop)

    # Add text
    # Position text elements with perfect centering

    # Position top subtitle with padding from the top of the backdrop
    top_padding = 20
    subtitle_y = backdrop_y + top_padding + (subtitle_height // 2)

    # Position bottom subtitle near the bottom of the backdrop
    bottom_subtitle_x = (width - bottom_subtitle_width) // 2
    bottom_padding = 30
    bottom_subtitle_y = (
        backdrop_y + backdrop_height - bottom_subtitle_height - bottom_padding
    )

    # Center the title horizontally
    title_x = (width - title_width) // 2

    # Center the title vertically between the top and bottom subtitles
    # Calculate the space between subtitles and center the title in that space
    space_top = subtitle_y + subtitle_height
    space_bottom = bottom_subtitle_y
    title_y = space_top + (space_bottom - space_top - title_height) // 2

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
        vertical_offset = 30  # Increased pixels to move the number up
        number_y = subtitle_y - number_y_offset // 2 - vertical_offset
    except (AttributeError, IndexError):
        # Fallback for older Pillow versions
        vertical_offset = 30  # Same offset as above
        number_y = subtitle_y - (number_height - text_height) // 2 - vertical_offset

    draw_text(
        draw=draw,
        position=(start_x, number_y),
        text=number_part,
        font=number_font,
        text_color=palette["subtitle_text"],
    )
    logger.info(f"Drawing number part with color: {palette['subtitle_text']}")

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
    logger.info(f"Drawing title with color: {palette['title_text']}")

    # Bottom subtitle
    draw_text(
        draw=draw,
        position=(bottom_subtitle_x, bottom_subtitle_y),
        text=bottom_subtitle_text,
        font=bottom_subtitle_font,
        text_color=palette["subtitle_text"],
    )
    logger.info(f"Drawing bottom subtitle with color: {palette['subtitle_text']}")

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
    custom_top_subtitle: str = None,
    custom_bottom_subtitle: str = None,
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


def adjust_color_for_contrast(
    text_color: Tuple[int, int, int],
    bg_color: Tuple[int, int, int],
    min_contrast: float,
) -> Tuple[int, int, int]:
    """
    Adjust the text color to ensure it has sufficient contrast against the background color.

    Args:
        text_color: The original text color as an RGB tuple.
        bg_color: The background color as an RGB tuple.
        min_contrast: The minimum contrast ratio required.

    Returns:
        The adjusted text color as an RGB tuple.
    """

    def luminance(color: Tuple[int, int, int]) -> float:
        r, g, b = [x / 255 for x in color]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def contrast_ratio(
        color1: Tuple[int, int, int], color2: Tuple[int, int, int]
    ) -> float:
        lum1 = luminance(color1)
        lum2 = luminance(color2)
        return (max(lum1, lum2) + 0.05) / (min(lum1, lum2) + 0.05)

    current_contrast = contrast_ratio(text_color, bg_color)

    if current_contrast >= min_contrast:
        return text_color

    # Adjust the text color to meet the minimum contrast ratio
    # Start by increasing the brightness of the text color
    r, g, b = text_color
    step = 10
    while current_contrast < min_contrast and r < 255 and g < 255 and b < 255:
        r = min(255, r + step)
        g = min(255, g + step)
        b = min(255, b + step)
        current_contrast = contrast_ratio((r, g, b), bg_color)

    if current_contrast >= min_contrast:
        return (r, g, b)

    # If increasing brightness doesn't work, try decreasing it
    r, g, b = text_color
    while current_contrast < min_contrast and r > 0 and g > 0 and b > 0:
        r = max(0, r - step)
        g = max(0, g - step)
        b = max(0, b - step)
        current_contrast = contrast_ratio((r, g, b), bg_color)

    return (r, g, b)
