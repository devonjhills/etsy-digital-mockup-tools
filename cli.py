#!/usr/bin/env python3
"""
Main command-line interface for mockup tools.
"""
import os
import sys
import argparse

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the mockup tools CLI.
    """
    parser = argparse.ArgumentParser(description="Mockup tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Pattern command
    pattern_parser = subparsers.add_parser("pattern", help="Pattern processing tools")
    pattern_subparsers = pattern_parser.add_subparsers(
        dest="pattern_command", help="Pattern command to run"
    )

    # Pattern all command
    pattern_all_parser = pattern_subparsers.add_parser(
        "all", help="Run the complete pattern workflow"
    )
    pattern_all_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )
    pattern_all_parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum size in MB for zip files",
    )
    pattern_all_parser.add_argument(
        "--image_quality", type=int, default=75, help="JPEG quality for zip files"
    )
    pattern_all_parser.add_argument(
        "--create_video", action="store_true", help="Create video mockups"
    )

    # Pattern resize command
    pattern_resize_parser = pattern_subparsers.add_parser(
        "resize", help="Resize pattern images"
    )
    pattern_resize_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )
    pattern_resize_parser.add_argument(
        "--max_width", type=int, default=3600, help="Maximum width in pixels"
    )
    pattern_resize_parser.add_argument(
        "--max_height", type=int, default=3600, help="Maximum height in pixels"
    )

    # Pattern mockup command
    pattern_mockup_parser = pattern_subparsers.add_parser(
        "mockup", help="Create pattern mockups"
    )
    pattern_mockup_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing pattern subfolders",
    )

    # Clipart command
    clipart_parser = subparsers.add_parser("clipart", help="Clipart processing tools")
    clipart_subparsers = clipart_parser.add_subparsers(
        dest="clipart_command", help="Clipart command to run"
    )

    # Clipart all command
    clipart_all_parser = clipart_subparsers.add_parser(
        "all", help="Run the complete clipart workflow"
    )
    clipart_all_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base input directory containing clipart subfolders",
    )
    clipart_all_parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size in pixels for clipart resizing",
    )
    clipart_all_parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for all generated mockups",
    )
    clipart_all_parser.add_argument(
        "--create_video", action="store_true", help="Create video mockups"
    )

    # Clipart resize command
    clipart_resize_parser = clipart_subparsers.add_parser(
        "resize", help="Resize clipart images"
    )
    clipart_resize_parser.add_argument(
        "--input_folder",
        default="input",
        help="Path to the main input folder containing subfolders of images",
    )
    clipart_resize_parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size (pixels) for the longest edge",
    )

    # Clipart mockup command
    clipart_mockup_parser = clipart_subparsers.add_parser(
        "mockup", help="Create clipart mockups"
    )
    clipart_mockup_parser.add_argument(
        "--input_dir",
        default="input",
        help="Path to the base directory containing subfolders of images",
    )
    clipart_mockup_parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for all generated mockups",
    )

    # Wall art command
    wall_art_parser = subparsers.add_parser(
        "wall-art", help="Wall art processing tools"
    )
    wall_art_subparsers = wall_art_parser.add_subparsers(
        dest="wall_art_command", help="Wall art command to run"
    )

    # Wall art all command
    wall_art_all_parser = wall_art_subparsers.add_parser(
        "all", help="Run the complete wall art workflow"
    )

    # Wall art process command
    wall_art_process_parser = wall_art_subparsers.add_parser(
        "process", help="Process wall art images"
    )

    # Wall art mockup command
    wall_art_mockup_parser = wall_art_subparsers.add_parser(
        "mockup", help="Create wall art mockups"
    )

    # Brush strokes command
    brush_strokes_parser = subparsers.add_parser(
        "brush-strokes", help="Brush strokes processing tools"
    )
    brush_strokes_subparsers = brush_strokes_parser.add_subparsers(
        dest="brush_strokes_command", help="Brush strokes command to run"
    )

    # Brush strokes all command
    brush_strokes_all_parser = brush_strokes_subparsers.add_parser(
        "all", help="Run the complete brush strokes workflow"
    )

    # Brush strokes process command
    brush_strokes_process_parser = brush_strokes_subparsers.add_parser(
        "process", help="Process brush strokes images"
    )

    # Brush strokes mask command
    brush_strokes_mask_parser = brush_strokes_subparsers.add_parser(
        "mask", help="Apply mask to brush strokes images"
    )

    # Etsy command
    etsy_parser = subparsers.add_parser("etsy", help="Etsy integration tools")
    etsy_subparsers = etsy_parser.add_subparsers(
        dest="etsy_command", help="Etsy command to run"
    )

    # Etsy auth command
    etsy_auth_parser = etsy_subparsers.add_parser("auth", help="Authenticate with Etsy")

    # Etsy create command
    etsy_create_parser = etsy_subparsers.add_parser(
        "create", help="Create an Etsy listing"
    )
    etsy_create_parser.add_argument(
        "--folder", required=True, help="Path to the product folder"
    )
    etsy_create_parser.add_argument(
        "--product_type",
        required=True,
        choices=["pattern", "patterns", "clipart", "wall_art", "brush_strokes"],
        help="Product type",
    )
    etsy_create_parser.add_argument(
        "--name", help="Product name (defaults to folder name)"
    )
    etsy_create_parser.add_argument(
        "--title", help="Custom title for the listing (optional)"
    )
    etsy_create_parser.add_argument(
        "--description", help="Custom description for the listing (optional)"
    )
    etsy_create_parser.add_argument(
        "--tags", help="Comma-separated list of tags for the listing (optional, max 13)"
    )
    etsy_create_parser.add_argument(
        "--draft",
        action="store_true",
        help="Create as draft instead of publishing immediately",
    )

    # Etsy template commands
    etsy_template_parser = etsy_subparsers.add_parser(
        "template", help="Manage listing templates"
    )
    etsy_template_subparsers = etsy_template_parser.add_subparsers(
        dest="etsy_template_command", help="Template command to run"
    )

    # Etsy list templates command
    etsy_template_list_parser = etsy_template_subparsers.add_parser(
        "list", help="List available templates"
    )

    # Etsy create default templates command
    etsy_template_create_defaults_parser = etsy_template_subparsers.add_parser(
        "create-defaults", help="Create default templates"
    )

    args = parser.parse_args()

    if args.command == "pattern":
        # Import pattern CLI module
        from pattern.cli import main as pattern_main

        # Prepare sys.argv for pattern CLI
        sys.argv = [sys.argv[0]]
        if args.pattern_command:
            sys.argv.append(args.pattern_command)

            # Add arguments based on the pattern command
            if args.pattern_command == "all":
                sys.argv.extend(["--input_dir", args.input_dir])
                sys.argv.extend(["--max_size_mb", str(args.max_size_mb)])
                sys.argv.extend(["--image_quality", str(args.image_quality)])
                if args.create_video:
                    sys.argv.append("--create_video")
            elif args.pattern_command == "resize":
                sys.argv.extend(["--input_dir", args.input_dir])
                sys.argv.extend(["--max_width", str(args.max_width)])
                sys.argv.extend(["--max_height", str(args.max_height)])
            elif args.pattern_command == "mockup":
                sys.argv.extend(["--input_dir", args.input_dir])

        # Run pattern CLI
        pattern_main()

    elif args.command == "clipart":
        # Import clipart CLI module
        try:
            from clipart.cli import main as clipart_main

            # Prepare sys.argv for clipart CLI
            sys.argv = [sys.argv[0]]
            if args.clipart_command:
                sys.argv.append(args.clipart_command)

                # Add arguments based on the clipart command
                if args.clipart_command == "all":
                    sys.argv.extend(["--input_dir", args.input_dir])
                    sys.argv.extend(["--max_size", str(args.max_size)])
                    if args.title:
                        sys.argv.extend(["--title", args.title])
                    if args.create_video:
                        sys.argv.append("--create_video")
                elif args.clipart_command == "resize":
                    sys.argv.extend(["--input_folder", args.input_folder])
                    sys.argv.extend(["--max_size", str(args.max_size)])
                elif args.clipart_command == "mockup":
                    sys.argv.extend(["--input_dir", args.input_dir])
                    if args.title:
                        sys.argv.extend(["--title", args.title])

            # Run clipart CLI
            clipart_main()
        except ImportError:
            logger.error(
                "Clipart module not found. Please implement the clipart CLI module."
            )
            sys.exit(1)

    elif args.command == "wall-art":
        # Import wall art CLI module
        try:
            from wall_art.cli import main as wall_art_main

            # Prepare sys.argv for wall art CLI
            sys.argv = [sys.argv[0]]
            if args.wall_art_command:
                sys.argv.append(args.wall_art_command)

            # Run wall art CLI
            wall_art_main()
        except ImportError:
            logger.error(
                "Wall art module not found. Please implement the wall art CLI module."
            )
            sys.exit(1)

    elif args.command == "brush-strokes":
        # Import brush strokes CLI module
        try:
            from brush_strokes.cli import main as brush_strokes_main

            # Prepare sys.argv for brush strokes CLI
            sys.argv = [sys.argv[0]]
            if args.brush_strokes_command:
                sys.argv.append(args.brush_strokes_command)

            # Run brush strokes CLI
            brush_strokes_main()
        except ImportError:
            logger.error(
                "Brush strokes module not found. Please implement the brush strokes CLI module."
            )
            sys.exit(1)

    elif args.command == "etsy":
        # Import etsy CLI module
        try:
            from etsy.cli import main as etsy_main

            # Prepare sys.argv for etsy CLI
            sys.argv = [sys.argv[0]]
            if args.etsy_command:
                sys.argv.append(args.etsy_command)

                # Add arguments based on the etsy command
                if args.etsy_command == "create":
                    sys.argv.extend(["--folder", args.folder])
                    sys.argv.extend(["--product_type", args.product_type])
                    if args.name:
                        sys.argv.extend(["--name", args.name])
                    if args.title:
                        sys.argv.extend(["--title", args.title])
                    if args.description:
                        sys.argv.extend(["--description", args.description])
                    if args.tags:
                        sys.argv.extend(["--tags", args.tags])
                    if args.draft:
                        sys.argv.append("--draft")
                elif args.etsy_command == "template" and args.etsy_template_command:
                    sys.argv.extend([args.etsy_template_command])

            # Run etsy CLI
            etsy_main()
        except ImportError:
            logger.error("Etsy module not found. Please implement the etsy CLI module.")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
