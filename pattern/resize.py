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

        # Process each image
        for index, image_file in enumerate(sorted(image_files), start=1):
            try:
                with Image.open(image_file) as img:
                    # Get original dimensions
                    original_width, original_height = img.size

                    # Check if image is already within max dimensions
                    needs_resize = (
                        original_width > max_size[0] or original_height > max_size[1]
                    )

                    if not needs_resize:
                        logger.info(
                            f"    {os.path.basename(image_file)} already within max dimensions"
                        )
                        # Even if no resize needed, we still want to rename the file
                        img_to_save = img
                    else:
                        # Calculate new dimensions while maintaining aspect ratio
                        width_ratio = max_size[0] / original_width
                        height_ratio = max_size[1] / original_height
                        ratio = min(width_ratio, height_ratio)

                        new_width = int(original_width * ratio)
                        new_height = int(original_height * ratio)

                        # Resize the image
                        img_to_save = img.resize(
                            (new_width, new_height), get_resampling_filter()
                        )

                        # Set DPI
                        if hasattr(img_to_save, "info"):
                            img_to_save.info["dpi"] = dpi

                    # Log resize info if needed
                    if needs_resize:
                        logger.info(
                            f"    Resized {os.path.basename(image_file)} from {original_width}x{original_height} to {new_width}x{new_height}"
                        )
                    else:
                        # Set these variables for consistent code below
                        new_width, new_height = original_width, original_height

                    # Create new filename based on subfolder name and index
                    original_filename = os.path.basename(image_file)
                    # Default to jpg for consistency
                    new_filename = f"{safe_subfolder_name}_{index}.jpg"
                    new_file_path = os.path.join(
                        os.path.dirname(image_file), new_filename
                    )

                    # Check if the file is already correctly named
                    if original_filename == new_filename:
                        logger.info(f"    File already correctly named: {new_filename}")
                        # If resize was needed, save in place
                        if needs_resize:
                            img_to_save.save(
                                new_file_path,
                                format="JPEG",
                                dpi=dpi,
                                quality=85,
                                optimize=True,
                            )
                            logger.info(
                                f"    Updated file with resized version: {new_filename}"
                            )
                    else:
                        # Save the image with the new name
                        img_to_save.save(
                            new_file_path,
                            format="JPEG",
                            dpi=dpi,
                            quality=85,
                            optimize=True,
                        )

                        # Remove the original file if it's different from the new file
                        try:
                            os.remove(image_file)
                            logger.info(
                                f"    Renamed and replaced: {original_filename} -> {new_filename}"
                            )
                        except OSError as e:
                            logger.error(
                                f"    Could not remove original file {image_file}: {e}"
                            )

            except Exception as e:
                logger.error(f"    Error processing {image_file}: {e}")

    logger.info("Image processing complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resize pattern images")
    parser.add_argument(
        "--input_folder",
        required=True,
        help="Path to the input folder containing subfolders with images",
    )
    parser.add_argument(
        "--max_width", type=int, default=3600, help="Maximum width in pixels"
    )
    parser.add_argument(
        "--max_height", type=int, default=3600, help="Maximum height in pixels"
    )
    parser.add_argument("--dpi_x", type=int, default=300, help="Horizontal DPI")
    parser.add_argument("--dpi_y", type=int, default=300, help="Vertical DPI")

    args = parser.parse_args()

    process_images(
        args.input_folder, (args.max_width, args.max_height), (args.dpi_x, args.dpi_y)
    )
