"""
Main module for pattern processing.
"""

import os
import sys

from utils.common import setup_logging, ensure_dir_exists
from pattern.resize import process_images
from pattern.seamless import create_pattern, create_seamless_mockup
from pattern.mockups.grid import create_grid_mockup_with_borders

# Import the new dynamic main mockup instead of the old one
from pattern.mockups.dynamic_main_mockup import create_main_mockup
from pattern.mockups.layered import create_large_grid
from pattern.video import create_seamless_zoom_video

# Set up logging
logger = setup_logging(__name__)


def process_pattern_folder(
    input_folder: str,
    create_video: bool = False,
    title_font: str = None,
    subtitle_font: str = None,
    title_font_size: int = None,
    top_subtitle_font_size: int = None,
    bottom_subtitle_font_size: int = None,
    use_dynamic_title_colors: bool = None,
    vertical_spacing: int = None,
    title_bottom_subtitle_spacing: int = None,
) -> bool:
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

        # Create main mockup with font, color, and spacing settings
        create_main_mockup(
            input_folder,
            title,
            title_font=title_font,
            subtitle_font=subtitle_font,
            title_font_size=title_font_size,
            top_subtitle_font_size=top_subtitle_font_size,
            bottom_subtitle_font_size=bottom_subtitle_font_size,
            use_dynamic_title_colors=use_dynamic_title_colors,
            vertical_spacing=vertical_spacing,
            title_bottom_subtitle_spacing=title_bottom_subtitle_spacing,
        )

        # Create grid mockup with borders
        create_grid_mockup_with_borders(input_folder)

        # Create large grid
        create_large_grid(input_folder)

        logger.info(f"Finished processing folder: {folder_name}")
        return True

    except Exception as e:
        logger.error(f"Error processing folder {folder_name}: {e}")
        return False


def process_all_patterns(
    base_input_dir: str,
    create_video: bool = False,
    title_font: str = None,
    subtitle_font: str = None,
    title_font_size: int = None,
    top_subtitle_font_size: int = None,
    bottom_subtitle_font_size: int = None,
    use_dynamic_title_colors: bool = None,
    vertical_spacing: int = None,
    title_bottom_subtitle_spacing: int = None,
) -> bool:
    """
    Process all pattern folders in the base input directory.

    Args:
        base_input_dir: Path to the base input directory
        create_video: Whether to create video mockups
        title_font: Font to use for the title text
        subtitle_font: Font to use for the subtitle text
        title_font_size: Font size for the title
        top_subtitle_font_size: Font size for the top subtitle
        bottom_subtitle_font_size: Font size for the bottom subtitle
        use_dynamic_title_colors: Whether to use dynamic title colors based on input image

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
        if not process_pattern_folder(
            subfolder,
            create_video,
            title_font=title_font,
            subtitle_font=subtitle_font,
            title_font_size=title_font_size,
            top_subtitle_font_size=top_subtitle_font_size,
            bottom_subtitle_font_size=bottom_subtitle_font_size,
            use_dynamic_title_colors=use_dynamic_title_colors,
            vertical_spacing=vertical_spacing,
            title_bottom_subtitle_spacing=title_bottom_subtitle_spacing,
        ):
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

    # Font options
    parser.add_argument(
        "--title_font",
        choices=["Angelina", "MarkerFelt", "Clattering", "Cravelo", "Poppins"],
        help="Font to use for the title text",
    )
    parser.add_argument(
        "--subtitle_font",
        choices=["Poppins", "MarkerFelt", "Angelina", "Clattering", "Cravelo"],
        help="Font to use for the subtitle text",
    )
    parser.add_argument(
        "--title_font_size",
        type=int,
        help="Font size for the title (0 for auto-sizing)",
    )
    parser.add_argument(
        "--top_subtitle_font_size",
        type=int,
        help="Font size for the top subtitle (0 for auto-sizing)",
    )
    parser.add_argument(
        "--bottom_subtitle_font_size",
        type=int,
        help="Font size for the bottom subtitle (0 for auto-sizing)",
    )
    parser.add_argument(
        "--use_dynamic_title_colors",
        action="store_true",
        help="Use dynamic title colors based on input image",
    )
    parser.add_argument(
        "--no_dynamic_title_colors",
        action="store_true",
        help="Disable dynamic title colors",
    )
    parser.add_argument(
        "--vertical_spacing",
        type=int,
        help="Vertical spacing between text elements (default: 20)",
    )
    parser.add_argument(
        "--title_bottom_spacing",
        type=int,
        help="Spacing between title and bottom subtitle (default: 10)",
    )

    args = parser.parse_args()

    logger.info("Starting pattern processing")

    # Resize images if requested
    if args.resize:
        logger.info("Resizing images...")
        process_images(args.input_dir, (args.max_width, args.max_height))

    # Determine dynamic title colors setting
    use_dynamic_title_colors = None
    if hasattr(args, "use_dynamic_title_colors") and args.use_dynamic_title_colors:
        use_dynamic_title_colors = True
    elif hasattr(args, "no_dynamic_title_colors") and args.no_dynamic_title_colors:
        use_dynamic_title_colors = False

    # Process patterns with font, color, and spacing settings
    if process_all_patterns(
        args.input_dir,
        False,  # create_video
        title_font=args.title_font if hasattr(args, "title_font") else None,
        subtitle_font=args.subtitle_font if hasattr(args, "subtitle_font") else None,
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
        vertical_spacing=(
            args.vertical_spacing if hasattr(args, "vertical_spacing") else None
        ),
        title_bottom_subtitle_spacing=(
            args.title_bottom_spacing if hasattr(args, "title_bottom_spacing") else None
        ),
    ):
        logger.info("Pattern processing completed successfully")
    else:
        logger.error("Pattern processing completed with errors")
        sys.exit(1)
