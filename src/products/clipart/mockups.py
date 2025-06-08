"""
Module for creating square mockups with a 2x3 grid (2 columns, 3 rows) and title overlay.
"""

import random
import colorsys
from typing import List, Tuple, Optional
from PIL import Image, ImageStat

from src.utils.common import setup_logging, get_resampling_filter, safe_load_image
from src.products.clipart.title import add_title_bar_and_text

# Set up logging
logger = setup_logging(__name__)


def arrange_images_around_text(
    input_image_paths: List[str],
    canvas: Image.Image,
    text_bounds: Tuple[int, int, int, int],
    padding: int = 30,
) -> Image.Image:
    """
    Arrange images beautifully around the text area, filling the entire canvas.

    Args:
        input_image_paths: List of paths to images
        canvas: Background canvas image
        text_bounds: Bounds of the text area to avoid (x1, y1, x2, y2)
        padding: Padding between images

    Returns:
        Canvas with arranged images
    """
    if not input_image_paths:
        logger.warning("No input images provided for arrangement.")
        return canvas

    # Make a copy of the canvas
    result = canvas.copy()
    canvas_width, canvas_height = result.size

    # Extract text area bounds
    text_x1, text_y1, text_x2, text_y2 = text_bounds

    # Define positions for 8 images around the text:
    # - 3 images in the top row
    # - 2 images on the sides of the text (left and right)
    # - 3 images in the bottom row

    # Calculate column widths for 3 columns
    col_width = (canvas_width - (4 * padding)) // 3

    # Calculate row heights for 2 rows with text in the middle
    top_row_height = text_y1 - (2 * padding)
    bottom_row_height = canvas_height - text_y2 - (2 * padding)

    positions = [
        # Top row - left
        (padding, padding, padding + col_width, text_y1 - padding),
        # Top row - middle
        (
            padding * 2 + col_width,
            padding,
            padding * 2 + col_width * 2,
            text_y1 - padding,
        ),
        # Top row - right
        (
            padding * 3 + col_width * 2,
            padding,
            canvas_width - padding,
            text_y1 - padding,
        ),
        # Middle row - left side of text
        (padding, text_y1, text_x1 - padding, text_y2),
        # Middle row - right side of text
        (text_x2 + padding, text_y1, canvas_width - padding, text_y2),
        # Bottom row - left
        (padding, text_y2 + padding, padding + col_width, canvas_height - padding),
        # Bottom row - middle
        (
            padding * 2 + col_width,
            text_y2 + padding,
            padding * 2 + col_width * 2,
            canvas_height - padding,
        ),
        # Bottom row - right
        (
            padding * 3 + col_width * 2,
            text_y2 + padding,
            canvas_width - padding,
            canvas_height - padding,
        ),
    ]

    # Adjust positions to ensure they have reasonable sizes
    for i, pos in enumerate(positions):
        x1, y1, x2, y2 = pos
        # Ensure minimum size
        min_width = canvas_width // 8

        # Different minimum heights for different rows
        if i < 3:  # Top row
            min_height = top_row_height // 2
        elif i < 5:  # Middle row (sides of text)
            min_height = (text_y2 - text_y1) // 2
            min_width = (
                min((text_x1 - (2 * padding)), (canvas_width - text_x2 - (2 * padding)))
                // 2
            )
        else:  # Bottom row
            min_height = bottom_row_height // 2

        # Ensure minimum width
        if x2 - x1 < min_width:
            if i == 3:  # Left side of text
                x2 = x1 + min_width
            elif i == 4:  # Right side of text
                x1 = x2 - min_width
            elif i % 3 == 0 or (i - 5) % 3 == 0:  # Left column
                x2 = x1 + min_width
            elif i % 3 == 1 or (i - 5) % 3 == 1:  # Middle column
                x1 = (x1 + x2 - min_width) // 2
                x2 = x1 + min_width
            else:  # Right column
                x1 = x2 - min_width

        # Ensure minimum height
        if y2 - y1 < min_height:
            if i < 3:  # Top row
                y2 = y1 + min_height
            elif i < 5:  # Middle row
                # Center vertically in the middle section
                center_y = (text_y1 + text_y2) // 2
                half_height = min_height // 2
                y1 = center_y - half_height
                y2 = center_y + half_height
            else:  # Bottom row
                y1 = y2 - min_height

        positions[i] = (x1, y1, x2, y2)

    # Ensure we have enough images (duplicate if needed)
    image_paths = input_image_paths.copy()
    while len(image_paths) < 8 and len(input_image_paths) > 0:
        # Add more images by duplicating existing ones
        image_paths.extend(
            input_image_paths[: min(8 - len(image_paths), len(input_image_paths))]
        )

    # Randomize image order slightly for more organic feel
    if len(image_paths) > 3:
        random.shuffle(image_paths)

    logger.info(f"Using {min(len(image_paths), 8)} images for the main mockup")

    # Place images in the defined positions - use exactly 8 images
    used_images = []
    for i, img_path in enumerate(image_paths[:8]):
        try:
            # Load image
            img = safe_load_image(img_path, "RGBA")
            if not img:
                logger.warning(f"Failed to load image: {img_path}")
                continue

            # Track successfully loaded images
            used_images.append(img_path)

            # Get position
            x1, y1, x2, y2 = positions[i]
            pos_width = x2 - x1
            pos_height = y2 - y1

            # Resize image to fit position while maintaining aspect ratio
            img_aspect = img.width / img.height if img.height > 0 else 1

            # Determine if this is a corner image (positions 0, 2, 5, 7)
            is_corner_image = i in [0, 2, 5, 7]

            # Scale factor - make corner images larger
            scale_factor = 1.35 if is_corner_image else 1.0

            # For all positions, we want to fill the space completely
            # while maintaining aspect ratio
            if pos_width / pos_height > img_aspect:
                # Position is wider than image aspect ratio, fit to width
                img_width = int(pos_width * scale_factor)
                img_height = int(img_width / img_aspect)
            else:
                # Position is taller than image aspect ratio, fit to height
                img_height = int(pos_height * scale_factor)
                img_width = int(img_height * img_aspect)

            # Resize image
            img_resized = img.resize((img_width, img_height), get_resampling_filter())

            # Center in position
            x_centered = x1 + (pos_width - img_width) // 2
            y_centered = y1 + (pos_height - img_height) // 2

            # Paste image
            result.paste(img_resized, (x_centered, y_centered), img_resized)

            logger.info(f"Placed image {i+1} at position {positions[i]}: {img_path}")

        except Exception as e:
            logger.error(f"Error processing image {img_path} for arrangement: {e}")

    # Log how many images were actually used
    logger.info(f"Successfully placed {len(used_images)} images in the mockup")

    return result, used_images


