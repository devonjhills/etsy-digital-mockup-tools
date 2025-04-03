# clipart.py
import os
import glob
from typing import List, Optional  # Added Optional
from PIL import Image
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Import modules using relative imports
try:
    from . import config
    from . import utils
    from . import image_processing
except ImportError as e:
    log.critical(
        f"Failed relative import: {e}. Ensure scripts are run correctly (e.g., python -m clipart.clipart) and dependent files exist.",
        exc_info=True,
    )
    raise

# Conditionally import video processing
try:
    from . import video_processing

    VIDEO_AVAILABLE = True
except ImportError:
    log.warning(
        "video_processing module not found or failed to import. Video generation disabled."
    )
    VIDEO_AVAILABLE = False


# --- Modified grid_mockup Function ---
def grid_mockup(input_dir_base: str, title_override: str = None) -> List[str]:
    """
    Generates various mockups for images found in subfolders of input_dir_base.
    Saves results into a 'mocks' subfolder WITHIN each processed input subfolder.
    Returns a list of paths to all generated mockup files across all folders.
    """
    generated_files_all_folders = []

    # --- Verify Input Base Directory ---
    if not os.path.isdir(input_dir_base):
        log.critical(
            f"Input directory base not found or not a directory: {input_dir_base}"
        )
        return []

    # --- Find Subfolders ---
    try:
        subfolders = sorted(
            [
                f.path
                for f in os.scandir(input_dir_base)
                if f.is_dir() and not f.name.startswith(".") and f.name != "mocks"
            ]
        )
    except OSError as e:
        log.critical(f"Error scanning input directory {input_dir_base}: {e}")
        return []

    if not subfolders:
        log.warning(
            f"No valid subdirectories (excluding 'mocks') found in '{input_dir_base}'. Nothing to process."
        )
        return []

    log.info(
        f"Found {len(subfolders)} potential subfolder(s) in '{input_dir_base}' to process."
    )

    # --- Process Each Subfolder ---
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

        # --- Define Output Path: 'mocks' folder inside the input subfolder ---
        mocks_output_folder_path = os.path.join(input_folder_path, "mocks")

        log.info(
            f"\n{'=' * 15} Processing Folder {index}/{len(subfolders)}: {subfolder_name} {'=' * 15}"
        )
        log.info(f"  Input Path: {input_folder_path}")
        log.info(f"  Outputting Mocks To: {mocks_output_folder_path}")
        log.info(f"  Title: '{title}'")

        # Create the 'mocks' output directory for the current subfolder
        try:
            os.makedirs(mocks_output_folder_path, exist_ok=True)
        except OSError as e:
            log.error(
                f"Error creating mocks output directory {mocks_output_folder_path}: {e}. Skipping folder."
            )
            continue

        # Initialize lists for this specific folder
        output_filenames_current_folder = []
        video_source_filenames = []

        # --- Load Backgrounds (Crucial for the new title function) ---
        canvas_bg_main: Optional[Image.Image] = None
        canvas_bg_2x2: Optional[Image.Image] = None
        try:
            # Load main background for collage AND title backdrop
            canvas_bg_main = utils.safe_load_image(config.CANVAS_PATH, "RGBA")
            if canvas_bg_main:
                canvas_bg_main = canvas_bg_main.resize(
                    config.OUTPUT_SIZE, Image.Resampling.LANCZOS
                )
            else:
                log.warning(
                    f"Failed to load main canvas '{config.CANVAS_PATH}' required for collage and title. Generating fallback."
                )
                canvas_bg_main = utils.generate_background(config.OUTPUT_SIZE).convert(
                    "RGBA"
                )

            # Load background for 2x2 grid (can be the same source, different size)
            canvas_bg_2x2 = utils.safe_load_image(config.CANVAS_PATH, "RGBA")
            if canvas_bg_2x2:
                canvas_bg_2x2 = canvas_bg_2x2.resize(
                    config.GRID_2x2_SIZE, Image.Resampling.LANCZOS
                )
            else:
                log.warning(
                    f"Failed to load 2x2 canvas '{config.CANVAS_PATH}'. Generating fallback."
                )
                canvas_bg_2x2 = utils.generate_background(config.GRID_2x2_SIZE).convert(
                    "RGBA"
                )
        except AttributeError as e:
            log.error(
                f"Error accessing canvas configuration (config.CANVAS_PATH?): {e}. Using fallbacks.",
                exc_info=True,
            )
            if not canvas_bg_main:
                canvas_bg_main = utils.generate_background(config.OUTPUT_SIZE).convert(
                    "RGBA"
                )
            if not canvas_bg_2x2:
                canvas_bg_2x2 = utils.generate_background(config.GRID_2x2_SIZE).convert(
                    "RGBA"
                )
        except Exception as e:
            log.error(
                f"Unexpected error loading/resizing canvases: {e}. Using fallbacks.",
                exc_info=True,
            )
            if not canvas_bg_main:
                canvas_bg_main = utils.generate_background(config.OUTPUT_SIZE).convert(
                    "RGBA"
                )
            if not canvas_bg_2x2:
                canvas_bg_2x2 = utils.generate_background(config.GRID_2x2_SIZE).convert(
                    "RGBA"
                )

        # --- Find Input Images ---
        try:
            input_image_paths = sorted(
                glob.glob(os.path.join(input_folder_path, "*.png"))
            )
        except Exception as e:
            log.error(
                f"Error searching for PNG files in {input_folder_path}: {e}. Skipping folder.",
                exc_info=True,
            )
            continue

        num_images = len(input_image_paths)
        if not input_image_paths:
            log.warning(
                f"No PNG images found in {input_folder_path}. Skipping mockup generation."
            )
            continue
        log.info(f"Found {num_images} PNG images for mockup generation.")

        # --- 1. Main Mockup Generation ---
        try:
            log.info("--- Generating Main Mockup ---")
            subtitle_bottom_text = f"{num_images} clip arts • 300 DPI • Transparent PNG"

            # Get title style arguments (font, padding, etc.) - color args will be ignored by the new function
            title_style_args = getattr(config, "TITLE_STYLE_ARGS", {})

            # --- Calculate title bounds using the NEW function signature ---
            log.info("Calculating title bounds...")
            dummy_layer = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
            _, title_backdrop_bounds = image_processing.add_title_bar_and_text(
                image=dummy_layer,
                background_image=canvas_bg_main,  # *** NEW: Pass background image ***
                title=title,
                subtitle_top=getattr(config, "SUBTITLE_TEXT_TOP", ""),
                subtitle_bottom=subtitle_bottom_text,
                # image_for_color_analysis=centerpiece_for_analysis, # Removed
                # use_dynamic_colors=False, # Removed
                **title_style_args,  # Pass remaining style args (font, padding etc)
            )
            if not title_backdrop_bounds:
                log.warning(
                    "Title bounds calculation failed. Collage placement might be affected."
                )

            # --- Create the title layer using the NEW function signature ---
            log.info("Creating title layer...")
            title_layer_canvas = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
            image_with_title_block_only, _ = image_processing.add_title_bar_and_text(
                image=title_layer_canvas,
                background_image=canvas_bg_main,  # *** NEW: Pass background image ***
                title=title,
                subtitle_top=getattr(config, "SUBTITLE_TEXT_TOP", ""),
                subtitle_bottom=subtitle_bottom_text,
                # image_for_color_analysis=centerpiece_for_analysis, # Removed
                # use_dynamic_colors=False, # Removed
                **title_style_args,
            )
            if not image_with_title_block_only:
                log.warning("Failed to generate title block layer. Using blank layer.")
                image_with_title_block_only = Image.new(
                    "RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0)
                )

            # --- Create Collage Layout (Needs title bounds for avoidance) ---
            output_main_filename = os.path.join(
                mocks_output_folder_path, "01_main_collage_layout.png"
            )
            log.info("Creating collage layout...")
            collage_style_args = getattr(config, "COLLAGE_STYLE_ARGS", {})
            layout_with_images = image_processing.create_collage_layout(
                image_paths=input_image_paths,
                canvas=canvas_bg_main.copy(),  # Use the loaded main background
                title_backdrop_bounds=title_backdrop_bounds,  # Pass calculated bounds
                **collage_style_args,
            )

            # --- Composite Title onto Collage ---
            log.info("Compositing title block...")
            # Ensure both layers are RGBA for alpha_composite
            final_main_mockup = Image.alpha_composite(
                layout_with_images.convert("RGBA"),
                image_with_title_block_only.convert("RGBA"),
            )

            # --- Save Main Mockup ---
            try:
                final_main_mockup.save(output_main_filename, "PNG")
                log.info(
                    f"Saved: {os.path.relpath(output_main_filename, input_dir_base)}"
                )
                output_filenames_current_folder.append(output_main_filename)
            except Exception as e:
                log.error(
                    f"Error saving main mockup {output_main_filename}: {e}",
                    exc_info=True,
                )

        except Exception as e:
            log.error(
                f"Error during main mockup generation for {subfolder_name}: {e}",
                exc_info=True,
            )

        # --- 2. 2x2 Grid Mockups ---
        # (No changes needed here as it doesn't use the modified title function)
        try:
            log.info("--- Generating 2x2 Grid Mockups ---")
            if canvas_bg_2x2:
                grid_count = 0
                for i in range(0, num_images, 4):
                    batch_paths = input_image_paths[i : i + 4]
                    if not batch_paths:
                        continue
                    grid_count += 1
                    log.info(
                        f"Creating grid {grid_count} (images {i + 1}-{i + len(batch_paths)})..."
                    )
                    mockup_2x2 = image_processing.create_2x2_grid(
                        input_image_paths=batch_paths,
                        canvas_bg_image=canvas_bg_2x2.copy(),
                        grid_size=config.GRID_2x2_SIZE,
                        padding=config.CELL_PADDING,
                    )
                    mockup_2x2_watermarked = image_processing.apply_watermark(
                        mockup_2x2
                    )

                    output_filename = os.path.join(
                        mocks_output_folder_path,
                        f"{grid_count + 1:02d}_grid_mockup.png",
                    )
                    try:
                        mockup_2x2_watermarked.save(output_filename, "PNG")
                        log.info(
                            f"Saved: {os.path.relpath(output_filename, input_dir_base)}"
                        )
                        output_filenames_current_folder.append(output_filename)
                        video_source_filenames.append(output_filename)
                    except Exception as e:
                        log.error(
                            f"Error saving 2x2 mockup {output_filename}: {e}",
                            exc_info=True,
                        )
            else:
                log.warning(
                    "Skipping 2x2 grids: Background canvas for grids unavailable."
                )
        except Exception as e:
            log.error(
                f"Error during 2x2 grid generation for {subfolder_name}: {e}",
                exc_info=True,
            )

        # --- 3. Transparency Demo ---
        # (No changes needed here)
        try:
            log.info("--- Generating Transparency Demo ---")
            if input_image_paths:
                first_image_path = input_image_paths[0]
                log.info(f"Using image: {os.path.basename(first_image_path)}")
                trans_demo = image_processing.create_transparency_demo(first_image_path)
                if trans_demo:
                    output_trans_demo = os.path.join(
                        mocks_output_folder_path,
                        f"{len(output_filenames_current_folder) + 1:02d}_transparency_demo.png",
                    )
                    try:
                        trans_demo.save(output_trans_demo, "PNG")
                        log.info(
                            f"Saved: {os.path.relpath(output_trans_demo, input_dir_base)}"
                        )
                        output_filenames_current_folder.append(output_trans_demo)
                    except Exception as e:
                        log.error(
                            f"Error saving transparency demo {output_trans_demo}: {e}",
                            exc_info=True,
                        )
                else:
                    log.warning(
                        f"Failed to create transparency demo for {first_image_path}."
                    )
            else:
                log.warning("Skipping transparency demo: No input images found.")
        except Exception as e:
            log.error(
                f"Error during transparency demo generation for {subfolder_name}: {e}",
                exc_info=True,
            )

        # --- 4. Video Generation ---
        # (No changes needed here)
        try:
            log.info("--- Generating Video Mockup ---")
            create_video_flag = getattr(config, "CREATE_VIDEO", False)
            if create_video_flag and VIDEO_AVAILABLE and video_source_filenames:
                log.info(
                    f"Using {len(video_source_filenames)} source frames for video."
                )
                video_path = os.path.join(
                    mocks_output_folder_path,
                    f"{len(output_filenames_current_folder) + 1:02d}_mockup_video.mp4",
                )
                try:
                    video_args = getattr(config, "VIDEO_ARGS", {})
                    video_processing.create_video_mockup(
                        image_paths=video_source_filenames,
                        output_path=video_path,
                        **video_args,
                    )
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                        output_filenames_current_folder.append(video_path)
                        log.info(
                            f"Saved: {os.path.relpath(video_path, input_dir_base)}"
                        )
                    else:
                        log.warning(
                            f"Video file {video_path} was not created or is empty."
                        )
                except Exception as e:
                    log.error(f"Error during video creation: {e}", exc_info=True)
            elif not create_video_flag:
                log.info("Skipping video generation as configured.")
            elif not VIDEO_AVAILABLE:
                log.info("Skipping video: video_processing module unavailable.")
            else:
                log.info("Skipping video: No source grid images generated.")
        except Exception as e:
            log.error(
                f"Error during video generation logic for {subfolder_name}: {e}",
                exc_info=True,
            )

        # Add files generated for this folder to the overall list
        generated_files_all_folders.extend(output_filenames_current_folder)
        log.info(
            f"Finished processing folder '{subfolder_name}'. Generated {len(output_filenames_current_folder)} file(s) in 'mocks' subfolder."
        )
        # End of loop for one subfolder

    log.info(f"\n--- Mockup Generation Complete for all folders ---")
    log.info(f"Processed {len(subfolders)} subfolder(s) from '{input_dir_base}'.")
    log.info(f"Outputs saved into 'mocks' subdirectories within each processed folder.")
    return generated_files_all_folders


