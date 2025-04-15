"""
Command-line interface for clipart processing.
"""

import os
import sys
import argparse

from utils.common import setup_logging, run_script
from clipart.resize import process_images
from clipart.main import process_clipart
from folder_renamer import process_input_directory

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the clipart CLI.
    """
    parser = argparse.ArgumentParser(description="Clipart processing tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # All-in-one command
    all_parser = subparsers.add_parser("all", help="Run the complete clipart workflow")
    all_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing clipart subfolders",
    )
    all_parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size in pixels for clipart resizing",
    )
    all_parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for all generated mockups",
    )
    all_parser.add_argument(
        "--zip_max_mb",
        type=float,
        default=20.0,
        help="Maximum size in MB for zip files",
    )
    all_parser.add_argument(
        "--zip_quality", type=int, default=80, help="JPEG quality for zip files"
    )
    all_parser.add_argument(
        "--create_video", action="store_true", help="Create video mockups"
    )

    # Resize command
    resize_parser = subparsers.add_parser("resize", help="Resize clipart images")
    resize_parser.add_argument(
        "--input_folder",
        default="input",
        help="Path to the main input folder containing subfolders of images",
    )
    resize_parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size (pixels) for the longest edge",
    )

    # Mockup command
    mockup_parser = subparsers.add_parser("mockup", help="Create clipart mockups")
    mockup_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base directory containing subfolders of images",
    )
    mockup_parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for all generated mockups",
    )
    mockup_parser.add_argument(
        "--create_video", action="store_true", help="Create video mockups"
    )

    # Zip command
    zip_parser = subparsers.add_parser("zip", help="Create zip files of clipart images")
    zip_parser.add_argument(
        "--source_folder",
        default="input",
        help="Path to the base input directory containing clipart subfolders",
    )
    zip_parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum size in MB for zip files",
    )
    zip_parser.add_argument(
        "--image_quality", type=int, default=80, help="JPEG quality for zip files"
    )

    args = parser.parse_args()

    if args.command == "all":
        # Step 0: Rename folders based on Gemini API analysis
        logger.info("Step 0: Renaming folders based on Gemini API analysis...")
        # Get Gemini API key from environment
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if gemini_api_key:
            process_input_directory(args.input_dir, gemini_api_key)
        else:
            logger.warning(
                "GEMINI_API_KEY not found in environment variables. Skipping folder renaming."
            )

        # Step 1: Resize images
        logger.info("Step 1: Resizing clipart images...")
        process_images(args.input_dir, args.max_size)

        # Step 2: Create mockups
        logger.info("Step 2: Creating clipart mockups...")
        process_clipart(args.input_dir, args.title, args.create_video)

        # Step 3: Create zip files
        logger.info("Step 3: Creating zip files...")
        zip_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zip.py"
        )
        zip_args = [
            "--source_folder",
            args.input_dir,
            "--max_size_mb",
            str(args.zip_max_mb),
            "--image_quality",
            str(args.zip_quality),
        ]
        if not run_script(zip_script, "Zipper", zip_args):
            logger.error("Error creating zip files")
            sys.exit(1)

        logger.info("Clipart workflow completed successfully")

    elif args.command == "resize":
        process_images(args.input_folder, args.max_size)

    elif args.command == "mockup":
        process_clipart(
            args.input_dir,
            args.title,
            args.create_video if hasattr(args, "create_video") else False,
        )

    elif args.command == "zip":
        zip_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zip.py"
        )
        zip_args = [
            "--source_folder",
            args.source_folder,
            "--max_size_mb",
            str(args.max_size_mb),
            "--image_quality",
            str(args.image_quality),
        ]
        if not run_script(zip_script, "Zipper", zip_args):
            logger.error("Error creating zip files")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
