"""
Shared image processing utilities for pattern and clipart mockups.
"""

from typing import List, Tuple, Optional
from PIL import Image, ImageDraw

from utils.common import setup_logging, get_resampling_filter

# Set up logging
logger = setup_logging(__name__)


def resize_image(
    image: Image.Image, target_width: int, target_height: int = None
) -> Image.Image:
    """
    Resize an image to the target width while maintaining aspect ratio.
    If target_height is provided, resize to fit within both dimensions.

    Args:
        image: PIL Image to resize
        target_width: Target width in pixels
        target_height: Optional target height in pixels

    Returns:
        Resized PIL Image
    """
    if target_height is None:
        # Calculate height to maintain aspect ratio
        aspect_ratio = image.width / image.height
        target_height = int(target_width / aspect_ratio)
    else:
        # Resize to fit within both dimensions while maintaining aspect ratio
        width_ratio = target_width / image.width
        height_ratio = target_height / image.height
        
        # Use the smaller ratio to ensure the image fits within both dimensions
        ratio = min(width_ratio, height_ratio)
        target_width = int(image.width * ratio)
        target_height = int(image.height * ratio)
    
    # Resize the image
    return image.resize((target_width, target_height), get_resampling_filter())


def create_grid(
    images: List[str],
    grid_width: int,
    grid_height: int,
    canvas_width: int,
    canvas_height: int,
    background_color: Tuple[int, int, int] = (255, 255, 255),
    padding: int = 10,
    border_width: int = 0,
    border_color: Tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """
    Create a grid of images.

    Args:
        images: List of image paths
        grid_width: Number of columns in the grid
        grid_height: Number of rows in the grid
        canvas_width: Width of the output canvas
        canvas_height: Height of the output canvas
        background_color: RGB background color
        padding: Padding between images
        border_width: Width of the border around each image
        border_color: RGB border color

    Returns:
        PIL Image with the grid
    """
    # Create a blank canvas
    canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
    
    # Calculate the size of each cell in the grid
    cell_width = (canvas_width - (padding * (grid_width + 1))) // grid_width
    cell_height = (canvas_height - (padding * (grid_height + 1))) // grid_height
    
    # Calculate the actual image size (accounting for border)
    image_width = cell_width - (border_width * 2)
    image_height = cell_height - (border_width * 2)
    
    # Limit the number of images to the grid size
    max_images = grid_width * grid_height
    images = images[:min(len(images), max_images)]
    
    # Place images in the grid
    for i, img_path in enumerate(images):
        try:
            # Calculate grid position
            row = i // grid_width
            col = i % grid_width
            
            # Calculate pixel position
            x = padding + col * (cell_width + padding) + border_width
            y = padding + row * (cell_height + padding) + border_width
            
            # Open and resize the image
            with Image.open(img_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Resize to fit the cell while maintaining aspect ratio
                img_aspect = img.width / img.height
                if img_aspect > 1:  # Landscape
                    new_width = image_width
                    new_height = int(image_width / img_aspect)
                else:  # Portrait or square
                    new_height = image_height
                    new_width = int(image_height * img_aspect)
                
                # Resize the image
                img_resized = img.resize((new_width, new_height), get_resampling_filter())
                
                # Calculate position to center the image in the cell
                img_x = x + (image_width - new_width) // 2
                img_y = y + (image_height - new_height) // 2
                
                # Draw border if requested
                if border_width > 0:
                    draw = ImageDraw.Draw(canvas)
                    border_x = img_x - border_width
                    border_y = img_y - border_width
                    border_width_end = img_x + new_width + border_width
                    border_height_end = img_y + new_height + border_width
                    draw.rectangle(
                        [(border_x, border_y), (border_width_end, border_height_end)],
                        outline=border_color,
                        width=border_width,
                    )
                
                # Paste the image onto the canvas
                canvas.paste(img_resized, (img_x, img_y))
        
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
    
    return canvas


def apply_shadow(
    image: Image.Image,
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 100),
    offset: Tuple[int, int] = (5, 5),
    blur_radius: int = 3,
) -> Image.Image:
    """
    Apply a drop shadow to an image.

    Args:
        image: PIL Image to apply shadow to
        shadow_color: RGBA shadow color
        offset: (x, y) offset for the shadow
        blur_radius: Blur radius for the shadow

    Returns:
        PIL Image with shadow
    """
    # Create a new image with space for the shadow
    width, height = image.size
    new_width = width + abs(offset[0]) + 2 * blur_radius
    new_height = height + abs(offset[1]) + 2 * blur_radius
    
    # Calculate the position of the original image
    img_x = blur_radius
    img_y = blur_radius
    if offset[0] < 0:
        img_x += abs(offset[0])
    if offset[1] < 0:
        img_y += abs(offset[1])
    
    # Calculate the position of the shadow
    shadow_x = img_x + offset[0]
    shadow_y = img_y + offset[1]
    
    # Create a new transparent image
    result = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    
    # Create the shadow
    shadow = Image.new("RGBA", image.size, shadow_color)
    
    # Apply blur to the shadow (if PIL supports it)
    try:
        from PIL import ImageFilter
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    except (ImportError, AttributeError):
        # Skip blur if not supported
        pass
    
    # Paste the shadow and then the image
    result.paste(shadow, (shadow_x, shadow_y), shadow)
    result.paste(image, (img_x, img_y), image)
    
    return result


def create_watermark(
    text: str,
    font_size: int = 30,
    opacity: int = 50,
    color: Tuple[int, int, int] = (0, 0, 0),
    angle: int = 45,
) -> Image.Image:
    """
    Create a watermark image with text.

    Args:
        text: Text for the watermark
        font_size: Font size for the text
        opacity: Opacity of the watermark (0-255)
        color: RGB color for the text
        angle: Rotation angle for the text

    Returns:
        PIL Image with the watermark
    """
    from PIL import ImageFont
    from utils.common import get_font
    
    # Create a transparent image
    watermark = Image.new("RGBA", (500, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    
    # Load font
    font = get_font("Arial", size=font_size)
    
    # Draw text
    draw.text((10, 10), text, font=font, fill=color + (opacity,))
    
    # Rotate if needed
    if angle != 0:
        watermark = watermark.rotate(angle, expand=True)
    
    return watermark


def apply_watermark(
    image: Image.Image, watermark: Image.Image, position: str = "center"
) -> Image.Image:
    """
    Apply a watermark to an image.

    Args:
        image: PIL Image to apply watermark to
        watermark: PIL Image with the watermark
        position: Position for the watermark (center, tile, bottom-right, etc.)

    Returns:
        PIL Image with watermark
    """
    # Convert image to RGBA if needed
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # Create a copy of the image
    result = image.copy()
    
    if position == "center":
        # Calculate position to center the watermark
        x = (image.width - watermark.width) // 2
        y = (image.height - watermark.height) // 2
        result.paste(watermark, (x, y), watermark)
    
    elif position == "tile":
        # Tile the watermark across the image
        for y in range(0, image.height, watermark.height):
            for x in range(0, image.width, watermark.width):
                result.paste(watermark, (x, y), watermark)
    
    elif position == "bottom-right":
        # Place in the bottom-right corner
        x = image.width - watermark.width - 10
        y = image.height - watermark.height - 10
        result.paste(watermark, (x, y), watermark)
    
    else:  # Default to center
        x = (image.width - watermark.width) // 2
        y = (image.height - watermark.height) // 2
        result.paste(watermark, (x, y), watermark)
    
    return result
