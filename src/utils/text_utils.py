"""
Shared text rendering utilities for pattern and clipart mockups.
"""

from typing import Tuple, Dict, Optional, List
from PIL import Image, ImageDraw, ImageFont

from utils.common import setup_logging, get_font

# Set up logging
logger = setup_logging(__name__)


def draw_text(
    draw: ImageDraw.Draw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    text_color: Tuple[int, int, int],
    shadow_offset: int = 0,
    shadow_color: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """
    Draw text with optional shadow for better readability.

    Args:
        draw: ImageDraw object to draw on
        position: (x, y) position for the text
        text: Text to draw
        font: Font to use
        text_color: RGB color for the text
        shadow_offset: Offset for shadow (0 for no shadow)
        shadow_color: RGBA color for shadow (default: semi-transparent black)
    """
    x, y = position
    
    # Draw shadow if requested
    if shadow_offset > 0:
        shadow_color = shadow_color or (0, 0, 0, 100)
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=shadow_color,
        )
    
    # Draw the main text
    draw.text(position, text, font=font, fill=text_color)


def calculate_text_dimensions(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> Tuple[int, int]:
    """
    Calculate the dimensions of text using the given font.
    Compatible with different Pillow versions.

    Args:
        draw: ImageDraw object
        text: Text to measure
        font: Font to use

    Returns:
        (width, height) of the text
    """
    try:
        # For newer Pillow versions
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height
    except AttributeError:
        # For older Pillow versions
        return draw.textsize(text, font=font)


def fit_text_to_width(
    draw: ImageDraw.Draw,
    text: str,
    font_name: str,
    max_width: int,
    max_font_size: int,
    min_font_size: int,
    step_size: int = 5,
) -> Tuple[ImageFont.FreeTypeFont, int, int]:
    """
    Find the largest font size that fits the text within the given width.

    Args:
        draw: ImageDraw object
        text: Text to fit
        font_name: Name of the font to use
        max_width: Maximum width for the text
        max_font_size: Maximum font size to try
        min_font_size: Minimum acceptable font size
        step_size: Size reduction step

    Returns:
        Tuple of (font, text_width, text_height)
    """
    font_size = max_font_size
    font = get_font(font_name, size=font_size)
    text_width, text_height = calculate_text_dimensions(draw, text, font)
    
    # Reduce font size until text fits or minimum size is reached
    while text_width > max_width and font_size > min_font_size:
        font_size -= step_size
        font = get_font(font_name, size=font_size)
        text_width, text_height = calculate_text_dimensions(draw, text, font)
    
    return font, text_width, text_height


def create_text_backdrop(
    width: int,
    height: int,
    background_color: Tuple[int, int, int, int],
    border_color: Optional[Tuple[int, int, int, int]] = None,
    border_thickness: int = 2,
    border_radius: int = 15,
    sample_image: Optional[Image.Image] = None,
    sample_opacity: int = 60,
) -> Image.Image:
    """
    Create a backdrop for text with optional border and sample image overlay.

    Args:
        width: Width of the backdrop
        height: Height of the backdrop
        background_color: RGBA background color
        border_color: RGBA border color (None for no border)
        border_thickness: Border thickness
        border_radius: Border corner radius
        sample_image: Optional image to use as a semi-transparent overlay
        sample_opacity: Opacity of the sample image (0-255)

    Returns:
        RGBA image with the backdrop
    """
    # Create a mask for rounded corners
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (width, height)], radius=border_radius, fill=255
    )

    # Create the solid backdrop with rounded corners
    solid_backdrop = Image.new("RGBA", (width, height), background_color)
    solid_backdrop.putalpha(mask)  # Apply rounded corners

    # Create the final text backdrop that will hold all layers
    text_backdrop = solid_backdrop.copy()

    # If we have a sample image, overlay it on the backdrop with transparency
    if sample_image is not None:
        try:
            # Resize the sample image to fill the text backdrop while preserving aspect ratio
            img_aspect = (
                sample_image.width / sample_image.height
                if sample_image.height > 0
                else 1
            )
            backdrop_aspect = width / height

            # Determine which dimension to match and which to overflow
            if img_aspect > backdrop_aspect:  # Image is wider than backdrop
                # Match height and let width overflow
                new_height = height
                new_width = int(height * img_aspect)
            else:  # Image is taller than backdrop or same aspect ratio
                # Match width and let height overflow
                new_width = width
                new_height = int(width / img_aspect)

            # Resize to the calculated dimensions
            from utils.common import get_resampling_filter
            sample_resized = sample_image.resize(
                (new_width, new_height), get_resampling_filter()
            )

            # Calculate position to center the image in the backdrop
            pos_x = (width - new_width) // 2
            pos_y = (height - new_height) // 2

            # Create a semi-transparent version of the sample image
            sample_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            sample_pixels = sample_overlay.load()
            resized_pixels = sample_resized.load()

            # Copy pixels with reduced alpha (semi-transparent)
            for target_y in range(height):
                for target_x in range(width):
                    # Calculate the corresponding position in the source image
                    source_x = target_x - pos_x
                    source_y = target_y - pos_y

                    # Check if the source coordinates are within the resized image
                    if (
                        0 <= source_x < sample_resized.width
                        and 0 <= source_y < sample_resized.height
                    ):
                        r, g, b, a = resized_pixels[source_x, source_y]
                        # Make the overlay semi-transparent
                        new_alpha = min(sample_opacity, a)
                        sample_pixels[target_x, target_y] = (r, g, b, new_alpha)

            # Apply the rounded corner mask to the sample overlay
            sample_alpha = sample_overlay.split()[3]
            masked_alpha = Image.new("L", (width, height), 0)
            masked_alpha.paste(sample_alpha, (0, 0), mask)
            r, g, b, _ = sample_overlay.split()
            sample_overlay = Image.merge("RGBA", (r, g, b, masked_alpha))

            # Composite the sample overlay onto the backdrop
            text_backdrop = Image.alpha_composite(text_backdrop, sample_overlay)

        except Exception as e:
            logger.warning(
                f"Error applying sample image overlay: {e}. Using solid backdrop."
            )

    # Draw border if requested
    if border_color is not None and border_thickness > 0:
        border_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=border_radius,
            outline=border_color,
            width=border_thickness,
        )
        text_backdrop = Image.alpha_composite(text_backdrop, border_img)

    return text_backdrop


