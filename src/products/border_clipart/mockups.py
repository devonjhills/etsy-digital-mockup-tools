"""Border clipart mockup generation."""

import os
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import random
from src.utils.color_utils import extract_colors_from_images
from src.utils.text_utils import draw_text, calculate_text_dimensions, create_text_backdrop
from src.utils.common import get_font
import colorsys


def _generate_border_color_palette(base_colors):
    """Generate a color palette for border clipart text overlays."""
    # Use a fixed dark backdrop color with even more transparency
    text_bg_rgb = (40, 40, 40)
    text_bg_with_alpha = text_bg_rgb + (120,)  # Even more transparent backdrop (was 160, now 120)
    
    # Always use white text on dark background for border clipart
    title_text = (255, 255, 255)
    subtitle_text = (255, 255, 255)
    
    # Get a nice border color from the extracted colors
    if base_colors:
        # Get the most saturated color for the border
        colors_with_hsv = []
        for color in base_colors:
            h, s, v = colorsys.rgb_to_hsv(color[0] / 255, color[1] / 255, color[2] / 255)
            colors_with_hsv.append((color, h, s, v))
        
        colors_with_hsv.sort(key=lambda x: x[2], reverse=True)  # Sort by saturation
        divider_border = colors_with_hsv[0][0] if colors_with_hsv else (150, 150, 150)
    else:
        divider_border = (150, 150, 150)
    
    return {
        "text_bg": text_bg_with_alpha,
        "title_text": title_text,
        "subtitle_text": subtitle_text,
        "divider_border": divider_border
    }