def extract_colors_from_images(
    input_image_paths: List[str], num_colors: int = 5
) -> List[Tuple[int, int, int, int]]:
    """
    Extract dominant colors from input images.

    Args:
        input_image_paths: List of paths to images
        num_colors: Number of colors to extract

    Returns:
        List of RGBA color tuples
    """
    if not input_image_paths:
        return [(50, 50, 50, 255)]  # Default dark gray

    # Sample a subset of images for efficiency
    sample_paths = input_image_paths[: min(5, len(input_image_paths))]
    colors = []

    for img_path in sample_paths:
        try:
            # Load image
            img = safe_load_image(img_path, "RGB")
            if not img:
                continue

            # Resize for faster processing
            img_small = img.resize((50, 50), get_resampling_filter())

            # Get image stats
            stat = ImageStat.Stat(img_small)
            avg_color = tuple(map(int, stat.mean))

            # Convert to HSV to check if it's a good color for text
            r, g, b = avg_color
            _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)  # h is unused

            # We want darker colors (lower value) with some saturation
            if v < 0.7 and v > 0.2 and s > 0.2:
                colors.append((*avg_color, 255))  # Add alpha channel
        except Exception as e:
            logger.error(f"Error extracting colors from {img_path}: {e}")

    # If we couldn't extract any suitable colors, return default
    if not colors:
        return [(50, 50, 50, 255)]  # Default dark gray

    # Sort by darkness (lower sum = darker)
    colors.sort(key=lambda c: sum(c[:3]))

    # Return the darkest colors first
    return colors[:num_colors]


