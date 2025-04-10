"""
Module for resizing pattern images.
"""

import os
import re
from typing import Tuple
from PIL import Image

from utils.common import setup_logging, get_resampling_filter

# Set up logging
logger = setup_logging(__name__)


def process_images(
    input_folder: str,
    max_size: Tuple[int, int] = (3600, 3600),
    dpi: Tuple[int, int] = (300, 300),
) -> None:
    """
    Resizes images to fit within max dimensions while maintaining aspect ratio.

    Args:
        input_folder: Path to the input folder containing subfolders with images
        max_size: Maximum image size (width, height) in pixels
        dpi: Desired DPI for the images
    """
    # Ensure the input folder exists
    if not os.path.isdir(input_folder):
        logger.error(f"Input folder not found at '{input_folder}'")
        return

    logger.info(f"Processing images in: {input_folder}")

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        # Skip if not a directory or if it's a special directory
        if not os.path.isdir(subfolder_path) or subfolder in ["mocks", "zipped"]:
            continue

        logger.info(f"  Processing subfolder: {subfolder}")
        
        # Create a safe subfolder name for renaming files
        safe_subfolder_name = re.sub(r"[^a-zA-Z0-9_]", "_", subfolder).lower()
        logger.info(f"  Using safe subfolder name: {safe_subfolder_name}")

        # Get all image files in the subfolder
        image_files = []
        for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            image_files.extend(
                [
                    os.path.join(subfolder_path, f)
                    for f in os.listdir(subfolder_path)
                    if f.lower().endswith(ext)
                ]
            )

        if not image_files:
            logger.warning(f"  No image files found in {subfolder_path}")
            continue

        logger.info(f"  Found {len(image_files)} image(s)")

        # Check which files are already correctly named and sized
        correct_files = []
        files_to_process = []
        
        for image_file in image_files:
            filename = os.path.basename(image_file)
            
            # Check if the file is already correctly named and sized
            is_correct = False
            if re.match(f"^{re.escape(safe_subfolder_name)}_\\d+\\.jpe?g$", filename.lower()):
                try:
                    with Image.open(image_file) as img:
                        width, height = img.size
                        if width <= max_size[0] and height <= max_size[1]:
                            is_correct = True
                except Exception:
                    pass
            
            if is_correct:
                correct_files.append(image_file)
            else:
                files_to_process.append(image_file)
        
        # Skip if all files are already correct
        if not files_to_process:
            logger.info(f"  All files in {subfolder} are already correctly named and sized")
            continue
            
        logger.info(f"  Processing {len(files_to_process)} files that need work")
        
        # Get the existing numbers from correctly named files
        existing_numbers = set()
        for file_path in correct_files:
            filename = os.path.basename(file_path)
            match = re.search(f"{re.escape(safe_subfolder_name)}_([0-9]+)", filename.lower())
            if match:
                existing_numbers.add(int(match.group(1)))
        
        # Find the next available number starting from 1
        next_number = 1
        while next_number in existing_numbers:
            next_number += 1
        
        # Process each file that needs work
        for i, image_file in enumerate(sorted(files_to_process), start=1):
            try:
                with Image.open(image_file) as img:
                    # Get original dimensions
                    original_width, original_height = img.size
                    original_filename = os.path.basename(image_file)
                    
                    # Determine if resizing is needed
                    needs_resize = original_width > max_size[0] or original_height > max_size[1]
                    
                    # Assign a number to this file
                    file_number = next_number
                    next_number += 1
                    
                    # Create new filename
                    new_filename = f"{safe_subfolder_name}_{file_number}.jpg"
                    new_file_path = os.path.join(os.path.dirname(image_file), new_filename)
                    
                    # Log what we're doing
                    logger.info(f"    Processing: {original_filename} -> {new_filename}")
                    
                    # Resize if needed
                    if needs_resize:
                        # Calculate new dimensions
                        width_ratio = max_size[0] / original_width
                        height_ratio = max_size[1] / original_height
                        ratio = min(width_ratio, height_ratio)
                        
                        new_width = int(original_width * ratio)
                        new_height = int(original_height * ratio)
                        
                        # Resize the image
                        img_to_save = img.resize((new_width, new_height), get_resampling_filter())
                        
                        # Set DPI
                        if hasattr(img_to_save, "info"):
                            img_to_save.info["dpi"] = dpi
                            
                        logger.info(f"    Resized: {original_width}x{original_height} -> {new_width}x{new_height}")
                    else:
                        img_to_save = img
                    
                    # Save the image
                    img_to_save.save(
                        new_file_path,
                        format="JPEG",
                        dpi=dpi,
                        quality=85,
                        optimize=True,
                    )
                    
                    # Delete the original file if it's different from the new file
                    if image_file != new_file_path:
                        try:
                            os.remove(image_file)
                            logger.info(f"    Deleted original: {original_filename}")
                        except Exception as e:
                            logger.error(f"    Error deleting {image_file}: {e}")
                
            except Exception as e:
                logger.error(f"    Error processing {image_file}: {e}")
    
    logger.info("Image processing complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resize pattern images")
    parser.add_argument(
        "--input_folder", required=True, help="Path to the input folder containing subfolders with images"
    )
    parser.add_argument(
        "--max_width", type=int, default=3600, help="Maximum width for the resized images"
    )
    parser.add_argument(
        "--max_height", type=int, default=3600, help="Maximum height for the resized images"
    )
    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI value to set for the resized images"
    )
    args = parser.parse_args()

    process_images(
        args.input_folder,
        max_size=(args.max_width, args.max_height),
        dpi=(args.dpi, args.dpi),
    )