def create_horizontal_seamless_mockup(
    input_image_paths: List[str],
    title: str,
    subtitle_top: str = "Seamless Borders Cliparts",
    subtitle_bottom: str = "transparent png  |  300 dpi  |  commercial use",
    canvas_size: Tuple[int, int] = (3000, 2250),
    rows: int = 4
) -> Image.Image:
    """
    Create a horizontal seamless border mockup showing borders repeating horizontally.
    
    Args:
        input_image_paths: List of border image file paths
        title: Main title text
        subtitle_top: Top subtitle text
        subtitle_bottom: Bottom subtitle text  
        canvas_size: Canvas dimensions (width, height)
        rows: Number of rows to display
        
    Returns:
        PIL Image of the mockup
    """
    
    # Create white canvas
    canvas = Image.new("RGB", canvas_size, "white")
    draw = ImageDraw.Draw(canvas)
    
    canvas_width, canvas_height = canvas_size
    
    # Define layout zones (optimized for 4 rows)
    title_zone_height = 150  # Further reduced to maximize border space
    bottom_padding = 30  # Minimal bottom padding
    border_zone_height = canvas_height - title_zone_height - bottom_padding  # Maximum space for borders
    row_height = border_zone_height // rows
    
    # Load and prepare border images
    border_images = []
    for img_path in input_image_paths[:rows]:  # Use only as many as we have rows
        try:
            img = Image.open(img_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            border_images.append(img)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            continue
    
    if not border_images:
        # Create placeholder if no images loaded
        placeholder = Image.new("RGBA", (200, 100), (200, 200, 200, 255))
        border_images = [placeholder] * rows
    
    # If we have fewer images than rows, cycle through them
    while len(border_images) < rows:
        border_images.extend(border_images[:rows - len(border_images)])
    
    # Draw borders in horizontal seamless rows
    start_y = title_zone_height  # Start immediately after title space
    
    for row_idx in range(rows):
        border_img = border_images[row_idx]
        
        # Calculate optimal height for this border (make images bigger)
        max_border_height = int(row_height * 0.95)  # Use 95% of row height for bigger images (was 80%)
        original_width, original_height = border_img.size
        
        # Scale to fit height while maintaining aspect ratio
        scale_factor = min(max_border_height / original_height, 1.0)  # Don't upscale
        new_height = int(original_height * scale_factor)
        new_width = int(original_width * scale_factor)
        
        # Resize the border
        resized_border = border_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Calculate how many times we need to tile horizontally to fill the canvas
        tiles_needed = (canvas_width // new_width) + 2  # Extra tiles to ensure full coverage
        
        # Create row position - evenly distribute rows in the available space
        row_y = start_y + (row_idx * row_height) + (row_height - new_height) // 2
        
        # Tile the border horizontally across the canvas
        for tile_idx in range(tiles_needed):
            tile_x = tile_idx * new_width - (new_width // 4)  # Slight overlap to ensure seamless
            
            if tile_x < canvas_width:  # Only draw if within canvas bounds
                # Create a temporary image for compositing with transparency
                temp_canvas = Image.new("RGBA", canvas_size, (255, 255, 255, 0))
                temp_canvas.paste(resized_border, (tile_x, row_y), resized_border)
                
                # Composite onto main canvas
                canvas = Image.alpha_composite(
                    canvas.convert("RGBA"), 
                    temp_canvas
                ).convert("RGB")
    
    # Add text overlays using the same system as patterns
    draw = ImageDraw.Draw(canvas)
    
    # Extract colors from border images for dynamic color palette
    try:
        extracted_colors = extract_colors_from_images(input_image_paths)
        color_palette = _generate_border_color_palette(extracted_colors)
    except Exception as e:
        print(f"Error extracting colors: {e}")
        # Fallback to default colors
        color_palette = {
            "text_bg": (40, 40, 40, 220),
            "title_text": (255, 255, 255),
            "subtitle_text": (255, 255, 255),
            "divider_border": (150, 150, 150)
        }
    
    # Load fonts with proper configuration (increased subtitle sizes)
    try:
        title_font = get_font("GreatVibes-Regular", size=150)
        subtitle_font = get_font("LibreBaskerville-Italic", size=60)  # Increased from 48
    except:
        title_font = get_font("Arial", size=90)
        subtitle_font = get_font("Arial", size=60)  # Increased from 48
    
    # Calculate text dimensions
    title_width, title_height = calculate_text_dimensions(draw, title, title_font)
    subtitle_top_width, subtitle_top_height = calculate_text_dimensions(draw, subtitle_top, subtitle_font)
    subtitle_bottom_width, subtitle_bottom_height = calculate_text_dimensions(draw, subtitle_bottom, subtitle_font)
    
    # Calculate text backdrop dimensions (reduced horizontal padding)
    padding_x = 25  # Reduced from 50
    padding_y = 45
    text_width = max(title_width, subtitle_top_width, subtitle_bottom_width) + (padding_x * 2)
    text_height = subtitle_top_height + title_height + subtitle_bottom_height + (padding_y * 3)
    
    # Load a sample image for the backdrop
    sample_image = None
    if input_image_paths:
        try:
            # Use the first image as a sample for the backdrop
            sample_image_path = input_image_paths[0]
            sample_image = Image.open(sample_image_path).convert("RGBA")
            print(f"Using {sample_image_path} as backdrop sample image")
        except Exception as e:
            print(f"Error loading sample image: {e}. Using solid color background.")
    
    # Create text backdrop with sample image (reduced extra padding)
    backdrop_width = text_width + 20  # Reduced from 40
    backdrop_height = text_height + 40
    text_backdrop = create_text_backdrop(
        width=backdrop_width,
        height=backdrop_height,
        background_color=color_palette["text_bg"],
        border_color=color_palette["divider_border"],
        border_thickness=3,
        border_radius=15,
        sample_image=sample_image,
        sample_opacity=40  # Lower opacity for subtle image overlay
    )
    
    # Position and paste backdrop
    backdrop_x = (canvas_width - backdrop_width) // 2
    backdrop_y = (canvas_height - backdrop_height) // 2
    canvas = canvas.convert("RGBA")
    canvas.paste(text_backdrop, (backdrop_x, backdrop_y), text_backdrop)
    
    # Create new draw object after conversion
    draw = ImageDraw.Draw(canvas)
    
    # Draw text elements
    # Top subtitle
    subtitle_top_x = (canvas_width - subtitle_top_width) // 2
    subtitle_top_y = backdrop_y + 30
    draw_text(draw, (subtitle_top_x, subtitle_top_y), subtitle_top, subtitle_font, color_palette["subtitle_text"])
    
    # Title (centered)
    title_x = (canvas_width - title_width) // 2
    title_y = backdrop_y + (backdrop_height - title_height) // 2
    draw_text(draw, (title_x, title_y), title, title_font, color_palette["title_text"])
    
    # Bottom subtitle
    subtitle_bottom_x = (canvas_width - subtitle_bottom_width) // 2
    subtitle_bottom_y = backdrop_y + backdrop_height - subtitle_bottom_height - 30
    draw_text(draw, (subtitle_bottom_x, subtitle_bottom_y), subtitle_bottom, subtitle_font, color_palette["subtitle_text"])
    
    # Convert back to RGB for final output
    canvas = canvas.convert("RGB")
    
    return canvas


def create_border_horizontal_rows(
    input_image_paths: List[str],
    grid_size: Tuple[int, int] = (2000, 2000),
    max_rows: int = 3,
    padding: int = 20
) -> Image.Image:
    """
    Create rows showcasing border pieces with horizontal tiling - each row shows one border tiled horizontally.
    
    Args:
        input_image_paths: List of border image file paths
        grid_size: Output grid dimensions
        max_rows: Maximum number of rows to create
        padding: Padding between rows
        
    Returns:
        PIL Image with horizontal rows
    """
    
    # Create white canvas
    canvas = Image.new("RGB", grid_size, "white")
    
    grid_width, grid_height = grid_size
    
    # Determine how many images to use (one per row)
    num_rows = min(len(input_image_paths), max_rows)
    if num_rows == 0:
        return canvas
    
    # Calculate row dimensions
    total_padding = padding * (num_rows + 1)
    row_height = (grid_height - total_padding) // num_rows
    
    for row_idx in range(num_rows):
        try:
            img_path = input_image_paths[row_idx]
            
            # Load border image
            img = Image.open(img_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # Scale border to fit row height while maintaining aspect ratio
            original_width, original_height = img.size
            scale_factor = min(row_height / original_height, 1.0)  # Don't upscale
            new_height = int(original_height * scale_factor)
            new_width = int(original_width * scale_factor)
            
            # Resize the border
            resized_border = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Calculate row position
            row_y = padding + row_idx * (row_height + padding)
            
            # Create row canvas
            row_canvas = Image.new("RGBA", (grid_width, row_height), (255, 255, 255, 0))
            
            # Calculate how many times we need to tile horizontally to fill the row
            tiles_needed = (grid_width // new_width) + 2  # Extra tiles to ensure full coverage
            
            # Center the tiled border vertically in the row
            tile_y = (row_height - new_height) // 2
            
            # Tile the border horizontally across the row
            for tile_idx in range(tiles_needed):
                tile_x = tile_idx * new_width - (new_width // 4)  # Slight overlap for seamless effect
                
                if tile_x < grid_width:  # Only draw if within row bounds
                    row_canvas.paste(resized_border, (tile_x, tile_y), resized_border)
            
            # Crop row canvas to exact row size
            row_canvas = row_canvas.crop((0, 0, grid_width, row_height))
            
            # Create temp canvas for compositing
            temp_canvas = Image.new("RGBA", grid_size, (255, 255, 255, 0))
            temp_canvas.paste(row_canvas, (0, row_y), row_canvas)
            
            # Composite onto main canvas
            canvas = Image.alpha_composite(
                canvas.convert("RGBA"), 
                temp_canvas
            ).convert("RGB")
            
        except Exception as e:
            print(f"Error processing image {img_path}: {e}")
            continue
    
    return canvas