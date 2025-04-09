"""
Main module for pattern processing.
"""

import os
import sys
from typing import List, Optional

from utils.common import setup_logging, ensure_dir_exists
from pattern.resize import process_images
from pattern.mockups.seamless import create_pattern, create_seamless_mockup
from pattern.mockups.grid import create_grid_mockup_with_borders
from pattern.mockups.main_mockup import create_main_mockup
from pattern.mockups.layered import create_large_grid
from pattern.video import create_seamless_zoom_video

# Set up logging
logger = setup_logging(__name__)


def process_pattern_folder(input_folder: str, create_video: bool = False) -> bool:
    """
    Process a single pattern folder.

    Args:
        input_folder: Path to the input folder
        create_video: Whether to create video mockups

    Returns:
        True if processing was successful, False otherwise
    """
    if not os.path.isdir(input_folder):
        logger.error(f"Input folder not found: {input_folder}")
        return False

    # Create mocks output folder
    mocks_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(mocks_folder)

    # Get folder name for title
    folder_name = os.path.basename(input_folder)
    title = folder_name.replace("_", " ").replace("-", " ").title()

    logger.info(f"Processing folder: {folder_name}")
    logger.info(f"Title: {title}")

    try:
        # Create seamless pattern (only for patterns, not clipart)
        seamless_pattern_file = create_pattern(input_folder)

        # Create seamless zoom video (only for patterns, not clipart) if requested
        if create_video:
            logger.info("Creating video mockup as requested")
            create_seamless_zoom_video(input_folder, seamless_pattern_file)
        else:
            logger.info("Skipping video creation (use --create_video to enable)")

        # Create seamless mockup (only for patterns, not clipart)
        # This uses canvas2.png and should only be used for patterns
        create_seamless_mockup(input_folder)

        # Create main mockup
        create_main_mockup(input_folder, title)

        # Create grid mockup with borders
        create_grid_mockup_with_borders(input_folder)

        # Create large grid
        create_large_grid(input_folder)

        logger.info(f"Finished processing folder: {folder_name}")
        return True

    except Exception as e:
        logger.error(f"Error processing folder {folder_name}: {e}")
        return False


def process_all_patterns(base_input_dir: str, create_video: bool = False) -> bool:
    """
    Process all pattern folders in the base input directory.

    Args:
        base_input_dir: Path to the base input directory
        create_video: Whether to create video mockups

    Returns:
        True if processing was successful, False otherwise
    """
    if not os.path.isdir(base_input_dir):
        logger.error(f"Base input directory not found: {base_input_dir}")
        return False

    # Find subfolders to process
    folders_to_ignore = {"mocks", "zipped"}
    subfolders = [
        os.path.join(base_input_dir, d)
        for d in os.listdir(base_input_dir)
        if os.path.isdir(os.path.join(base_input_dir, d)) and d not in folders_to_ignore
    ]

    if not subfolders:
        logger.warning("No valid subfolders found in the input directory to process.")
        return False

    logger.info(f"Found {len(subfolders)} subfolder(s) to process.")

    success = True
    for subfolder in subfolders:
        if not process_pattern_folder(subfolder, create_video):
            success = False

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process pattern images and create mockups"
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        help="Path to the base input directory containing pattern subfolders",
    )
    parser.add_argument(
        "--resize", action="store_true", help="Resize images before processing"
    )
    parser.add_argument(
        "--max_width",
        type=int,
        default=3600,
        help="Maximum width for resizing (if --resize is specified)",
    )
    parser.add_argument(
        "--max_height",
        type=int,
        default=3600,
        help="Maximum height for resizing (if --resize is specified)",
    )

    args = parser.parse_args()

    logger.info("Starting pattern processing")

    # Resize images if requested
    if args.resize:
        logger.info("Resizing images...")
        process_images(args.input_dir, (args.max_width, args.max_height))

    # Process patterns
    if process_all_patterns(args.input_dir):
        logger.info("Pattern processing completed successfully")
    else:
        logger.error("Pattern processing completed with errors")
        sys.exit(1)