def select_text_color(
    colors: List[Tuple[int, int, int, int]], bg_color: Tuple[int, int, int]
) -> Tuple[int, int, int, int]:
    """
    Select an appropriate text color from the extracted colors,
    ensuring good contrast with the background.

    Args:
        colors: List of extracted colors
        bg_color: Background color to check contrast against

    Returns:
        Selected text color (RGBA)
    """
    if not colors:
        return (50, 50, 50, 255)  # Default dark gray

    # Calculate background brightness
    bg_brightness = sum(bg_color) / 3

    # Function to calculate contrast ratio (simplified version)
    def has_good_contrast(color, _):
        # Calculate color brightness
        color_brightness = sum(color[:3]) / 3

        # Calculate contrast
        if bg_brightness > color_brightness:
            contrast = (bg_brightness + 50) / (
                color_brightness + 50
            )  # Add small value to avoid division by zero
        else:
            contrast = (color_brightness + 50) / (bg_brightness + 50)

        return contrast >= 3.0  # Good contrast threshold

    # Try to find a color with good contrast
    for color in colors:
        if has_good_contrast(color, bg_color):
            return color

    # If no color has good contrast, use black or white based on background brightness
    if bg_brightness < 128:
        return (255, 255, 255, 255)  # White for dark backgrounds
    else:
        return (50, 50, 50, 255)  # Dark gray for light backgrounds


