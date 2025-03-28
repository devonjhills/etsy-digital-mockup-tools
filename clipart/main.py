# clipart/main.py
import os
import glob
import traceback
from typing import List
from PIL import Image  # Needed for Image.alpha_composite

# Import modules using relative imports
from . import config
from . import utils
from . import image_processing
from . import video_processing


def grid_mockup(input_folder: str, title: str) -> List[str]:
    """
    Generates various mockups for images in the input folder.
    Saves results to the configured output directory.
    Returns a list of paths to the generated mockup files.
    """
    subfolder_name = os.path.basename(input_folder)
    output_folder = os.path.join(config.OUTPUT_DIR_BASE, subfolder_name)

    print(f"Outputting mockups to: {output_folder}")
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_folder}: {e}")
        return []

    output_filenames = []
    video_source_filenames = []

    # --- Load Backgrounds ---
    canvas_bg_main = utils.safe_load_image(config.CANVAS_PATH, "RGBA")
    if canvas_bg_main:
        try:
            canvas_bg_main = canvas_bg_main.resize(
                config.OUTPUT_SIZE, Image.Resampling.LANCZOS
            )
        except Exception as e:
            print(f"Error resizing main canvas: {e}.")
            canvas_bg_main = None
    if not canvas_bg_main:
        canvas_bg_main = utils.generate_background(config.OUTPUT_SIZE).convert("RGBA")

    canvas_bg_2x2 = utils.safe_load_image(config.CANVAS_PATH, "RGBA")
    if canvas_bg_2x2:
        try:
            canvas_bg_2x2 = canvas_bg_2x2.resize(
                config.GRID_2x2_SIZE, Image.Resampling.LANCZOS
            )
        except Exception as e:
            print(f"Error resizing 2x2 canvas: {e}.")
            canvas_bg_2x2 = None
    if not canvas_bg_2x2:
        canvas_bg_2x2 = utils.generate_background(config.GRID_2x2_SIZE).convert("RGBA")

    # --- Find Input Images ---
    input_image_paths = sorted(glob.glob(os.path.join(input_folder, "*.png")))
    num_images = len(input_image_paths)
    if not input_image_paths:
        print(f"Error: No PNG images found in {input_folder}")
        return []
    print(f"Found {num_images} PNG images in {input_folder}")

    # --- 1. Main Mockup Generation --- ## UPDATED SECTION ##
    print(f"\n--- Generating Main Mockup ---")

    if not canvas_bg_main:
        print(
            "Skipping main mockup generation: Failed background canvas loading/generation."
        )
    else:
        subtitle_bottom_text = f"{num_images} clip arts • 300 DPI • Transparent PNG"

        # --- Determine Title Backdrop Bounds ONCE (Needed for avoidance) ---
        print("  Calculating title backdrop bounds...")
        dummy_layer = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
        _, title_backdrop_bounds = image_processing.add_title_bar_and_text(
            image=dummy_layer,
            title=title,
            subtitle_top=config.SUBTITLE_TEXT_TOP,
            subtitle_bottom=subtitle_bottom_text,
            font_name=config.DEFAULT_TITLE_FONT,
            subtitle_font_name=config.DEFAULT_SUBTITLE_FONT,
            subtitle_font_size=config.SUBTITLE_FONT_SIZE,
            subtitle_text_color=config.SUBTITLE_TEXT_COLOR,
            subtitle_spacing=config.SUBTITLE_SPACING,
            bar_opacity=config.TITLE_BAR_OPACITY,
            text_color=config.TITLE_TEXT_COLOR,
            padding_x=config.TITLE_PADDING_X,
            max_font_size=config.TITLE_MAX_FONT_SIZE,
            min_font_size=config.TITLE_MIN_FONT_SIZE,
            line_spacing=config.TITLE_LINE_SPACING,
            font_step=config.TITLE_FONT_STEP,
            max_lines=config.TITLE_MAX_LINES,
            bar_color=config.TITLE_BAR_COLOR,
            bar_gradient=config.TITLE_BAR_GRADIENT,
            backdrop_padding_x=config.TITLE_BACKDROP_PADDING_X,
            backdrop_padding_y=config.TITLE_BACKDROP_PADDING_Y,
            backdrop_corner_radius=config.TITLE_BACKDROP_CORNER_RADIUS,
        )
        if title_backdrop_bounds:
            print(f"  Title Backdrop Bounds (calculated): {title_backdrop_bounds}")
        else:
            print(
                "  Warning: Title backdrop bounds calculation failed. Collage avoidance might be affected."
            )

        # --- Create Title Block Layer ONCE ---
        print("  Creating title block layer...")
        title_layer_canvas = Image.new("RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0))
        image_with_title_block_only, _ = image_processing.add_title_bar_and_text(
            image=title_layer_canvas,
            title=title,
            subtitle_top=config.SUBTITLE_TEXT_TOP,
            subtitle_bottom=subtitle_bottom_text,
            font_name=config.DEFAULT_TITLE_FONT,
            subtitle_font_name=config.DEFAULT_SUBTITLE_FONT,
            subtitle_font_size=config.SUBTITLE_FONT_SIZE,
            subtitle_text_color=config.SUBTITLE_TEXT_COLOR,
            subtitle_spacing=config.SUBTITLE_SPACING,
            bar_opacity=config.TITLE_BAR_OPACITY,
            text_color=config.TITLE_TEXT_COLOR,
            padding_x=config.TITLE_PADDING_X,
            max_font_size=config.TITLE_MAX_FONT_SIZE,
            min_font_size=config.TITLE_MIN_FONT_SIZE,
            line_spacing=config.TITLE_LINE_SPACING,
            font_step=config.TITLE_FONT_STEP,
            max_lines=config.TITLE_MAX_LINES,
            bar_color=config.TITLE_BAR_COLOR,
            bar_gradient=config.TITLE_BAR_GRADIENT,
            backdrop_padding_x=config.TITLE_BACKDROP_PADDING_X,
            backdrop_padding_y=config.TITLE_BACKDROP_PADDING_Y,
            backdrop_corner_radius=config.TITLE_BACKDROP_CORNER_RADIUS,
        )
        if not image_with_title_block_only:
            print(
                "Warn: Failed to generate title block layer. Main mockup will lack title."
            )
            image_with_title_block_only = Image.new(
                "RGBA", config.OUTPUT_SIZE, (0, 0, 0, 0)
            )

        # --- Define the Output Filename (Consistent Name) ---
        output_main_filename = os.path.join(
            output_folder, "01_main_collage_layout.png"  # Use this name consistently
        )

        # --- Create Collage Image Layout --- ## CONSISTENT CALL ##
        print("  Creating collage image layout...")
        # Call the single layout function
        layout_with_images = image_processing.create_collage_layout(
            image_paths=input_image_paths,
            canvas=canvas_bg_main.copy(),  # Start fresh
            title_backdrop_bounds=title_backdrop_bounds,  # Pass the calculated bounds
            # Uses parameters from config.py (COLLAGE_*)
        )

        # --- Composite Title onto Layout ---
        print("  Compositing title block onto layout...")
        final_main_mockup = Image.alpha_composite(
            layout_with_images.convert("RGBA"),
            image_with_title_block_only.convert("RGBA"),
        )

        # --- Save The Main Mockup ---
        try:
            final_main_mockup.save(output_main_filename, "PNG")
            print(f"Saved: {output_main_filename}")
            output_filenames.append(output_main_filename)
        except Exception as e:
            print(f"Error saving main mockup {output_main_filename}: {e}")
            traceback.print_exc()

    # --- 2. 2x2 Grids ---
    # This section correctly applies the watermark ONLY to the 2x2 grids
    print(f"\n--- Generating 2x2 Grid Mockups ---")
    if canvas_bg_2x2:
        print(f"Canvas size: {config.GRID_2x2_SIZE[0]}x{config.GRID_2x2_SIZE[1]}")
        grid_count = 0
        for i in range(0, num_images, 4):
            batch_paths = input_image_paths[i : i + 4]
            if not batch_paths:
                continue
            grid_count += 1
            print(
                f"  Creating grid {grid_count} (images {i+1}-{i+len(batch_paths)})..."
            )
            mockup_2x2 = image_processing.create_2x2_grid(
                input_image_paths=batch_paths,
                canvas_bg_image=canvas_bg_2x2.copy(),
                grid_size=config.GRID_2x2_SIZE,
                padding=config.CELL_PADDING,
            )
            # Watermark is applied HERE
            mockup_2x2_watermarked = image_processing.apply_watermark(mockup_2x2)
            output_filename = os.path.join(
                output_folder, f"{grid_count+1:02d}_grid_mockup.png"
            )
            try:
                # The watermarked version is saved
                mockup_2x2_watermarked.save(output_filename, "PNG")
                print(f"Saved: {output_filename}")
                output_filenames.append(output_filename)
                video_source_filenames.append(
                    output_filename
                )  # Video uses watermarked grids
            except Exception as e:
                print(f"Error saving 2x2 mockup {output_filename}: {e}")
                traceback.print_exc()
    else:
        print("Skipping 2x2 grids: Failed background generation.")

    # --- 3. Transparency Demo ---
    print(f"\n--- Generating Transparency Demo ---")
    if input_image_paths:
        first_image_path = input_image_paths[0]
        print(f"Using image: {os.path.basename(first_image_path)}")

        trans_demo = image_processing.create_transparency_demo(first_image_path)
        if trans_demo:
            output_trans_demo = os.path.join(
                output_folder, f"{len(output_filenames) + 1:02d}_transparency_demo.png"
            )
            try:
                trans_demo.save(output_trans_demo, "PNG")
                print(f"Saved: {output_trans_demo}")
                output_filenames.append(output_trans_demo)
            except Exception as e:
                print(f"Error saving transparency demo {output_trans_demo}: {e}")
                traceback.print_exc()
        else:
            print(f"Failed to create transparency demo for {first_image_path}.")
    else:
        print("Skipping transparency demo: No input images.")

    # --- 4. Video ---
    CREATE_VIDEO = True
    print(f"\n--- Generating Video Mockup ---")
    if CREATE_VIDEO and len(video_source_filenames) >= 1:
        print(f"Using {len(video_source_filenames)} source frames for video.")
        next_seq = len(output_filenames) + 1
        video_path = os.path.join(output_folder, f"{next_seq:02d}_mockup_video.mp4")
        try:
            if "video_processing" in globals():
                video_processing.create_video_mockup(
                    image_paths=video_source_filenames,
                    output_path=video_path,
                    target_size=config.VIDEO_TARGET_SIZE,
                    fps=config.VIDEO_FPS,
                    num_transition_frames=config.VIDEO_TRANSITION_FRAMES,
                    display_frames=config.VIDEO_DISPLAY_FRAMES,
                )
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    output_filenames.append(video_path)
            else:
                print("Skipping video: video_processing module not available.")
        except Exception as e:
            print(f"Error during video creation call: {e}")
            traceback.print_exc()
    elif not CREATE_VIDEO:
        print("Skipping video generation as configured.")
    else:
        print("Skipping video generation: No source grid images were generated.")

    return output_filenames


# --- Script Execution Entry Point ---
if __name__ == "__main__":
    # (Keep the existing __main__ block)
    print("Starting mockup generation process...")
    print(f"Project Root Directory: {config.PROJECT_ROOT}")
    print(f"Input Directory: {config.INPUT_DIR}")
    print(f"Base Output Directory: {config.OUTPUT_DIR_BASE}")
    print(f"Assets Directory: {config.ASSETS_DIR}")

    processed_count = 0

    if config.DELETE_IDENTIFIERS_ON_START:
        print(f"\nCleaning identifier/system files in '{config.INPUT_DIR}'...")
        files_removed = 0
        try:
            for root, _, files in os.walk(config.INPUT_DIR):
                for file in files:
                    if file.endswith(".Identifier") or file == ".DS_Store":
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            files_removed += 1
                        except OSError as e:
                            print(f"Warn: Could not remove {file_path}: {e}")
            print(
                f"Removed {files_removed} files."
                if files_removed > 0
                else "No files to remove."
            )
        except Exception as e:
            print(f"Error during cleanup walk: {e}")

    try:
        if not os.path.isdir(config.INPUT_DIR):
            raise FileNotFoundError(f"Input dir not found: {config.INPUT_DIR}")
        subfolders = sorted(
            [f.name for f in os.scandir(config.INPUT_DIR) if f.is_dir()]
        )
    except Exception as e:
        print(f"Error accessing input directory {config.INPUT_DIR}: {e}")
        subfolders = []

    if not subfolders:
        print(f"\nNo subdirectories found in '{config.INPUT_DIR}'. Nothing to process.")
    else:
        print(f"\nFound subfolders: {', '.join(subfolders)}")
        for subfolder_name in subfolders:
            subfolder_path = os.path.join(config.INPUT_DIR, subfolder_name)
            title = " ".join(
                word.capitalize()
                for word in subfolder_name.replace("_", " ").replace("-", " ").split()
                if word
            )
            print(f"\n{'='*20} Processing: {subfolder_name} {'='*20}")
            print(f"      Path: {subfolder_path} | Title: '{title}'")
            try:
                generated_files = grid_mockup(subfolder_path, title)
                if generated_files:
                    print(f"Generated {len(generated_files)} mockup file(s).")
                else:
                    print(f"Warning: No files generated for '{subfolder_name}'.")
                processed_count += 1
            except Exception as e:
                print(f"\n!!! Critical Error processing folder '{subfolder_name}' !!!")
                print(f"Error Message: {e}")
                traceback.print_exc()
                print(f"!!! Skipping folder '{subfolder_name}' !!!")

    print(f"\n--- Mockup Generation Complete! ---")
    print(f"Processed {processed_count} subfolder(s) from '{config.INPUT_DIR}'.")
    print(f"Outputs saved under '{config.OUTPUT_DIR_BASE}'.")
