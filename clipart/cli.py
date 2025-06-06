"""
Command-line interface for clipart processing.
"""

import os
import sys
import argparse

from utils.common import setup_logging, run_script
from clipart.resize import process_images
from clipart.main import process_clipart

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

    all_parser.add_argument(
        "--title_font",
        default=None,
        help="Font to use for the title text (e.g., Angelina, Clattering, MarkerFelt, Poppins)",
    )
    all_parser.add_argument(
        "--subtitle_font",
        default=None,
        help="Font to use for the subtitle text (e.g., MarkerFelt, Angelina, Clattering, Poppins)",
    )
    all_parser.add_argument(
        "--title_font_size",
        type=int,
        default=None,
        help="Maximum font size for the title text (default: 170)",
    )
    all_parser.add_argument(
        "--subtitle_font_size",
        type=int,
        default=None,
        help="Font size for the subtitle text (default: 70)",
    )
    all_parser.add_argument(
        "--subtitle_spacing",
        type=int,
        default=None,
        help="Spacing between title and subtitles (default: 35)",
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
    mockup_parser.add_argument(
        "--title_font",
        default=None,
        help="Font to use for the title text (e.g., Angelina, Clattering, MarkerFelt, Poppins)",
    )
    mockup_parser.add_argument(
        "--subtitle_font",
        default=None,
        help="Font to use for the subtitle text (e.g., MarkerFelt, Angelina, Clattering, Poppins)",
    )
    mockup_parser.add_argument(
        "--title_font_size",
        type=int,
        default=None,
        help="Maximum font size for the title text (default: 170)",
    )
    mockup_parser.add_argument(
        "--subtitle_font_size",
        type=int,
        default=None,
        help="Font size for the subtitle text (default: 70)",
    )
    mockup_parser.add_argument(
        "--subtitle_spacing",
        type=int,
        default=None,
        help="Spacing between title and subtitles (default: 35)",
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

        # Step 1: Resize images
        logger.info("Step 1: Resizing clipart images...")
        process_images(args.input_dir, args.max_size)

        # Step 2: Create mockups
        logger.info("Step 2: Creating clipart mockups...")
        process_clipart(
            args.input_dir,
            args.title,
            args.create_video,
            args.title_font if hasattr(args, "title_font") else None,
            args.subtitle_font if hasattr(args, "subtitle_font") else None,
            args.title_font_size if hasattr(args, "title_font_size") else None,
            args.subtitle_font_size if hasattr(args, "subtitle_font_size") else None,
            args.subtitle_spacing if hasattr(args, "subtitle_spacing") else None,
        )

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
            args.title_font if hasattr(args, "title_font") else None,
            args.subtitle_font if hasattr(args, "subtitle_font") else None,
            args.title_font_size if hasattr(args, "title_font_size") else None,
            args.subtitle_font_size if hasattr(args, "subtitle_font_size") else None,
            args.subtitle_spacing if hasattr(args, "subtitle_spacing") else None,
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
