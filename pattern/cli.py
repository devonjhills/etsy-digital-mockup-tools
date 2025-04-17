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
    all_parser.add_argument(
        "--provider",
        choices=["gemini", "openai"],
        help="AI provider to use for content generation (overrides environment variable)",
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
        if not process_all_patterns(args.input_dir, args.create_video):
            logger.error("Error creating pattern mockups")
            sys.exit(1)

        # Set AI provider if specified
        if hasattr(args, "provider") and args.provider:
            os.environ["AI_PROVIDER"] = args.provider
            logger.info(f"Using AI provider: {args.provider}")

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
        if not process_all_patterns(args.input_dir):
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
