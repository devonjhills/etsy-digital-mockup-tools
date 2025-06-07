"""
Main module for clipart processing.
"""

import os
import glob
from typing import List, Tuple
from PIL import Image

from utils.common import (
    setup_logging,
    ensure_dir_exists,
    clean_identifier_files,
    safe_load_image,
)
from clipart import config

# Import resize module for CLI usage only
from clipart.processing.square_mockup import create_square_mockup
from clipart.processing.grid import create_2x2_grid
from clipart.processing.transparency import create_transparency_demo

# Title bar is now handled by square_mockup
from clipart.video import create_video_mockup

# Set up logging
logger = setup_logging(__name__)


def grid_mockup(
    input_dir_base: str, title_override: str = None, create_video: bool = False
) -> List[str]:
    """
    Generate various mockups for images found in subfolders of input_dir_base.
    Saves results into a 'mocks' subfolder WITHIN each processed input subfolder.

    Args:
        input_dir_base: Path to the base directory containing subfolders of images
        title_override: Optional override title for all generated mockups
        create_video: Whether to create video mockups

    Returns:
        List of paths to all generated mockup files
    """
    generated_files_all_folders = []

    # Verify input base directory
    if not os.path.isdir(input_dir_base):
        logger.critical(
            f"Input directory base not found or not a directory: {input_dir_base}"
        )
        return []

    # Find subfolders
    try:
        subfolders = sorted(
            [
                f.path
                for f in os.scandir(input_dir_base)
                if f.is_dir() and not f.name.startswith(".") and f.name != "mocks"
            ]
        )
    except OSError as e:
        logger.critical(f"Error scanning input directory {input_dir_base}: {e}")
        return []

    if not subfolders:
        logger.warning(
            f"No valid subdirectories (excluding 'mocks') found in '{input_dir_base}'. Nothing to process."
        )
        return []

    logger.info(
        f"Found {len(subfolders)} potential subfolder(s) in '{input_dir_base}' to process."
    )

    # Process each subfolder
    for index, input_folder_path in enumerate(subfolders, start=1):
        subfolder_name = os.path.basename(input_folder_path)

        # Determine title
        title = (
            title_override
            if title_override
            else " ".join(
                word.capitalize()
                for word in subfolder_name.replace("_", " ").replace("-", " ").split()
            )
        )

        # Define output path: 'mocks' folder inside the input subfolder
        mocks_output_folder_path = os.path.join(input_folder_path, "mocks")

        logger.info(
            f"\n{'=' * 15} Processing Folder {index}/{len(subfolders)}: {subfolder_name} {'=' * 15}"
        )
        logger.info(f"  Input Path: {input_folder_path}")
        logger.info(f"  Outputting Mocks To: {mocks_output_folder_path}")
        logger.info(f"  Title: '{title}'")

        # Create the 'mocks' output directory
        try:
            ensure_dir_exists(mocks_output_folder_path)
        except OSError as e:
            logger.error(
                f"Error creating mocks output directory {mocks_output_folder_path}: {e}. Skipping folder."
            )
            continue

        # Initialize lists for this specific folder
        output_filenames_current_folder = []
        video_source_filenames = []

        # Load backgrounds
        canvas_bg_main = None
        canvas_bg_2x2 = None

        try:
            # Load main background for collage AND title backdrop
            canvas_bg_main = safe_load_image(config.CANVAS_PATH, "RGBA")
            if canvas_bg_main:
                canvas_bg_main = canvas_bg_main.resize(
                    config.OUTPUT_SIZE, get_resampling_filter()
                )
            else:
                logger.warning(
                    f"Failed to load main canvas '{config.CANVAS_PATH}' required for collage and title. Generating fallback."
                )
                canvas_bg_main = generate_background(config.OUTPUT_SIZE).convert("RGBA")

            # Load background for 2x2 grid
            canvas_bg_2x2 = safe_load_image(config.CANVAS_PATH, "RGBA")
            if canvas_bg_2x2:
                canvas_bg_2x2 = canvas_bg_2x2.resize(
                    config.GRID_2x2_SIZE, get_resampling_filter()
                )
            else:
                logger.warning(
                    f"Failed to load 2x2 canvas '{config.CANVAS_PATH}'. Generating fallback."
                )
                canvas_bg_2x2 = generate_background(config.GRID_2x2_SIZE).convert(
                    "RGBA"
                )

        except Exception as e:
            logger.error(f"Error loading/resizing canvases: {e}. Using fallbacks.")
            if not canvas_bg_main:
                canvas_bg_main = generate_background(config.OUTPUT_SIZE).convert("RGBA")
            if not canvas_bg_2x2:
                canvas_bg_2x2 = generate_background(config.GRID_2x2_SIZE).convert(
                    "RGBA"
                )

        # Find input images - support both PNG and JPG/JPEG formats
        try:
            png_paths = sorted(glob.glob(os.path.join(input_folder_path, "*.png")))
            jpg_paths = sorted(glob.glob(os.path.join(input_folder_path, "*.jpg")))
            jpeg_paths = sorted(glob.glob(os.path.join(input_folder_path, "*.jpeg")))

            # Combine all image paths
            input_image_paths = png_paths + jpg_paths + jpeg_paths
        except Exception as e:
            logger.error(
                f"Error searching for image files in {input_folder_path}: {e}. Skipping folder."
            )
            continue

        num_images = len(input_image_paths)
        if not input_image_paths:
            logger.warning(
                f"No PNG or JPG images found in {input_folder_path}. Skipping mockup generation."
            )
            continue

        logger.info(f"Found {num_images} images for mockup generation.")

        # 1. Main Mockup Generation
        try:
            logger.info("--- Generating Main Mockup ---")

            # Create square mockup with 2x2 grid and title overlay
            output_main_filename = os.path.join(mocks_output_folder_path, "main.png")
            subtitle_bottom_text = config.SUBTITLE_BOTTOM_TEXT_FORMAT.format(
                num_images=num_images
            )

            # Load 2x2 grid background
            canvas_bg_2x2_copy = canvas_bg_2x2.copy()

            # Create square mockup
            logger.info(
                "Creating square mockup with 2x3 grid (2 columns, 3 rows) and title overlay..."
            )
            # Use the centralized font configuration
            final_main_mockup, _ = create_square_mockup(
                input_image_paths=input_image_paths,
                canvas_bg_image=canvas_bg_2x2_copy,
                title=title,
                subtitle_top=config.SUBTITLE_TEXT_TOP.format(num_images=num_images),
                subtitle_bottom=subtitle_bottom_text,
                grid_size=config.GRID_2x2_SIZE,
                padding=config.CELL_PADDING,
                # Use font configuration from config
                title_font_name=config.FONT_CONFIG["TITLE_FONT"],
                subtitle_font_name=config.FONT_CONFIG["SUBTITLE_FONT"],
                # Use font sizes from config
                title_max_font_size=config.FONT_CONFIG["TITLE_MAX_FONT_SIZE"],
                title_min_font_size=config.FONT_CONFIG["TITLE_MIN_FONT_SIZE"],
                subtitle_font_size=config.FONT_CONFIG["SUBTITLE_FONT_SIZE"],
                # Other settings
                title_padding_x=60,  # Smaller than default
            )

            # Save main mockup
            try:
                if final_main_mockup:
                    final_main_mockup.save(output_main_filename, "PNG")
                    logger.info(
                        f"Saved: {os.path.relpath(output_main_filename, input_dir_base)}"
                    )
                    output_filenames_current_folder.append(output_main_filename)
                else:
                    logger.error("Failed to create square mockup.")
            except Exception as e:
                logger.error(f"Error saving main mockup {output_main_filename}: {e}")

        except Exception as e:
            logger.error(
                f"Error during main mockup generation for {subfolder_name}: {e}"
            )

        # 2. 2x2 Grid Mockups
        try:
            logger.info("--- Generating 2x2 Grid Mockups ---")
            if canvas_bg_2x2:
                grid_count = 0
                for i in range(0, num_images, 4):
                    batch_paths = input_image_paths[i : i + 4]
                    if not batch_paths:
                        continue

                    grid_count += 1
                    logger.info(
                        f"Creating grid {grid_count} (images {i+1}-{i+len(batch_paths)})..."
                    )

                    mockup_2x2 = create_2x2_grid(
                        input_image_paths=batch_paths,
                        canvas_bg_image=canvas_bg_2x2.copy(),
                        grid_size=config.GRID_2x2_SIZE,
                        padding=config.CELL_PADDING,
                    )

                    from utils.common import apply_watermark
                    mockup_2x2_watermarked = apply_watermark(mockup_2x2)

                    output_filename = os.path.join(
                        mocks_output_folder_path, f"{grid_count+1:02d}_grid_mockup.png"
                    )

                    try:
                        mockup_2x2_watermarked.save(output_filename, "PNG")
                        logger.info(
                            f"Saved: {os.path.relpath(output_filename, input_dir_base)}"
                        )
                        output_filenames_current_folder.append(output_filename)
                        video_source_filenames.append(output_filename)
                    except Exception as e:
                        logger.error(f"Error saving 2x2 mockup {output_filename}: {e}")
            else:
                logger.warning(
                    "Skipping 2x2 grids: Background canvas for grids unavailable."
                )

        except Exception as e:
            logger.error(f"Error during 2x2 grid generation for {subfolder_name}: {e}")

        # 3. Transparency Demo
        try:
            logger.info("--- Generating Transparency Demo ---")
            if input_image_paths:
                first_image_path = input_image_paths[0]
                logger.info(f"Using image: {os.path.basename(first_image_path)}")

                trans_demo = create_transparency_demo(first_image_path)
                if trans_demo:
                    output_trans_demo = os.path.join(
                        mocks_output_folder_path,
                        f"{len(output_filenames_current_folder)+1:02d}_transparency_demo.png",
                    )

                    try:
                        trans_demo.save(output_trans_demo, "PNG")
                        logger.info(
                            f"Saved: {os.path.relpath(output_trans_demo, input_dir_base)}"
                        )
                        output_filenames_current_folder.append(output_trans_demo)
                    except Exception as e:
                        logger.error(
                            f"Error saving transparency demo {output_trans_demo}: {e}"
                        )
                else:
                    logger.warning(
                        f"Failed to create transparency demo for {first_image_path}."
                    )
            else:
                logger.warning("Skipping transparency demo: No input images found.")

        except Exception as e:
            logger.error(
                f"Error during transparency demo generation for {subfolder_name}: {e}"
            )

        # 4. Video Generation
        try:
            logger.info("--- Generating Video Mockup ---")
            # Use the create_video parameter passed to the function, overriding the config
            if create_video and video_source_filenames:
                logger.info(
                    f"Using {len(video_source_filenames)} source frames for video."
                )

                video_path = os.path.join(
                    mocks_output_folder_path,
                    f"{len(output_filenames_current_folder)+1:02d}_mockup_video.mp4",
                )

                try:
                    video_args = getattr(config, "VIDEO_ARGS", {})
                    success = create_video_mockup(
                        image_paths=video_source_filenames,
                        output_path=video_path,
                        **video_args,
                    )

                    if success:
                        output_filenames_current_folder.append(video_path)
                        logger.info(
                            f"Saved: {os.path.relpath(video_path, input_dir_base)}"
                        )
                    else:
                        logger.warning(
                            f"Video file {video_path} was not created or is empty."
                        )
                except Exception as e:
                    logger.error(f"Error during video creation: {e}")
            elif not create_video:
                logger.info("Skipping video generation (use --create_video to enable).")
            else:
                logger.info("Skipping video: No source grid images generated.")

        except Exception as e:
            logger.error(
                f"Error during video generation logic for {subfolder_name}: {e}"
            )

        # Add files generated for this folder to the overall list
        generated_files_all_folders.extend(output_filenames_current_folder)
        logger.info(
            f"Finished processing folder '{subfolder_name}'. Generated {len(output_filenames_current_folder)} file(s) in 'mocks' subfolder."
        )

    logger.info(f"\n--- Mockup Generation Complete for all folders ---")
    logger.info(f"Processed {len(subfolders)} subfolder(s) from '{input_dir_base}'.")
    logger.info(
        f"Outputs saved into 'mocks' subdirectories within each processed folder."
    )

    return generated_files_all_folders