def clean_identifier_files(input_dir: str) -> None:
    """Removes common identifier and system files from the specified directory and subdirectories."""
    # (No changes needed here)
    files_removed = 0
    files_to_remove = {".DS_Store", "Thumbs.db", "desktop.ini"}
    extensions_to_remove = (".Identifier", ".identifier")

    log.debug(f"Scanning for system files in {input_dir}...")
    try:
        for root, dirs, files in os.walk(input_dir):
            dirs[:] = [
                d for d in dirs if d not in {"mocks", "zipped", "temp_zip_creation"}
            ]
            for file in files:
                remove_file = False
                if file in files_to_remove:
                    remove_file = True
                else:
                    for ext in extensions_to_remove:
                        if file.endswith(ext):
                            remove_file = True
                            break
                if remove_file:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        log.debug(f"Removed system file: {file_path}")
                        files_removed += 1
                    except OSError as e:
                        log.warning(f"Could not remove {file_path}: {e}")
    except Exception as e:
        log.error(
            f"Error during system file cleanup scan in {input_dir}: {e}", exc_info=True
        )

    if files_removed:
        log.info(f"Removed {files_removed} identifier/system file(s) from {input_dir}.")
    else:
        log.info(f"No identifier/system files found to remove in {input_dir}.")


# --- Main execution block ---
if __name__ == "__main__":
    # (No changes needed here)
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
    cli_args = parser.parse_args()

    log.info(f"Starting mockup generation process (clipart.py invoked)...")
    log.info(f"Input base directory: {cli_args.input_dir}")
    log.info(
        "Mockups will be saved into a 'mocks' subfolder within each processed input subfolder."
    )
    if cli_args.title:
        log.info(f"Using override title: {cli_args.title}")

    if not os.path.isdir(cli_args.input_dir):
        log.critical(f"Input directory '{cli_args.input_dir}' not found. Exiting.")
    else:
        delete_identifiers = getattr(config, "DELETE_IDENTIFIERS_ON_START", False)
        if delete_identifiers:
            log.info(f"Cleaning identifier/system files in '{cli_args.input_dir}'...")
            clean_identifier_files(cli_args.input_dir)
        else:
            log.info("Skipping system file cleanup as configured.")

        try:
            grid_mockup(
                input_dir_base=cli_args.input_dir,
                title_override=cli_args.title,
            )
        except Exception as e:
            log.critical(
                f"A critical error occurred during mockup generation: {e}",
                exc_info=True,
            )

    log.info("Mockup generation process finished (clipart.py).")
