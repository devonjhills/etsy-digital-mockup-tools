"""
Main module for clipart processing.
"""

import os
import sys
import glob
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image

from utils.common import (
    setup_logging,
    ensure_dir_exists,
    clean_identifier_files,
    safe_load_image,
)
from clipart import config
from clipart.resize import process_images
from clipart.processing.collage import create_collage_layout
from clipart.processing.grid import create_2x2_grid, apply_watermark
from clipart.processing.transparency import create_transparency_demo
from clipart.processing.title import add_title_bar_and_text
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

        # Find input images
        try:
            input_image_paths = sorted(
                glob.glob(os.path.join(input_folder_path, "*.png"))
            )
        except Exception as e:
            logger.error(
                f"Error searching for PNG files in {input_folder_path}: {e}. Skipping folder."
            )
            continue

        num_images = len(input_image_paths)
        if not input_image_paths:
            logger.warning(
                f"No PNG images found in {input_folder_path}. Skipping mockup generation."
            )
            continue

        logger.info(f"Found {num_images} PNG images for mockup generation.")

        # 1. Main Mockup Generation
        try:
            logger.info("--- Generating Main Mockup ---")
            subtitle_bottom_text = f"{num_images} clip arts • 300 DPI • Transparent PNG"

            # Create title style arguments with only the parameters that add_title_bar_and_text accepts
            title_style_args = {
                "title_font_name": "Angelina",  # Explicitly set to Angelina font
                "subtitle_font_name": "MarkerFelt",
                "title_max_font_size": config.TITLE_MAX_FONT_SIZE,
                "title_min_font_size": config.TITLE_MIN_FONT_SIZE,
                "title_line_spacing": config.TITLE_LINE_SPACING,
                "title_font_step": config.TITLE_FONT_STEP,
                "title_max_lines": config.TITLE_MAX_LINES,
                "title_padding_x": config.TITLE_PADDING_X,
                "subtitle_spacing": config.SUBTITLE_SPACING,
                "subtitle_font_size": config.SUBTITLE_FONT_SIZE,
                "text_color": config.TITLE_TEXT_COLOR,
                "subtitle_text_color": config.SUBTITLE_TEXT_COLOR,
                "backdrop_padding_x": config.TITLE_BACKDROP_PADDING_X,
                "backdrop_padding_y": config.TITLE_BACKDROP_PADDING_Y,
                "backdrop_corner_radius": config.TITLE_BACKDROP_CORNER_RADIUS,
                "backdrop_opacity": config.TITLE_BACKDROP_OPACITY,
                "border_width": config.TITLE_BACKDROP_BORDER_WIDTH,
                "border_color": config.TITLE_BACKDROP_BORDER_COLOR,
                # No vertical_adjustment parameter needed anymore
            }

            # Calculate title bounds
            logger.info("Calculating title bounds...")
            dummy_layer = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
            _, title_backdrop_bounds = add_title_bar_and_text(
                image=dummy_layer,
                background_image=canvas_bg_main,
                title=title,
                subtitle_top=getattr(config, "SUBTITLE_TEXT_TOP", ""),
                subtitle_bottom=subtitle_bottom_text,
                **title_style_args,
            )

            if not title_backdrop_bounds:
                logger.warning(
                    "Title bounds calculation failed. Collage placement might be affected."
                )

            # Create the title layer
            logger.info("Creating title layer...")
            title_layer_canvas = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
            image_with_title_block_only, _ = add_title_bar_and_text(
                image=title_layer_canvas,
                background_image=canvas_bg_main,
                title=title,
                subtitle_top=getattr(config, "SUBTITLE_TEXT_TOP", ""),
                subtitle_bottom=subtitle_bottom_text,
                **title_style_args,
            )

            if not image_with_title_block_only:
                logger.warning(
                    "Failed to generate title block layer. Using blank layer."
                )
                image_with_title_block_only = Image.new(
                    "RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0)
                )

            # Create collage layout
            output_main_filename = os.path.join(
                mocks_output_folder_path, "01_main_collage_layout.png"
            )
            logger.info("Creating collage layout...")
            collage_style_args = getattr(config, "COLLAGE_STYLE_ARGS", {})
            layout_with_images = create_collage_layout(
                image_paths=input_image_paths,
                canvas=canvas_bg_main.copy(),
                title_backdrop_bounds=title_backdrop_bounds,
                **collage_style_args,
            )

            # Composite title onto collage
            logger.info("Compositing title block...")
            final_main_mockup = Image.alpha_composite(
                layout_with_images.convert("RGBA"),
                image_with_title_block_only.convert("RGBA"),
            )

            # Save main mockup
            try:
                final_main_mockup.save(output_main_filename, "PNG")
                logger.info(
                    f"Saved: {os.path.relpath(output_main_filename, input_dir_base)}"
                )
                output_filenames_current_folder.append(output_main_filename)
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
    input_dir: str, title_override: str = None, create_video: bool = False
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

    args = parser.parse_args()

    logger.info(f"Starting mockup generation process (clipart.py invoked)...")
    logger.info(f"Input base directory: {args.input_dir}")
    logger.info(
        "Mockups will be saved into a 'mocks' subfolder within each processed input subfolder."
    )

    if args.title:
        logger.info(f"Using override title: {args.title}")

    process_clipart(args.input_dir, args.title)

    logger.info("Mockup generation process finished.")
