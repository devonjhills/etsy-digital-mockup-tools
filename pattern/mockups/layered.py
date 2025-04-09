"""
Module for creating layered mockups.
"""
import os
import glob
from typing import Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from utils.common import (
    setup_logging, 
    get_resampling_filter, 
    ensure_dir_exists
)

# Set up logging
logger = setup_logging(__name__)

def create_large_grid(input_folder: str) -> List[str]:
    """
    Creates layered/rotated mockups.
    
    Args:
        input_folder: Path to the input folder containing images
        
    Returns:
        List of paths to the created layered mockup files
    """
    logger.info("Creating layered composite outputs...")
    output_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(output_folder)
    
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))
    
    num_images = len(images)
    if num_images < 3:
        logger.warning(f"Skipping layered composite: At least 3 JPG images required, found {num_images}.")
        return []
    
    # Settings
    CANVAS_WIDTH = 2800
    CANVAS_HEIGHT = 2250
    center_target_size = (2400, 2400)
    bottom_left_target_size = (1800, 1800)
    center_rotation = -25
    bottom_left_rotation = -15
    shadow_offset = 25
    shadow_blur = 15
    shadow_opacity = 120
    
    # Determine number of sets (up to 4)
    max_sets = min(4, num_images // 3)
    logger.info(f"Generating {max_sets} layered set(s)...")
    
    output_files = []
    
    for set_index in range(max_sets):
        logger.info(f"Processing set {set_index + 1}...")
        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
        
        # Backdrop Image
        backdrop_img_index = set_index * 3
        try:
            backdrop_img = Image.open(images[backdrop_img_index]).convert("RGB")
            
            # Fit backdrop to canvas
            backdrop_img_resized = ImageOps.fit(
                backdrop_img,
                (CANVAS_WIDTH, CANVAS_HEIGHT),
                method=get_resampling_filter(),
            )
            
            offset_x = (CANVAS_WIDTH - backdrop_img_resized.width) // 2
            offset_y = (CANVAS_HEIGHT - backdrop_img_resized.height) // 2
            canvas.paste(backdrop_img_resized, (offset_x, offset_y))
            
        except Exception as e:
            logger.error(f"Error processing backdrop image {images[backdrop_img_index]}: {e}")
            continue
        
        # Center Image
        center_img_index = set_index * 3 + 1
        if center_img_index < num_images:
            try:
                center_img = Image.open(images[center_img_index]).convert("RGBA")
                center_img = ImageOps.fit(
                    center_img, center_target_size, method=get_resampling_filter()
                )
                center_img_rotated = center_img.rotate(
                    center_rotation, expand=True, resample=Image.BICUBIC
                )
                
                # Calculate position
                center_offset_x_base = (CANVAS_WIDTH - center_target_size[0]) // 2 - 800
                center_offset_y_base = (CANVAS_HEIGHT - center_target_size[1]) // 2 + 100
                
                center_offset_x = (
                    center_offset_x_base
                    - (center_img_rotated.width - center_target_size[0]) // 2
                )
                center_offset_y = (
                    center_offset_y_base
                    - (center_img_rotated.height - center_target_size[1]) // 2
                )
                
                # Create and apply shadows
                center_shadow = Image.new("RGBA", center_img_rotated.size, (0, 0, 0, 0))
                try:
                    center_alpha = center_img_rotated.split()[3]
                    center_shadow.paste((0, 0, 0, shadow_opacity), mask=center_alpha)
                    center_shadow_blurred = center_shadow.filter(
                        ImageFilter.GaussianBlur(shadow_blur)
                    )
                    
                    # Shadow 1 (top-right offset)
                    canvas.paste(
                        center_shadow_blurred,
                        (
                            center_offset_x + shadow_offset,
                            center_offset_y + shadow_offset,
                        ),
                        center_shadow_blurred,
                    )
                    
                    # Shadow 2 (top-left offset)
                    canvas.paste(
                        center_shadow_blurred,
                        (
                            center_offset_x - shadow_offset,
                            center_offset_y - shadow_offset,
                        ),
                        center_shadow_blurred,
                    )
                    
                except Exception as e:
                    logger.warning(f"Error creating/pasting center shadow: {e}")
                
                # Paste center image
                canvas.paste(
                    center_img_rotated,
                    (center_offset_x, center_offset_y),
                    center_img_rotated,
                )
                
            except Exception as e:
                logger.error(f"Error processing center image {images[center_img_index]}: {e}")
        
        # Bottom-Left Image
        bottom_left_img_index = set_index * 3 + 2
        if bottom_left_img_index < num_images:
            try:
                bottom_left_img = Image.open(images[bottom_left_img_index]).convert("RGBA")
                bottom_left_img = ImageOps.fit(
                    bottom_left_img,
                    bottom_left_target_size,
                    method=get_resampling_filter(),
                )
                bottom_left_img_rotated = bottom_left_img.rotate(
                    bottom_left_rotation, expand=True, resample=Image.BICUBIC
                )
                
                # Calculate position
                bottom_left_offset_x_base = -400
                bottom_left_offset_y_base = (CANVAS_HEIGHT - bottom_left_target_size[1] + 300)
                
                bottom_left_offset_x = (
                    bottom_left_offset_x_base
                    - (bottom_left_img_rotated.width - bottom_left_target_size[0]) // 2
                )
                bottom_left_offset_y = (
                    bottom_left_offset_y_base
                    - (bottom_left_img_rotated.height - bottom_left_target_size[1]) // 2
                )
                
                # Create and apply shadows
                bottom_left_shadow = Image.new("RGBA", bottom_left_img_rotated.size, (0, 0, 0, 0))
                try:
                    bottom_left_alpha = bottom_left_img_rotated.split()[3]
                    bottom_left_shadow.paste((0, 0, 0, shadow_opacity), mask=bottom_left_alpha)
                    bottom_left_shadow_blurred = bottom_left_shadow.filter(
                        ImageFilter.GaussianBlur(shadow_blur)
                    )
                    
                    # Shadow 1 (bottom-right offset)
                    canvas.paste(
                        bottom_left_shadow_blurred,
                        (
                            bottom_left_offset_x + shadow_offset,
                            bottom_left_offset_y + shadow_offset,
                        ),
                        bottom_left_shadow_blurred,
                    )
                    
                    # Shadow 2 (top-left offset)
                    canvas.paste(
                        bottom_left_shadow_blurred,
                        (
                            bottom_left_offset_x - shadow_offset,
                            bottom_left_offset_y - shadow_offset,
                        ),
                        bottom_left_shadow_blurred,
                    )
                    
                except Exception as e:
                    logger.warning(f"Error creating/pasting bottom-left shadow: {e}")
                
                # Paste bottom-left image
                canvas.paste(
                    bottom_left_img_rotated,
                    (bottom_left_offset_x, bottom_left_offset_y),
                    bottom_left_img_rotated,
                )
                
            except Exception as e:
                logger.error(f"Error processing bottom-left image {images[bottom_left_img_index]}: {e}")
        
        # Save the result
        try:
            output_filename = f"layered_mockup_{set_index + 1}.jpg"
            save_path = os.path.join(output_folder, output_filename)
            canvas.save(save_path, "JPEG", quality=95, optimize=True)
            logger.info(f"Layered mockup saved: {save_path}")
            output_files.append(save_path)
        except Exception as e:
            logger.error(f"Error saving layered mockup {set_index + 1}: {e}")
    
    return output_files
