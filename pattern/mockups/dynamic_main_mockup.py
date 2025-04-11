"""
Module for creating a dynamic main pattern mockup with colors extracted from the pattern.
"""

import os
import glob
from typing import Optional, Tuple, List, Dict
import colorsys
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageStat, ImageEnhance

from utils.common import (
    setup_logging,
    get_resampling_filter,
    get_asset_path,
    ensure_dir_exists,
    get_font,
)

# Set up logging
logger = setup_logging(__name__)


def extract_colors_from_images(
    images: List[str], num_colors: int = 5
) -> List[Tuple[int, int, int]]:
    """
    Extract dominant colors from a list of images.

    Args:
        images: List of image paths
        num_colors: Number of dominant colors to extract

    Returns:
        List of RGB color tuples
    """
    if not images:
        logger.warning("No images provided for color extraction")
        return [(222, 215, 211)]  # Default background color

    # Use the first few images for color extraction
    sample_images = images[: min(3, len(images))]
    all_colors = []

    for img_path in sample_images:
        try:
            with Image.open(img_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize for faster processing
                img.thumbnail((100, 100))

                # Get image statistics
                stat = ImageStat.Stat(img)
                avg_color = tuple(map(int, stat.mean))
                all_colors.append(avg_color)

                # Sample pixels from different regions
                width, height = img.size
                regions = [
                    (0, 0, width // 2, height // 2),
                    (width // 2, 0, width, height // 2),
                    (0, height // 2, width // 2, height),
                    (width // 2, height // 2, width, height),
                    (width // 4, height // 4, 3 * width // 4, 3 * height // 4),
                ]

                for region in regions:
                    region_img = img.crop(region)
                    region_stat = ImageStat.Stat(region_img)
                    region_color = tuple(map(int, region_stat.mean))
                    all_colors.append(region_color)

        except Exception as e:
            logger.error(f"Error extracting colors from {img_path}: {e}")

    # If we couldn't extract any colors, return default
    if not all_colors:
        return [(222, 215, 211)]  # Default background color

    # Filter out very similar colors
    filtered_colors = []
    for color in all_colors:
        # Convert to HSV for better color comparison
        h, s, v = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)

        # Skip very dark or very light colors
        if v < 0.2 or v > 0.95:
            continue

        # Skip colors with very low saturation
        if s < 0.1:
            continue

        # Check if this color is too similar to ones we've already kept
        is_unique = True
        for existing_color in filtered_colors:
            existing_h, existing_s, existing_v = colorsys.rgb_to_hsv(
                existing_color[0] / 255,
                existing_color[1] / 255,
                existing_color[2] / 255,
            )

            # Calculate color distance in HSV space
            h_diff = min(abs(h - existing_h), 1 - abs(h - existing_h))
            s_diff = abs(s - existing_s)
            v_diff = abs(v - existing_v)

            # If colors are too similar, skip this one
            if h_diff < 0.1 and s_diff < 0.2 and v_diff < 0.2:
                is_unique = False
                break

        if is_unique:
            filtered_colors.append(color)

    # If filtering removed all colors, return the original average colors
    if not filtered_colors:
        filtered_colors = all_colors

    # Return the requested number of colors
    return filtered_colors[:num_colors]


def calculate_contrast_ratio(
    color1: Tuple[int, int, int], color2: Tuple[int, int, int]
) -> float:
    """
    Calculate the contrast ratio between two colors according to WCAG 2.0.

    Args:
        color1: First RGB color tuple
        color2: Second RGB color tuple

    Returns:
        Contrast ratio between the two colors (1:1 to 21:1)
    """

    # Convert RGB to relative luminance
    def get_luminance(rgb):
        # Convert RGB to sRGB
        srgb = [c / 255 for c in rgb]
        # Convert sRGB to linear RGB
        rgb_linear = []
        for c in srgb:
            if c <= 0.03928:
                rgb_linear.append(c / 12.92)
            else:
                rgb_linear.append(((c + 0.055) / 1.055) ** 2.4)
        # Calculate luminance
        return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]

    # Get luminance for both colors
    l1 = get_luminance(color1)
    l2 = get_luminance(color2)

    # Calculate contrast ratio
    if l1 > l2:
        return (l1 + 0.05) / (l2 + 0.05)
    else:
        return (l2 + 0.05) / (l1 + 0.05)


def generate_color_palette(
    base_colors: List[Tuple[int, int, int]],
) -> Dict[str, Tuple[int, int, int]]:
    """
    Generate a color palette from base colors.

    Args:
        base_colors: List of base RGB color tuples

    Returns:
        Dictionary with color roles and RGB values
    """
    if not base_colors:
        # Default palette if no colors provided
        return {
            "background": (222, 215, 211),
            "divider": (180, 180, 180),
            "divider_border": (150, 150, 150),
            "text_bg": (240, 240, 240, 200),
            "title_text": (50, 50, 50),
            "subtitle_text": (80, 80, 80),
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

    # Create a lighter version for the text background (no transparency)
    text_bg_hsv = (h, s * 0.3, min(0.95, v + 0.2))
    text_bg_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(*text_bg_hsv))

    # Calculate relative luminance of the background color (using the formula for perceived brightness)
    # Formula: 0.299*R + 0.587*G + 0.114*B
    r, g, b = text_bg_rgb
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Determine if background is light or dark (threshold at 0.5)
    is_light_bg = luminance > 0.5

    # Choose contrasting colors based on background luminance
    # For dark backgrounds, use lighter text; for light backgrounds, use darker text
    if is_light_bg:
        # Dark text for light backgrounds - start with almost black
        title_text = (40, 40, 40)  # Almost black for title
        subtitle_text = (60, 60, 60)  # Dark gray for subtitle
    else:
        # Light text for dark backgrounds - start with almost white
        title_text = (250, 250, 250)  # Almost white for title
        subtitle_text = (230, 230, 230)  # Light gray for subtitle

    # Check contrast ratio and adjust if needed to ensure readability
    # WCAG AA standard requires a contrast ratio of at least 4.5:1 for normal text
    min_contrast = 4.5

    # Check and adjust title text contrast
    title_contrast = calculate_contrast_ratio(text_bg_rgb, title_text)
    if title_contrast < min_contrast:
        # Adjust title text to be darker or lighter based on background
        if is_light_bg:
            title_text = (
                0,
                0,
                0,
            )  # Pure black for maximum contrast on light background
        else:
            title_text = (
                255,
                255,
                255,
            )  # Pure white for maximum contrast on dark background

    # Check and adjust subtitle text contrast
    subtitle_contrast = calculate_contrast_ratio(text_bg_rgb, subtitle_text)
    if subtitle_contrast < min_contrast:
        # Adjust subtitle text to be darker or lighter based on background
        if is_light_bg:
            subtitle_text = (
                20,
                20,
                20,
            )  # Very dark gray for good contrast on light background
        else:
            subtitle_text = (
                240,
                240,
                240,
            )  # Very light gray for good contrast on dark background

    # Use a neutral background color
    background = (240, 240, 240) if v < 0.5 else (220, 220, 220)

    return {
        "background": background,
        "divider": divider_color,
        "divider_border": border_rgb,
        "text_bg": text_bg_rgb,
        "title_text": title_text,
        "subtitle_text": subtitle_text,
    }


def create_dynamic_overlay(
    width: int,
    height: int,
    palette: Dict[str, Tuple[int, int, int]],
    title: str,
    num_images: int = 12,
    texture_image: Optional[Image.Image] = None,
) -> Image.Image:
    """
    Create a dynamic overlay with colors from the palette.

    Args:
        width: Width of the overlay
        height: Height of the overlay
        palette: Color palette to use
        title: Title text to display
        num_images: Number of images in the pattern set

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

    # Load fonts and prepare text elements
    top_subtitle_font_size = (
        divider_height // 1.5
    )  # Larger size for top subtitle, but not too large
    bottom_subtitle_font_size = divider_height // 2  # Smaller size for bottom subtitle
    top_subtitle_font = get_font("DSMarkerFelt.ttf", size=top_subtitle_font_size)
    bottom_subtitle_font = get_font("DSMarkerFelt.ttf", size=bottom_subtitle_font_size)
    title_font_size = divider_height // 1.2
    title_font = get_font("Free Version Angelina.ttf", size=title_font_size)

    # Top subtitle
    subtitle_text = "Seamless & Commercial Use"
    subtitle_width, subtitle_height = draw.textbbox(
        (0, 0), subtitle_text, font=top_subtitle_font
    )[2:4]

    # Main title - adjust font size to fit
    max_title_width = width // 2 - 80  # Maximum width with some margin
    title_width, title_height = draw.textbbox((0, 0), title, font=title_font)[2:4]
    while title_width > max_title_width and title_font_size > 20:
        title_font_size -= 5
        title_font = get_font("Free Version Angelina.ttf", size=title_font_size)
        title_width, title_height = draw.textbbox((0, 0), title, font=title_font)[2:4]

    # Bottom subtitle
    bottom_subtitle_text = f"{num_images} tileable images  |  300 dpi  |  12x12in jpg"
    bottom_subtitle_width, bottom_subtitle_height = draw.textbbox(
        (0, 0), bottom_subtitle_text, font=bottom_subtitle_font
    )[2:4]

    # Calculate text dimensions and padding
    padding_x = 40  # Horizontal padding
    padding_y = 30  # Vertical padding
    vertical_spacing = 20  # Space between text elements

    # Calculate total text height with spacing
    total_text_height = (
        subtitle_height
        + vertical_spacing
        + title_height
        + vertical_spacing
        + bottom_subtitle_height
    )

    # Calculate text backdrop dimensions based on text content
    text_width = max(subtitle_width, title_width, bottom_subtitle_width) + (
        padding_x * 2
    )
    text_height = total_text_height + (padding_y * 2)
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2

    # Draw text backdrop with rounded corners and border
    border_thickness = max(2, divider_height // 20)  # Same as divider border thickness
    border_radius = 15

    # Create a separate image for the text backdrop with texture
    text_backdrop = Image.new("RGBA", (text_width, text_height), palette["text_bg"])

    # If we have a texture image, apply it as a distressed background
    if texture_image is not None:
        try:
            # Resize the texture to fit the text backdrop
            texture_resized = texture_image.resize(
                (text_width, text_height), get_resampling_filter()
            )

            # Convert to grayscale for better blending if it's not already
            if texture_resized.mode != "L":
                texture_grayscale = texture_resized.convert("L")
            else:
                texture_grayscale = texture_resized

            # Create a mask from the texture with varying opacity
            # Adjust contrast to enhance the distressed effect
            enhancer = ImageEnhance.Contrast(texture_grayscale)
            enhanced_texture = enhancer.enhance(1.5)  # Increase contrast

            # Convert the texture to RGBA with transparency
            texture_rgba = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))

            # Use the texture as an alpha mask with the text_bg color
            r, g, b = palette["text_bg"][:3]  # Get RGB from text_bg
            for y in range(text_height):
                for x in range(text_width):
                    # Get pixel value from enhanced texture (0-255)
                    pixel = enhanced_texture.getpixel((x, y))

                    # Create a semi-transparent pixel based on texture
                    # Darker areas of texture = more transparent
                    alpha = max(30, min(80, 255 - pixel))  # Limit transparency range

                    # Add subtle color variation based on texture
                    # Darker areas of texture get slightly darker color
                    color_variation = max(
                        0, min(20, (255 - pixel) // 12)
                    )  # Small variation
                    r_var = max(0, r - color_variation)
                    g_var = max(0, g - color_variation)
                    b_var = max(0, b - color_variation)

                    texture_rgba.putpixel((x, y), (r_var, g_var, b_var, alpha))

            # Composite the texture with the text backdrop
            text_backdrop = Image.alpha_composite(text_backdrop, texture_rgba)

            # Add a subtle grain effect
            try:
                import random

                # Create a smaller grain texture and then resize it for efficiency
                small_size = (text_width // 4, text_height // 4)
                grain_small = Image.new("RGBA", small_size, (0, 0, 0, 0))

                # Generate grain on the smaller image
                for y in range(small_size[1]):
                    for x in range(small_size[0]):
                        # Random noise with very low opacity
                        if random.random() < 0.4:  # Increase density for small image
                            noise = random.randint(-15, 15)
                            alpha = random.randint(
                                5, 20
                            )  # Slightly stronger for small image
                            grain_small.putpixel((x, y), (noise, noise, noise, alpha))

                # Resize the grain to full size with nearest neighbor for a gritty look
                grain_overlay = grain_small.resize(
                    (text_width, text_height), Image.NEAREST
                )

                # Apply the grain effect
                text_backdrop = Image.alpha_composite(text_backdrop, grain_overlay)
            except Exception as e:
                # If grain effect fails, just continue without it
                logger.debug(f"Skipping grain effect: {e}")
        except Exception as e:
            logger.warning(
                f"Error applying texture to text backdrop: {e}. Using solid color."
            )

    # Draw rounded corners on the text backdrop
    mask = Image.new("L", (text_width, text_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (text_width, text_height)], radius=border_radius, fill=255
    )

    # Apply the mask to get rounded corners
    text_backdrop.putalpha(mask)

    # Paste the text backdrop onto the overlay
    overlay.paste(text_backdrop, (text_x, text_y), text_backdrop)

    # Draw the border
    draw.rounded_rectangle(
        [(text_x, text_y), (text_x + text_width, text_y + text_height)],
        radius=border_radius,
        outline=palette["divider_border"],
        width=border_thickness,
    )

    # Add text
    # Position text elements
    subtitle_x = (width - subtitle_width) // 2
    # Move the top subtitle up to compensate for larger font size
    subtitle_offset_up = 15  # Pixels to move the subtitle up
    subtitle_y = text_y + padding_y - subtitle_offset_up

    # Move the title up by reducing the space between top subtitle and title
    title_offset_up = 20  # Pixels to move the title up
    title_x = (width - title_width) // 2
    title_y = subtitle_y + subtitle_height + vertical_spacing - title_offset_up

    # Keep the bottom subtitle position relative to the bottom of the rectangle
    # rather than relative to the title
    bottom_subtitle_x = (width - bottom_subtitle_width) // 2
    bottom_subtitle_y = text_y + text_height - padding_y - bottom_subtitle_height

    # Draw text elements
    draw.text(
        (subtitle_x, subtitle_y),
        subtitle_text,
        font=top_subtitle_font,
        fill=palette["subtitle_text"],
    )

    draw.text((title_x, title_y), title, font=title_font, fill=palette["title_text"])

    draw.text(
        (bottom_subtitle_x, bottom_subtitle_y),
        bottom_subtitle_text,
        font=bottom_subtitle_font,
        fill=palette["subtitle_text"],
    )

    return overlay


def create_main_mockup(input_folder: str, title: str) -> Optional[str]:
    """
    Creates the main 2x6 grid mockup with a dynamic overlay.

    Args:
        input_folder: Path to the input folder containing images
        title: Title to display on the mockup

    Returns:
        Path to the created main mockup file, or None if creation failed
    """
    logger.info(f"Creating dynamic main mockup for '{title}'...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)

    GRID_ROWS, GRID_COLS = 2, 6

    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        logger.warning(f"No images found in {input_folder} for main mockup.")
        return None

    grid_width = 3000
    grid_height = 2250

    # Extract colors from the images
    extracted_colors = extract_colors_from_images(images)
    color_palette = generate_color_palette(extracted_colors)

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
                shadow = shadow_img.resize(
                    (shadow_new_width, cell_height), get_resampling_filter()
                )
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

    # Select a texture image for the distressed effect
    texture_image = None
    if images:
        try:
            # Use the first image as texture
            texture_image_path = images[0]
            texture_image = Image.open(texture_image_path).convert("RGBA")
            logger.info(
                f"Using {os.path.basename(texture_image_path)} as texture for distressed effect"
            )
        except Exception as e:
            logger.warning(
                f"Error loading texture image: {e}. Will use solid color background."
            )

    # Create and add dynamic overlay
    try:
        dynamic_overlay = create_dynamic_overlay(
            grid_width, grid_height, color_palette, title, num_images, texture_image
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
