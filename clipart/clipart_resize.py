# clipart_resize.py (Corrected Numerical Sorting)
import os
import sys
import re  # Import regex for number extraction
from PIL import Image
import argparse
import logging
import shutil

# --- Configure logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


# --- Helper Functions ---
def trim(im):
    """Remove empty space around an image with transparency"""
    try:
        im = im.convert("RGBA")
        bbox = im.getbbox()
        if bbox:
            return im.crop(bbox)
        log.warning(
            "Trim: Image appears to be empty or fully transparent, returning original."
        )
        return im
    except Exception as e:
        log.error(f"Error during trim: {e}", exc_info=True)
        return im


def try_remove(file_path):
    """Attempts to remove a file, logging errors."""
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            log.debug(f"Removed file: {file_path}")
            return True
        elif os.path.exists(file_path):
            log.warning(f"Path exists but is not a file, cannot remove: {file_path}")
            return False
        else:
            return True  # Nothing to remove
    except OSError as e:
        log.warning(f"Could not remove file {file_path}: {e}")
        return False
    except Exception as e:
        log.error(f"Unexpected error removing file {file_path}: {e}", exc_info=True)
        return False


# --- Main Processing Function ---
def process_images(input_folder_path, max_size):
    """
    Processes images within subfolders of input_folder_path.
    Converts to PNG, trims, resizes if needed, sets DPI, and renames files
    to 'safesubfoldername_sequentialindex.png' based on NUMERICAL order.

    Skipping: If ALL image files in a subfolder ALREADY have the correct
    target name format AND the sequence is complete (1 to N), that
    ENTIRE subfolder is skipped.

    Parameters:
        input_folder_path (str): Absolute path to the input folder containing subfolders.
        max_size (int): Maximum size for the longest edge while maintaining aspect ratio.
    """
    log.info(f"Starting image processing in: {input_folder_path}")
    if not os.path.isdir(input_folder_path):
        log.error(f"Input folder not found or not a directory: {input_folder_path}")
        sys.exit(f"Error: Input folder '{input_folder_path}' not found.")

    total_processed_count = 0
    total_skipped_folders = 0
    total_error_count = 0
    total_deleted_original_count = 0

    subfolders = [
        d
        for d in os.listdir(input_folder_path)
        if os.path.isdir(os.path.join(input_folder_path, d))
    ]

    for subfolder_name in subfolders:
        subfolder_path = os.path.join(input_folder_path, subfolder_name)
        log.info(f"--- Evaluating subfolder: {subfolder_name} ---")
        safe_subfolder_name = subfolder_name.replace(" ", "_").lower()

        # --- Get initial list of image files ---
        try:
            all_files = os.listdir(subfolder_path)
            image_files_found = [
                f
                for f in all_files
                if os.path.isfile(os.path.join(subfolder_path, f))
                and f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
        except OSError as e:
            log.error(f"Could not list files in {subfolder_path}: {e}")
            total_error_count += 1
            continue

        if not image_files_found:
            log.info(f"No compatible image files found in {subfolder_path}. Skipping.")
            continue

        # --- Parse filenames and sort NUMERICALLY ---
        parsed_files = []  # List of tuples: (numeric_index, original_filename)
        # Regex to find the number before the extension, anchored by underscore
        # Handles names like name_1.png, name_01.png, name_long_12.png
        name_pattern = re.compile(r"(.+)_(\d+)\.(png|jpg|jpeg)$", re.IGNORECASE)

        for filename in image_files_found:
            match = name_pattern.match(filename)
            if match:
                try:
                    # Extract base name (unused here but could be useful) and number
                    # base_name = match.group(1)
                    number = int(match.group(2))
                    parsed_files.append((number, filename))
                except (ValueError, IndexError):
                    log.warning(
                        f"Could not parse number from filename '{filename}'. Skipping file."
                    )
            else:
                log.warning(
                    f"Filename '{filename}' does not match expected 'name_number.ext' format. Skipping file."
                )

        if not parsed_files:
            log.warning(
                f"No files with parseable numbers found in {subfolder_name}. Skipping folder processing."
            )
            continue

        # Sort based on the extracted number (the first element of the tuple)
        parsed_files.sort(key=lambda item: item[0])
        log.debug(f"Numerically sorted files (number, name): {parsed_files}")

        # --- Simplified Skip Logic: Check if ALL files match the target sequential name ---
        all_files_correctly_named_and_sequential = True
        expected_count = len(parsed_files)
        for i, (original_number, original_filename) in enumerate(parsed_files, start=1):
            expected_target_name = f"{safe_subfolder_name}_{i}.png"
            # Check 1: Does the filename already match the expected sequential name?
            # Check 2: Does the original number match the expected sequence number? (Optional but good sanity check)
            if original_filename != expected_target_name:  # or original_number != i:
                log.info(
                    f"File '{original_filename}' (parsed number {original_number}) needs processing. Expected name based on sequence: '{expected_target_name}'."
                )
                all_files_correctly_named_and_sequential = False
                break  # No need to check further

        # --- Skip entire folder OR proceed to process files ---
        if all_files_correctly_named_and_sequential:
            log.info(
                f"Skipping subfolder '{subfolder_name}': All {expected_count} files already correctly named and sequential."
            )
            total_skipped_folders += 1
            continue
        else:
            log.info(
                f"Processing files within subfolder: {subfolder_name} (Renaming based on numerical order)"
            )
            files_processed_this_folder = 0
            files_deleted_this_folder = 0
            errors_this_folder = 0

            # Process each image file based on the NUMERICALLY sorted list
            for target_index, (original_number, original_filename) in enumerate(
                parsed_files, start=1
            ):
                original_path = os.path.join(subfolder_path, original_filename)
                # TARGET name is based on the sequential index from the sorted list
                target_name = f"{safe_subfolder_name}_{target_index}.png"
                target_path = os.path.join(subfolder_path, target_name)

                log.info(f"  Processing: '{original_filename}' -> '{target_name}'")
                try:
                    if not os.path.exists(original_path):
                        log.warning(
                            f"  Original file '{original_filename}' not found at start of processing loop. Skipping."
                        )
                        errors_this_folder += 1
                        continue

                    with Image.open(original_path) as img:
                        img = img.convert("RGBA")
                        img_trimmed = trim(img)
                        img = img_trimmed

                        if img is None or img.size == (0, 0):
                            log.warning(
                                f"  Skipping '{original_filename}' due to invalid size after trim."
                            )
                            errors_this_folder += 1
                            continue

                        width, height = img.size
                        needs_resize = width > max_size or height > max_size

                        if needs_resize:
                            if width > height:
                                new_width = max_size
                                new_height = int(height * (max_size / width))
                            else:
                                new_height = max_size
                                new_width = int(width * (max_size / height))
                            log.debug(
                                f"    Resizing from {width}x{height} to {new_width}x{new_height}"
                            )
                            img = img.resize(
                                (new_width, new_height), Image.Resampling.LANCZOS
                            )

                        img.info["dpi"] = (300, 300)

                        log.debug(f"    Saving to '{target_name}'...")
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        # Save BEFORE removing original, especially if overwriting target==original
                        img.save(target_path, format="PNG", dpi=(300, 300))

                        # Remove the original file ONLY if the path has changed
                        if target_path != original_path:
                            if try_remove(original_path):
                                files_deleted_this_folder += 1

                        files_processed_this_folder += 1

                except FileNotFoundError:
                    log.error(f"  File disappeared during processing: {original_path}")
                    errors_this_folder += 1
                except Exception as e:
                    log.error(f"  Error processing {original_path}: {e}", exc_info=True)
                    errors_this_folder += 1
            # --- End loop through sorted files ---

            log.info(
                f"  Finished processing {subfolder_name}: Processed={files_processed_this_folder}, Deleted originals={files_deleted_this_folder}, Errors={errors_this_folder}"
            )
            total_processed_count += files_processed_this_folder
            total_deleted_original_count += files_deleted_this_folder
            total_error_count += errors_this_folder

    # --- End loop through subfolders ---

    log.info("--- Image Processing Summary ---")
    log.info(f"  Subfolders skipped (already correct): {total_skipped_folders}")
    log.info(f"  Total files processed (opened/saved): {total_processed_count}")
    log.info(
        f"  Total original files deleted (due to rename): {total_deleted_original_count}"
    )
    log.info(f"  Total errors encountered: {total_error_count}")


# --- Main execution block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resize, trim, convert images to PNG format with standard sequential naming based on numerical sort."
    )
    parser.add_argument(
        "--input_folder",
        required=True,
        help="Path to the main input folder containing subfolders of images.",
    )
    parser.add_argument(
        "--max_size",
        type=int,
        default=1500,
        help="Maximum size (pixels) for the longest edge. Aspect ratio is preserved.",
    )
    args = parser.parse_args()

    process_images(args.input_folder, args.max_size)
