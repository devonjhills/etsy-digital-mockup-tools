"""
Command-line interface for pattern processing.
"""

import os
import sys
import argparse

from utils.common import setup_logging, run_script
from pattern.main import process_all_patterns
from pattern.resize import process_images

# Folder renamer functionality has been removed

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the pattern CLI.
    """
    parser = argparse.ArgumentParser(description="Pattern processing tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # All-in-one command
    all_parser = subparsers.add_parser("all", help="Run the complete pattern workflow")
    all_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )
    all_parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum size in MB for zip files",
    )
    all_parser.add_argument(
        "--image_quality", type=int, default=75, help="JPEG quality for zip files"
    )
    all_parser.add_argument(
        "--create_video", action="store_true", help="Create video mockups"
    )

    # Font options
    all_parser.add_argument(
        "--title_font",
        choices=["Angelina", "MarkerFelt", "Clattering", "Cravelo", "Poppins"],
        help="Font to use for the title text",
    )
    all_parser.add_argument(
        "--subtitle_font",
        choices=["Poppins", "MarkerFelt", "Angelina", "Clattering", "Cravelo"],
        help="Font to use for the subtitle text",
    )
    all_parser.add_argument(
        "--title_font_size",
        type=int,
        help="Font size for the title (0 for auto-sizing)",
    )
    all_parser.add_argument(
        "--top_subtitle_font_size",
        type=int,
        help="Font size for the top subtitle (0 for auto-sizing)",
    )
    all_parser.add_argument(
        "--bottom_subtitle_font_size",
        type=int,
        help="Font size for the bottom subtitle (0 for auto-sizing)",
    )
    # Color options
    all_parser.add_argument(
        "--use_dynamic_title_colors",
        action="store_true",
        help="Use dynamic title colors based on input image",
    )
    all_parser.add_argument(
        "--no_dynamic_title_colors",
        action="store_true",
        help="Disable dynamic title colors",
    )
    # Spacing options
    all_parser.add_argument(
        "--top_subtitle_padding",
        type=int,
        help="Padding above the top subtitle (default: 30)",
    )
    all_parser.add_argument(
        "--bottom_subtitle_padding",
        type=int,
        help="Padding below the bottom subtitle (default: 30)",
    )

    # Resize command
    resize_parser = subparsers.add_parser("resize", help="Resize pattern images")
    resize_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )
    resize_parser.add_argument(
        "--max_width", type=int, default=3600, help="Maximum width in pixels"
    )
    resize_parser.add_argument(
        "--max_height", type=int, default=3600, help="Maximum height in pixels"
    )

    # Mockup command
    mockup_parser = subparsers.add_parser("mockup", help="Create pattern mockups")
    mockup_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )

    # Font options
    mockup_parser.add_argument(
        "--title_font",
        choices=["Angelina", "MarkerFelt", "Clattering", "Cravelo", "Poppins"],
        help="Font to use for the title text",
    )
    mockup_parser.add_argument(
        "--subtitle_font",
        choices=["Poppins", "MarkerFelt", "Angelina", "Clattering", "Cravelo"],
        help="Font to use for the subtitle text",
    )
    mockup_parser.add_argument(
        "--title_font_size",
        type=int,
        help="Font size for the title (0 for auto-sizing)",
    )
    mockup_parser.add_argument(
        "--top_subtitle_font_size",
        type=int,
        help="Font size for the top subtitle (0 for auto-sizing)",
    )
    mockup_parser.add_argument(
        "--bottom_subtitle_font_size",
        type=int,
        help="Font size for the bottom subtitle (0 for auto-sizing)",
    )
    # Color options
    mockup_parser.add_argument(
        "--use_dynamic_title_colors",
        action="store_true",
        help="Use dynamic title colors based on input image",
    )
    mockup_parser.add_argument(
        "--no_dynamic_title_colors",
        action="store_true",
        help="Disable dynamic title colors",
    )
    # Spacing options
    mockup_parser.add_argument(
        "--top_subtitle_padding",
        type=int,
        help="Padding above the top subtitle (default: 30)",
    )
    mockup_parser.add_argument(
        "--bottom_subtitle_padding",
        type=int,
        help="Padding below the bottom subtitle (default: 30)",
    )

    # Zip command
    zip_parser = subparsers.add_parser("zip", help="Create zip files of pattern images")
    zip_parser.add_argument(
        "--source_folder",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )
    zip_parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum size in MB for zip files",
    )
    zip_parser.add_argument(
        "--image_quality", type=int, default=75, help="JPEG quality for zip files"
    )

    args = parser.parse_args()

    if args.command == "all":
        # Folder renaming functionality has been removed
        logger.info("Starting pattern workflow...")

        # Step 1: Resize images
        logger.info("Step 1: Resizing pattern images...")
        process_images(args.input_dir)

        # Step 2: Create mockups
        logger.info("Step 2: Creating pattern mockups...")
        # Determine dynamic title colors setting
        use_dynamic_title_colors = None
        if hasattr(args, "use_dynamic_title_colors") and args.use_dynamic_title_colors:
            use_dynamic_title_colors = True
            logger.info("Using dynamic title colors based on input image")
        elif hasattr(args, "no_dynamic_title_colors") and args.no_dynamic_title_colors:
            use_dynamic_title_colors = False
            logger.info("Using default title colors (dynamic colors disabled)")

        # Get padding settings
        top_subtitle_padding = (
            args.top_subtitle_padding if hasattr(args, "top_subtitle_padding") else None
        )
        bottom_subtitle_padding = (
            args.bottom_subtitle_padding
            if hasattr(args, "bottom_subtitle_padding")
            else None
        )

        if top_subtitle_padding is not None:
            logger.info(f"Using custom top subtitle padding: {top_subtitle_padding}")
        if bottom_subtitle_padding is not None:
            logger.info(
                f"Using custom bottom subtitle padding: {bottom_subtitle_padding}"
            )

        if not process_all_patterns(
            args.input_dir,
            args.create_video,
            title_font=args.title_font if hasattr(args, "title_font") else None,
            subtitle_font=(
                args.subtitle_font if hasattr(args, "subtitle_font") else None
            ),
            title_font_size=(
                args.title_font_size if hasattr(args, "title_font_size") else None
            ),
            top_subtitle_font_size=(
                args.top_subtitle_font_size
                if hasattr(args, "top_subtitle_font_size")
                else None
            ),
            bottom_subtitle_font_size=(
                args.bottom_subtitle_font_size
                if hasattr(args, "bottom_subtitle_font_size")
                else None
            ),
            use_dynamic_title_colors=use_dynamic_title_colors,
            top_subtitle_padding=top_subtitle_padding,
            bottom_subtitle_padding=bottom_subtitle_padding,
        ):
            logger.error("Error creating pattern mockups")
            sys.exit(1)

        # Step 3: Create zip files
        logger.info("Step 3: Creating zip files...")
        zip_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zip.py"
        )
        zip_args = [
            "--source_folder",
            args.input_dir,
            "--max_size_mb",
            str(args.max_size_mb),
            "--image_quality",
            str(args.image_quality),
        ]
        if not run_script(zip_script, "Zipper", zip_args):
            logger.error("Error creating zip files")
            sys.exit(1)

        logger.info("Pattern workflow completed successfully")

    elif args.command == "resize":
        process_images(args.input_dir, (args.max_width, args.max_height))

    elif args.command == "mockup":
        # Determine dynamic title colors setting
        use_dynamic_title_colors = None
        if hasattr(args, "use_dynamic_title_colors") and args.use_dynamic_title_colors:
            use_dynamic_title_colors = True
            logger.info("Using dynamic title colors based on input image")
        elif hasattr(args, "no_dynamic_title_colors") and args.no_dynamic_title_colors:
            use_dynamic_title_colors = False
            logger.info("Using default title colors (dynamic colors disabled)")

        # Get padding settings
        top_subtitle_padding = (
            args.top_subtitle_padding if hasattr(args, "top_subtitle_padding") else None
        )
        bottom_subtitle_padding = (
            args.bottom_subtitle_padding
            if hasattr(args, "bottom_subtitle_padding")
            else None
        )

        if top_subtitle_padding is not None:
            logger.info(f"Using custom top subtitle padding: {top_subtitle_padding}")
        if bottom_subtitle_padding is not None:
            logger.info(
                f"Using custom bottom subtitle padding: {bottom_subtitle_padding}"
            )

        if not process_all_patterns(
            args.input_dir,
            False,  # create_video
            title_font=args.title_font if hasattr(args, "title_font") else None,
            subtitle_font=(
                args.subtitle_font if hasattr(args, "subtitle_font") else None
            ),
            title_font_size=(
                args.title_font_size if hasattr(args, "title_font_size") else None
            ),
            top_subtitle_font_size=(
                args.top_subtitle_font_size
                if hasattr(args, "top_subtitle_font_size")
                else None
            ),
            bottom_subtitle_font_size=(
                args.bottom_subtitle_font_size
                if hasattr(args, "bottom_subtitle_font_size")
                else None
            ),
            use_dynamic_title_colors=use_dynamic_title_colors,
            top_subtitle_padding=top_subtitle_padding,
            bottom_subtitle_padding=bottom_subtitle_padding,
        ):
            logger.error("Error creating pattern mockups")
            sys.exit(1)

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