def create_square_mockup(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    title: str,
    subtitle_top: str = "",
    subtitle_bottom: str = "",
    grid_size: Tuple[int, int] = (2000, 2000),
    padding: int = 30,
    title_font_name: str = None,
    subtitle_font_name: str = None,
    title_max_font_size: int = None,
    title_min_font_size: int = None,
    title_font_step: int = None,
    subtitle_font_size: int = None,
    # title_max_lines parameter removed as we always use a single line
    title_line_spacing: int = 15,
    subtitle_spacing: int = 25,
    title_padding_x: int = 60,  # Smaller than the default 80
) -> Tuple[Optional[Image.Image], List[str]]:
    """
    Create a square mockup with text in the center and images beautifully arranged around it.

    Args:
        input_image_paths: List of paths to images
        canvas_bg_image: Background image for the canvas
        title: The title text
        subtitle_top: The top subtitle text
        subtitle_bottom: The bottom subtitle text
        grid_size: Size of the grid (width, height)
        padding: Padding between images
        title_font_name: The font name for the title
        subtitle_font_name: The font name for the subtitle
        title_max_font_size: The maximum font size for the title
        title_min_font_size: The minimum font size for the title
        title_font_step: The step size for reducing the title font size
        subtitle_font_size: The font size for the subtitle
        # title_max_lines parameter removed as we always use a single line
        title_line_spacing: The spacing between title lines
        subtitle_spacing: The spacing between title and subtitle
        title_padding_x: The horizontal padding for the title

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

    logger.info(
        f"Creating square mockup with size {grid_size[0]}x{grid_size[1]} pixels"
    )

    # Create a blank canvas for our new layout
    logger.info("Creating canvas for beautiful image arrangement...")
    grid_image = canvas.copy()

    # Extract colors from input images for text
    logger.info("Extracting colors from input images for text...")
    extracted_colors = extract_colors_from_images(input_image_paths)

    # Sample background color from the center of the canvas
    bg_sample = canvas.resize((1, 1), get_resampling_filter())
    bg_color = bg_sample.getpixel((0, 0))

    # Select appropriate text color with good contrast
    selected_text_color = select_text_color(extracted_colors, bg_color)

    # Create a slightly lighter version for subtitle
    r, g, b, a = selected_text_color
    subtitle_color = (min(r + 30, 255), min(g + 30, 255), min(b + 30, 255), a)

    logger.info(f"Selected text color: {selected_text_color}")

    # Default configuration values
    DEFAULT_FONT_CONFIG = {
        "TITLE_FONT": "GreatVibes-Regular",
        "SUBTITLE_FONT": "LibreBaskerville-Italic", 
        "TITLE_MAX_FONT_SIZE": 250,
        "TITLE_MIN_FONT_SIZE": 40,
        "SUBTITLE_FONT_SIZE": 60
    }
    DEFAULT_TITLE_FONT_STEP = 5

    # Add title overlay
    logger.info("Adding title overlay...")

    # Use provided values or fall back to config values
    title_style_args = {
        "title_font_name": (
            title_font_name
            if title_font_name is not None
            else DEFAULT_FONT_CONFIG["TITLE_FONT"]
        ),
        "subtitle_font_name": (
            subtitle_font_name
            if subtitle_font_name is not None
            else DEFAULT_FONT_CONFIG["SUBTITLE_FONT"]
        ),
        "title_max_font_size": (
            title_max_font_size
            if title_max_font_size is not None
            else DEFAULT_FONT_CONFIG["TITLE_MAX_FONT_SIZE"]
        ),
        "title_min_font_size": (
            title_min_font_size
            if title_min_font_size is not None
            else DEFAULT_FONT_CONFIG["TITLE_MIN_FONT_SIZE"]
        ),
        "title_font_step": (
            title_font_step if title_font_step is not None else DEFAULT_TITLE_FONT_STEP
        ),
        "subtitle_font_size": (
            subtitle_font_size
            if subtitle_font_size is not None
            else DEFAULT_FONT_CONFIG["SUBTITLE_FONT_SIZE"]
        ),
        # title_max_lines removed as we always use a single line
        "title_line_spacing": title_line_spacing,
        "subtitle_spacing": subtitle_spacing,
        "title_padding_x": title_padding_x,
        "text_color": selected_text_color,
        "subtitle_text_color": subtitle_color,
    }

    logger.info(f"Using title font: {title_style_args['title_font_name']}")
    logger.info(f"Using subtitle font: {title_style_args['subtitle_font_name']}")

    # Create a blank layer for the title
    title_layer = Image.new("RGBA", grid_size, (0, 0, 0, 0))

    # Add title to the blank layer
    title_image, text_bounds = add_title_bar_and_text(
        image=title_layer,
        background_image=grid_image,
        title=title,
        subtitle_top=subtitle_top,
        subtitle_bottom=subtitle_bottom,
        **title_style_args,
    )

    if not title_image:
        logger.warning("Failed to add title overlay. Using blank title layer.")
        text_bounds = (
            grid_size[0] // 4,
            grid_size[1] // 4,
            grid_size[0] * 3 // 4,
            grid_size[1] * 3 // 4,
        )

    # Arrange images beautifully around the text
    logger.info("Arranging images beautifully around the text...")
    arranged_image, used_images = arrange_images_around_text(
        input_image_paths=input_image_paths[:8],  # Use first 8 images
        canvas=grid_image,
        text_bounds=text_bounds,
        padding=padding,
    )

    if title_image:
        # Composite title onto arranged image
        final_image = Image.alpha_composite(arranged_image.convert("RGBA"), title_image)
        logger.info(f"Final mockup created with {len(used_images)} images")
        return final_image, used_images
    else:
        logger.warning("Failed to add title overlay. Returning arranged image only.")
        logger.info(f"Final mockup created with {len(used_images)} images")
        return arranged_image, used_images
