"""
Shared color utilities for pattern and clipart mockups.
"""

import colorsys
from typing import List, Tuple, Dict, Optional
from PIL import ImageStat, Image

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)


def extract_colors_from_images(
    images: List[str], num_colors: int = 5
) -> List[Tuple[int, int, int]]:
    """Extract dominant colors from a list of images.

    Args:
        images: List of image paths
        num_colors: Number of dominant colors to extract

    Returns:
        List of RGB color tuples
    """
    if not images:
        logger.warning("No images provided for color extraction")
        return [(222, 215, 211)]  # Default background color

    # Use more images for better color representation
    sample_images = images[: min(5, len(images))]
    all_colors = []

    for img_path in sample_images:
        try:
            with Image.open(img_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize for faster processing but keep enough detail for color extraction
                img.thumbnail((200, 200))

                # Get image statistics
                stat = ImageStat.Stat(img)
                avg_color = tuple(map(int, stat.mean))
                all_colors.append(avg_color)

                # Sample pixels from different regions
                width, height = img.size

                # Create a more detailed grid of regions
                regions = []
                grid_size = 4  # 4x4 grid
                for x in range(grid_size):
                    for y in range(grid_size):
                        x_start = int(width * x / grid_size)
                        y_start = int(height * y / grid_size)
                        x_end = int(width * (x + 1) / grid_size)
                        y_end = int(height * (y + 1) / grid_size)
                        regions.append((x_start, y_start, x_end, y_end))

                # Add some focused regions for potential accent colors
                regions.extend(
                    [
                        (width // 4, height // 4, 3 * width // 4, 3 * height // 4),  # Center
                        (0, 0, width // 3, height // 3),  # Top-left
                        (2 * width // 3, 0, width, height // 3),  # Top-right
                        (0, 2 * height // 3, width // 3, height),  # Bottom-left
                        (2 * width // 3, 2 * height // 3, width, height),  # Bottom-right
                    ]
                )

                for region in regions:
                    region_img = img.crop(region)
                    region_stat = ImageStat.Stat(region_img)
                    region_color = tuple(map(int, region_stat.mean))
                    all_colors.append(region_color)

                    # Also extract min and max colors from each region for more variety
                    min_vals = (
                        region_stat.extrema[0][0],
                        region_stat.extrema[1][0],
                        region_stat.extrema[2][0],
                    )
                    max_vals = (
                        region_stat.extrema[0][1],
                        region_stat.extrema[1][1],
                        region_stat.extrema[2][1],
                    )
                    all_colors.append(tuple(map(int, min_vals)))
                    all_colors.append(tuple(map(int, max_vals)))

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

        # Allow a wider range of colors, only skip extreme values
        if v < 0.1 or v > 0.98:
            continue

        # Allow more colors with lower saturation but prioritize vibrant ones
        if s < 0.03:  # Only skip very desaturated colors
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

            # If colors are too similar, skip this one (use tighter threshold)
            if h_diff < 0.08 and s_diff < 0.15 and v_diff < 0.15:
                is_unique = False
                break

        if is_unique:
            filtered_colors.append(color)

    # If filtering removed all colors, return the original average colors
    if not filtered_colors:
        filtered_colors = all_colors

    # Sort by saturation to prioritize more vibrant colors
    filtered_colors_with_hsv = []
    for color in filtered_colors:
        h, s, v = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)
        filtered_colors_with_hsv.append((color, s))

    filtered_colors_with_hsv.sort(key=lambda x: x[1], reverse=True)
    sorted_colors = [c[0] for c in filtered_colors_with_hsv]

    # Return the requested number of colors
    return sorted_colors[:num_colors]


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


def adjust_color_for_contrast(
    foreground: Tuple[int, int, int],
    background: Tuple[int, int, int],
    min_contrast: float = 5.5,
) -> Tuple[int, int, int]:
    """
    Adjust foreground color to ensure minimum contrast with background.

    Args:
        foreground: RGB foreground color to adjust
        background: RGB background color to contrast against
        min_contrast: Minimum contrast ratio required (WCAG AA: 4.5 for normal text)
                     We use 5.5 for better readability

    Returns:
        Adjusted RGB foreground color with sufficient contrast
    """
    # Check current contrast
    current_contrast = calculate_contrast_ratio(foreground, background)

    if current_contrast >= min_contrast:
        return foreground  # Already meets contrast requirements

    # Convert to HSV for easier manipulation
    r, g, b = foreground
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    # Get background luminance to determine if we should lighten or darken
    bg_r, bg_g, bg_b = background
    bg_luminance = (0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b) / 255
    is_light_bg = bg_luminance > 0.5

    # For very light backgrounds, we want darker and more saturated text
    # For very dark backgrounds, we want lighter and more saturated text
    if is_light_bg:
        # Start with a more saturated color for light backgrounds
        s = min(1.0, s * 1.3)  # Increase saturation by 30%

        # If the background is very light, make the text darker to start with
        if bg_luminance > 0.85:
            v = max(0.0, v * 0.7)  # Reduce brightness by 30%
    else:
        # For dark backgrounds, increase saturation to make text pop more
        s = min(1.0, s * 1.2)  # Increase saturation by 20%

        # If the background is very dark, make the text lighter to start with
        if bg_luminance < 0.15:
            v = min(1.0, v * 1.3)  # Increase brightness by 30%

    # Adjust value (brightness) in steps until we reach minimum contrast
    step = 0.05
    max_iterations = 25
    iterations = 0

    while current_contrast < min_contrast and iterations < max_iterations:
        iterations += 1

        if is_light_bg:
            # For light backgrounds, darken the text
            v = max(0.0, v - step)
        else:
            # For dark backgrounds, lighten the text
            v = min(1.0, v + step)

        # Convert back to RGB
        adjusted_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
        current_contrast = calculate_contrast_ratio(adjusted_rgb, background)

        # If we've reached extreme values and still don't have enough contrast,
        # try adjusting saturation as well
        if (is_light_bg and v <= 0.1) or (not is_light_bg and v >= 0.9):
            # For both light and dark backgrounds, increase saturation for more pop
            s = min(1.0, s + step)
            adjusted_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
            current_contrast = calculate_contrast_ratio(adjusted_rgb, background)

    # If we still don't have enough contrast, use black or white with a hint of color
    if current_contrast < min_contrast:
        if is_light_bg:
            # Black text with a hint of the original hue for light backgrounds
            v = 0.05  # Very dark
            s = 0.8  # High saturation to maintain some color
            adjusted_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))

            # If still not enough contrast, use pure black
            if calculate_contrast_ratio(adjusted_rgb, background) < min_contrast:
                adjusted_rgb = (0, 0, 0)
        else:
            # White text with a hint of the original hue for dark backgrounds
            v = 0.95  # Very light
            s = 0.3  # Some saturation to maintain some color
            adjusted_rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))

            # If still not enough contrast, use pure white
            if calculate_contrast_ratio(adjusted_rgb, background) < min_contrast:
                adjusted_rgb = (255, 255, 255)

    return adjusted_rgb