def generate_background(
    size: Tuple[int, int], color: Tuple[int, int, int] = (248, 248, 248)
) -> Image.Image:
    """
    Generate a solid color background image.

    Args:
        size: Size of the background (width, height)
        color: Color of the background

    Returns:
        The background image
    """
    from PIL import Image

    return Image.new("RGB", size, color)


def get_resampling_filter():
    """
    Get the appropriate resampling filter based on the PIL version.

    Returns:
        The appropriate resampling filter
    """
    from PIL import Image

    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS


def process_clipart(
    input_dir: str,
    title_override: str = None,
    create_video: bool = False,
    title_font: str = None,
    subtitle_font: str = None,
    title_font_size: int = None,
    subtitle_font_size: int = None,
    subtitle_spacing: int = None,
) -> List[str]:
    """
    Process clipart images and generate mockups.

    Args:
        input_dir: Path to the input directory
        title_override: Optional override title for all generated mockups
        create_video: Whether to create video mockups

    Returns:
        List of paths to all generated mockup files
    """
    logger.info(f"Starting clipart processing for {input_dir}")

    # Check if input directory exists
    if not os.path.isdir(input_dir):
        logger.critical(f"Input directory '{input_dir}' not found.")
        return []

    # Clean identifier files if configured
    delete_identifiers = getattr(config, "DELETE_IDENTIFIERS_ON_START", False)
    if delete_identifiers:
        logger.info(f"Cleaning identifier/system files in '{input_dir}'...")
        num_removed = clean_identifier_files(input_dir)
        logger.info(f"Removed {num_removed} identifier/system files.")
    else:
        logger.info("Skipping system file cleanup as configured.")

    # Generate mockups
    try:
        # Use the update_font_config function to update font settings
        config.update_font_config(
            title_font=title_font,
            subtitle_font=subtitle_font,
            title_max_size=title_font_size,
            subtitle_size=subtitle_font_size,
            subtitle_spacing=subtitle_spacing,
        )

        # Log the font settings being used
        if title_font:
            logger.info(f"Using custom title font: {title_font}")
        if subtitle_font:
            logger.info(f"Using custom subtitle font: {subtitle_font}")
        if title_font_size:
            logger.info(f"Using custom title font size: {title_font_size}")
        if subtitle_font_size:
            logger.info(f"Using custom subtitle font size: {subtitle_font_size}")
        if subtitle_spacing:
            logger.info(f"Using custom subtitle spacing: {subtitle_spacing}")

        return grid_mockup(
            input_dir_base=input_dir,
            title_override=title_override,
            create_video=create_video,
        )
    except Exception as e:
        logger.critical(f"A critical error occurred during mockup generation: {e}")
        return []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate mockups into 'mocks' subfolder within each input subfolder."
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        help="Path to the base directory containing subfolders of images (e.g., 'input'). Mockups will be saved inside these subfolders.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for all generated mockups.",
    )
    parser.add_argument(
        "--title_font",
        default=None,
        help="Font to use for the title text (e.g., Angelina, Clattering, MarkerFelt, Poppins)",
    )
    parser.add_argument(
        "--subtitle_font",
        default=None,
        help="Font to use for the subtitle text (e.g., MarkerFelt, Angelina, Clattering, Poppins)",
    )
    parser.add_argument(
        "--title_font_size",
        type=int,
        default=None,
        help="Maximum font size for the title text (default: 170)",
    )
    parser.add_argument(
        "--subtitle_font_size",
        type=int,
        default=None,
        help="Font size for the subtitle text (default: 70)",
    )

    args = parser.parse_args()

    logger.info(f"Starting mockup generation process (clipart.py invoked)...")
    logger.info(f"Input base directory: {args.input_dir}")
    logger.info(
        "Mockups will be saved into a 'mocks' subfolder within each processed input subfolder."
    )

    if args.title:
        logger.info(f"Using override title: {args.title}")

    process_clipart(
        args.input_dir,
        args.title,
        False,
        args.title_font if hasattr(args, "title_font") else None,
        args.subtitle_font if hasattr(args, "subtitle_font") else None,
        args.title_font_size if hasattr(args, "title_font_size") else None,
        args.subtitle_font_size if hasattr(args, "subtitle_font_size") else None,
        args.subtitle_spacing if hasattr(args, "subtitle_spacing") else None,
    )

    logger.info("Mockup generation process finished.")
