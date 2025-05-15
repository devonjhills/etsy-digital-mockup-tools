"""
Module for resizing clipart images.
"""

import os
import sys
import re
import logging
import shutil
from typing import List, Dict, Tuple, Optional, Any
from PIL import Image

from utils.common import setup_logging, get_resampling_filter, ensure_dir_exists

# Set up logging
logger = setup_logging(__name__)


def trim(im: Image.Image) -> Image.Image:
    """
    Remove empty space around an image with transparency.

    Args:
        im: The image to trim

    Returns:
        The trimmed image
    """
    try:
        im = im.convert("RGBA")
        bbox = im.getbbox()
        if bbox:
            return im.crop(bbox)
        logger.warning(
            "Trim: Image appears to be empty or fully transparent, returning original."
        )
        return im
    except Exception as e:
        logger.error(f"Error during trim: {e}")
        return im


def try_remove(file_path: str) -> bool:
    """
    Attempt to remove a file, handling exceptions.

    Args:
        file_path: Path to the file to remove

    Returns:
        True if the file was removed successfully, False otherwise
    """
    try:
        os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")
        return False


def extract_number_from_filename(filename: str) -> int:
    """
    Extract a number from a filename, handling various formats.

    Args:
        filename: The filename to extract a number from

    Returns:
        The extracted number, or 999999 if no number is found
    """
    # Try to extract a number from the filename
    # First, try the pattern "name_N.ext" or "name (N).ext"
    match = re.search(r"[_\s(]+(\d+)[)\s.]*", filename)
    if match:
        return int(match.group(1))

    # If no match, try to find any number in the filename
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))

    # If no number found, return a high value to sort it at the end
    return 999999


def process_images(input_folder_path: str, max_size: int) -> Tuple[int, int, int, int]:
    """
    Process images within subfolders of input_folder_path.
    Converts to PNG, trims, resizes if needed, sets DPI, and renames files
    to 'safesubfoldername_sequentialindex.png' based on NUMERICAL order
    extracted from original filenames.

    Args:
        input_folder_path: Absolute path to the input folder containing subfolders
        max_size: Maximum size for the longest edge while maintaining aspect ratio

    Returns:
        Tuple of (total_processed_count, total_skipped_folders, total_error_count, total_deleted_original_count)
    """
    logger.info(f"Starting image processing in: {input_folder_path}")
    if not os.path.isdir(input_folder_path):
        logger.error(f"Input folder not found or not a directory: {input_folder_path}")
        sys.exit(f"Error: Input folder '{input_folder_path}' not found.")

    total_processed_count = 0
    total_skipped_folders = 0
    total_error_count = 0
    total_deleted_original_count = 0

    subfolders = [
        d
        for d in os.listdir(input_folder_path)
        if os.path.isdir(os.path.join(input_folder_path, d))
    ]

    if not subfolders:
        logger.warning(f"No subfolders found in {input_folder_path}")
        return 0, 0, 0, 0

    logger.info(f"Found {len(subfolders)} subfolder(s) to process")

    for subfolder in sorted(subfolders):
        subfolder_path = os.path.join(input_folder_path, subfolder)

        # Skip special folders
        if subfolder in ["mocks", "zipped"]:
            logger.info(f"Skipping special folder: {subfolder}")
            continue

        logger.info(f"Processing subfolder: {subfolder}")

        # Get all image files in the subfolder
        image_files = []
        for ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"]:
            image_files.extend(
                [
                    os.path.join(subfolder_path, f)
                    for f in os.listdir(subfolder_path)
                    if f.lower().endswith(ext)
                    and os.path.isfile(os.path.join(subfolder_path, f))
                ]
            )

        if not image_files:
            logger.warning(f"No image files found in {subfolder_path}")
            continue

        # Sort files by the number in their filename
        image_files.sort(
            key=lambda x: extract_number_from_filename(os.path.basename(x))
        )

        # Process each image
        files_processed_this_folder = 0
        errors_this_folder = 0
        files_deleted_this_folder = 0

        for i, original_path in enumerate(image_files, start=1):
            original_filename = os.path.basename(original_path)

            # Create target filename
            safe_subfolder_name = re.sub(r"[^a-zA-Z0-9_]", "_", subfolder)
            target_name = f"{safe_subfolder_name}_{i}.png"
            target_path = os.path.join(subfolder_path, target_name)

            logger.info(f"Processing {original_filename} -> {target_name}")

            try:
                with Image.open(original_path) as img:
                    img = img.convert("RGBA")
                    img_trimmed = trim(img)
                    img = img_trimmed  # Keep the trimmed version

                    if img is None or img.size == (0, 0):
                        logger.warning(
                            f"Skipping '{original_filename}' due to invalid size after trim."
                        )
                        errors_this_folder += 1
                        continue

                    width, height = img.size
                    needs_resize = width > max_size or height > max_size

                    if needs_resize:
                        if width > height:
                            new_width = max_size
                            new_height = int(height * (max_size / width))
                        else:
                            new_height = max_size
                            new_width = int(width * (max_size / height))

                        logger.info(
                            f"Resizing from {width}x{height} to {new_width}x{new_height}"
                        )
                        img = img.resize(
                            (new_width, new_height), get_resampling_filter()
                        )

                    img.info["dpi"] = (300, 300)

                    # Save the processed image
                    ensure_dir_exists(os.path.dirname(target_path))
                    img.save(target_path, format="PNG", dpi=(300, 300))

                    # Remove the original file if it's different from the target
                    if os.path.abspath(target_path) != os.path.abspath(original_path):
                        if try_remove(original_path):
                            files_deleted_this_folder += 1
                        else:
                            logger.warning(
                                f"Failed to remove original file: {original_path}"
                            )

                    files_processed_this_folder += 1

            except Exception as e:
                logger.error(f"Error processing {original_path}: {e}")
                errors_this_folder += 1

        # Update totals
        total_processed_count += files_processed_this_folder
        total_error_count += errors_this_folder
        total_deleted_original_count += files_deleted_this_folder

        logger.info(
            f"Subfolder {subfolder} summary: "
            f"Processed {files_processed_this_folder}, "
            f"Errors {errors_this_folder}, "
            f"Originals deleted {files_deleted_this_folder}"
        )

    # Log overall summary
    logger.info(
        f"Overall summary: "
        f"Processed {total_processed_count}, "
        f"Skipped folders {total_skipped_folders}, "
        f"Errors {total_error_count}, "
        f"Originals deleted {total_deleted_original_count}"
    )

    return (
        total_processed_count,
        total_skipped_folders,
        total_error_count,
        total_deleted_original_count,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Resize, trim, and convert clipart images to PNG format."
    )
    parser.add_argument(
        "--input_folder",
        required=True,
        help="Path to the main input folder containing subfolders of images.",
    )
    parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size (pixels) for the longest edge. Aspect ratio is preserved.",
    )

    args = parser.parse_args()

    # Get absolute path for input folder
    absolute_input_folder = os.path.abspath(args.input_folder)
    process_images(absolute_input_folder, args.max_size)