def split_text_into_lines(
    text: str, 
    max_width: int, 
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.Draw,
    max_lines: int = 3
) -> List[str]:
    """
    Split text into lines that fit within the given width.

    Args:
        text: Text to split
        max_width: Maximum width for each line
        font: Font to use for measuring text
        draw: ImageDraw object for measuring text
        max_lines: Maximum number of lines

    Returns:
        List of text lines
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        # Try adding the word to the current line
        test_line = current_line + [word]
        test_text = " ".join(test_line)
        width, _ = calculate_text_dimensions(draw, test_text, font)
        
        if width <= max_width:
            # Word fits, add it to the current line
            current_line = test_line
        else:
            # Word doesn't fit, start a new line
            if current_line:  # Only add the line if it's not empty
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # If the word is too long for a line by itself, force it
                lines.append(word)
                current_line = []
                
        # Check if we've reached the maximum number of lines
        if len(lines) >= max_lines - 1 and current_line:
            # If we're at the last line, add any remaining words with ellipsis if needed
            remaining_words = [word] + words[words.index(word) + 1:]
            remaining_text = " ".join(remaining_words)
            
            # Check if the remaining text fits
            width, _ = calculate_text_dimensions(draw, remaining_text, font)
            if width > max_width:
                # Truncate with ellipsis
                ellipsis = "..."
                truncated = remaining_text
                while truncated and calculate_text_dimensions(draw, truncated + ellipsis, font)[0] > max_width:
                    truncated = truncated[:-1]
                lines.append(truncated + ellipsis)
            else:
                lines.append(remaining_text)
            break
    
    # Add the last line if there's anything left
    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))
        
    return lines
