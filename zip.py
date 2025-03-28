# zip.py
import os
import zipfile
import shutil
from PIL import Image
import io
import argparse
import logging
import math  # For ceiling division

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)  # Use a specific logger


# --- Helper Functions (Compress, Verify Image, Verify Zip) ---
def compress_image(img_path, quality=85):
    """Compress an image with reduced quality but maintaining dimensions"""
    try:
        with Image.open(img_path) as img:
            img_format = img.format
            # Ensure PNGs are handled correctly for optimization, check mode for RGBA
            if img_format == "PNG" and img.mode != "RGBA":
                img = img.convert("RGBA")
            elif img_format == "JPEG" and img.mode != "RGB":
                img = img.convert("RGB")

            buffer = io.BytesIO()
            save_kwargs = {}
            if img_format == "JPEG":
                save_kwargs = {"quality": quality, "optimize": True}
            elif img_format == "PNG":
                save_kwargs = {"optimize": True}

            img.save(buffer, format=img_format, **save_kwargs)
            buffer.seek(0)  # Reset buffer position
            return buffer.getvalue()

    except Exception as e:
        log.error(f"Error compressing image {img_path}: {e}", exc_info=True)
        return None


def verify_image(img_path):
    """Verify that an image can be properly loaded"""
    try:
        with Image.open(img_path) as img:
            img.verify()  # Verify integrity
        with Image.open(img_path) as img:
            img.load()  # Load pixel data
        return True
    except FileNotFoundError:
        log.error(f"Verification failed: File not found {img_path}")
        return False
    except Exception as e:
        log.error(f"Error verifying image {img_path}: {e}", exc_info=True)
        return False


def verify_zip(zip_path):
    """Verify zip file integrity"""
    try:
        with zipfile.ZipFile(zip_path, "r") as zipf:
            bad_file = zipf.testzip()
            if bad_file:
                raise Exception(f"Zip file corrupted, bad file: {bad_file}")
        return True
    except FileNotFoundError:
        log.error(f"Verification failed: Zip file not found {zip_path}")
        return False
    except Exception as e:
        log.error(f"Error verifying zip {zip_path}: {e}", exc_info=True)
        return False


# --- Zip Creation Function ---
def create_zip_group(
    files_to_zip,  # List of filenames (relative to subfolder_path)
    subfolder_path,  # Absolute path to the source subfolder
    output_dir,  # Directory where the zip file should be created
    base_zip_name,  # Base name for the zip (e.g., "ocean_nursery")
    group_num=None,
    total_groups=None,
    compress_images=True,
    image_quality=80,
):
    """Helper function to create a single zip file with verification and compression"""
    valid_files_data = {}  # {filename: data_or_path}

    # Validate images and prepare data
    for filename in files_to_zip:
        img_path = os.path.join(subfolder_path, filename)
        # Ensure we are only dealing with files we intend to zip (redundant check here, main filter is earlier)
        if not os.path.isfile(img_path):
            log.warning(
                f"Item '{filename}' is not a file. Skipping during zip group creation."
            )
            continue
        if not verify_image(img_path):
            log.warning(f"Skipping invalid image during zip creation: {filename}")
            continue

        if compress_images:
            compressed_data = compress_image(img_path, image_quality)
            if compressed_data:
                valid_files_data[filename] = compressed_data
            else:
                log.warning(f"Compression failed for {filename}, using original.")
                valid_files_data[filename] = img_path  # Fallback: path
        else:
            valid_files_data[filename] = img_path  # Path

    if not valid_files_data:
        log.error(
            f"No valid images to zip for group {group_num or 'single'} of {base_zip_name}"
        )
        return None, 0  # Indicate failure

    # Create filename
    if group_num and total_groups:
        zip_filename = f"{base_zip_name}_part{group_num}of{total_groups}.zip"
    else:
        zip_filename = f"{base_zip_name}.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    # Create zip file
    try:
        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zipf:
            for filename, data_or_path in valid_files_data.items():
                arcname = (
                    filename  # Name inside the zip file should be just the filename
                )
                if isinstance(data_or_path, bytes):
                    zipf.writestr(arcname, data_or_path)
                else:  # It's a path to the original file
                    # Add the file from its original path, but name it just filename inside zip
                    zipf.write(data_or_path, arcname)

        # Verify zip after creation
        if not verify_zip(zip_path):
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise Exception(f"Failed verification for created zip file: {zip_filename}")

        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log.debug(
            f"Successfully created and verified: {zip_filename} ({zip_size_mb:.2f} MB)"
        )
        return zip_path, zip_size_mb

    except Exception as e:
        log.error(f"Failed to create zip file {zip_filename}: {e}", exc_info=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)  # Clean up failed attempt
        return None, 0  # Indicate failure


# --- Main Processing Function ---
def create_zip_files(source_base_folder, max_size_mb=20, image_quality=75):
    """
    Creates zip files containing ONLY the images directly within each subfolder
    found in source_base_folder. Tries 1 zip, then 3, then 4 based on max_size_mb.
    Assumes exactly 12 numbered images per subfolder for splitting.

    Args:
        source_base_folder (str): Path to the folder containing subfolders with images.
        max_size_mb (float): Maximum size in MB for a single zip file part.
        image_quality (int): Compression quality (1-100).

    Returns:
        dict: {subfolder_name: [list_of_final_zip_paths]}
    """
    if not os.path.isdir(source_base_folder):
        log.critical(
            f"Source folder not found or not a directory: {source_base_folder}"
        )
        return {}

    zip_files_created = {}
    log.info(f"Starting zip creation process in: {source_base_folder}")
    folders_to_ignore = {
        "mocks",
        "zipped",
        "temp_zip_creation",
    }  # Folders to explicitly ignore

    for item_name in os.listdir(source_base_folder):
        subfolder_path = os.path.join(source_base_folder, item_name)

        # --- Explicitly skip non-directories and ignored folder names ---
        if not os.path.isdir(subfolder_path):
            log.debug(f"Skipping non-directory item: {item_name}")
            continue
        if item_name in folders_to_ignore:
            log.debug(f"Skipping ignored directory: {item_name}")
            continue

        subfolder_name = (
            item_name  # Use the loop variable now we know it's a valid directory
        )
        log.info(f"Processing subfolder: {subfolder_name}")
        sanitized_name = subfolder_name.replace(" ", "_")
        # --- Output folders are INSIDE the subfolder being processed ---
        zipped_folder = os.path.join(subfolder_path, "zipped")
        temp_dir = os.path.join(zipped_folder, "temp_zip_creation")

        # Clean up/create output dirs
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(zipped_folder, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # --- Get and Sort Image Files ---
            # List items DIRECTLY inside the subfolder
            all_items_in_subfolder = os.listdir(subfolder_path)
            # Filter for FILES only and check extensions
            image_files_in_subfolder = [
                f_name
                for f_name in all_items_in_subfolder
                if os.path.isfile(
                    os.path.join(subfolder_path, f_name)
                )  # <<< Ensures it's a file, not a directory like 'mocks'
                and f_name.lower().endswith(
                    (".jpg", ".jpeg", ".png")
                )  # Add other formats if needed
            ]
            log.debug(f"Found potential image files: {image_files_in_subfolder}")

            # --- Sort files based on number in filename (name_X.ext) ---
            numbered_files = []
            for img_filename in image_files_in_subfolder:
                try:
                    name_part = os.path.splitext(img_filename)[0]
                    num = int(name_part.split("_")[-1])
                    numbered_files.append((num, img_filename))
                except (ValueError, IndexError):
                    log.warning(
                        f"File '{img_filename}' in '{subfolder_name}' does not match 'name_X.ext' convention. Skipping file for zipping."
                    )
                    continue  # Skip files that don't match the pattern for sorting/splitting

            # Sort by extracted number and get just the filenames
            numbered_files.sort(key=lambda x: x[0])
            sorted_files = [f for _, f in numbered_files]

            if not sorted_files:
                log.warning(
                    f"No valid, numbered image files found to zip in '{subfolder_name}'. Skipping zip creation."
                )
                continue

            # --- Check for exactly 12 files for splitting logic ---
            if len(sorted_files) != 12:
                log.warning(
                    f"Subfolder '{subfolder_name}' does not contain exactly 12 numbered image files ({len(sorted_files)} found). Standard splitting logic might not apply, but will attempt to zip."
                )
                # Decide behavior: skip, zip all, or error out?
                # Current logic proceeds, attempting a single zip, then potentially failing splits.
                # Let's proceed with attempting a single zip for non-12 counts.
                # Splitting logic below assumes 12, so it won't be triggered correctly otherwise.

            # --- Attempt 1: Single Zip ---
            log.info(f"[{subfolder_name}] Attempt 1: Creating single zip...")
            attempt1_zip_path, attempt1_size_mb = create_zip_group(
                sorted_files,
                subfolder_path,
                temp_dir,
                sanitized_name,
                compress_images=True,
                image_quality=image_quality,
            )

            # --- Handle Single Zip Result (and non-12 file case) ---
            if attempt1_zip_path and attempt1_size_mb <= max_size_mb:
                # Success with single zip (works for 12 files or fewer/more if size allows)
                final_path = os.path.join(
                    zipped_folder, os.path.basename(attempt1_zip_path)
                )
                shutil.move(attempt1_zip_path, final_path)
                log.info(
                    f"[{subfolder_name}] Success: Created single zip '{os.path.basename(final_path)}' ({attempt1_size_mb:.2f} MB)"
                )
                zip_files_created[subfolder_name] = [final_path]
                # If single zip worked, we are done with this folder, regardless of file count
                shutil.rmtree(temp_dir)  # Clean up temp dir early
                continue  # Move to next subfolder

            elif attempt1_zip_path:  # Single zip created but too large
                log.info(
                    f"[{subfolder_name}] Attempt 1 failed: Zip too large ({attempt1_size_mb:.2f} MB > {max_size_mb} MB)."
                )
                os.remove(attempt1_zip_path)
                # Only proceed to splitting attempts if we had exactly 12 files initially
                if len(sorted_files) != 12:
                    log.warning(
                        f"[{subfolder_name}] Cannot apply standard splitting logic as number of files is not 12. Zipping aborted."
                    )
                    shutil.rmtree(temp_dir)
                    continue  # Skip to next subfolder
            else:  # Failed to create single zip initially
                log.error(
                    f"[{subfolder_name}] Attempt 1 failed: Could not create initial zip. Zipping aborted."
                )
                shutil.rmtree(temp_dir)
                continue  # Skip to next subfolder

            # --- Splitting Logic (Only runs if Attempt 1 failed AND there were exactly 12 files) ---

            # --- Attempt 2: Three Zips (4 files each) ---
            log.info(f"[{subfolder_name}] Attempt 2: Trying 3 parts...")
            groups_3 = [sorted_files[0:4], sorted_files[4:8], sorted_files[8:12]]
            attempt2_paths = []  # Renamed from attempt3_paths
            attempt2_sizes = []  # Renamed from attempt3_sizes
            need_four_groups = False

            for i, group in enumerate(groups_3, 1):
                zip_path, zip_size = create_zip_group(
                    group,
                    subfolder_path,
                    temp_dir,
                    sanitized_name,
                    group_num=i,
                    total_groups=3,
                    compress_images=True,
                    image_quality=image_quality,
                )
                if zip_path and zip_size <= max_size_mb:
                    attempt2_paths.append(zip_path)
                    attempt2_sizes.append(zip_size)
                elif zip_path:  # Created, but too large
                    log.info(
                        f"[{subfolder_name}] Attempt 2 failed: Part {i} too large ({zip_size:.2f} MB > {max_size_mb} MB)."
                    )
                    need_four_groups = True
                    attempt2_paths.append(zip_path)  # Add path for cleanup
                    break
                else:  # Failed to create zip part
                    log.error(
                        f"[{subfolder_name}] Attempt 2 failed: Could not create part {i}."
                    )
                    need_four_groups = True
                    break

            if not need_four_groups:
                # Success with 3 zips! Move them.
                final_paths_3 = []
                for i, zip_path in enumerate(attempt2_paths):
                    final_path = os.path.join(zipped_folder, os.path.basename(zip_path))
                    shutil.move(zip_path, final_path)
                    log.info(
                        f"[{subfolder_name}] Success: Created part {i+1}/3 '{os.path.basename(final_path)}' ({attempt2_sizes[i]:.2f} MB)"
                    )
                    final_paths_3.append(final_path)
                zip_files_created[subfolder_name] = final_paths_3
                shutil.rmtree(temp_dir)  # Clean up temp dir
                continue  # Move to next subfolder
            else:
                # Cleanup failed 3-part attempt
                log.info(f"[{subfolder_name}] Cleaning up failed 3-part attempt...")
                for path in attempt2_paths:
                    if os.path.exists(path):
                        os.remove(path)

            # --- Attempt 3: Four Zips (3 files each) ---
            log.info(f"[{subfolder_name}] Attempt 3: Splitting into 4 parts...")
            groups_4 = [
                sorted_files[0:3],
                sorted_files[3:6],
                sorted_files[6:9],
                sorted_files[9:12],
            ]
            final_paths_4 = []
            success_4 = True

            for i, group in enumerate(groups_4, 1):
                # Create directly in final folder
                zip_path, zip_size = create_zip_group(
                    group,
                    subfolder_path,
                    zipped_folder,
                    sanitized_name,
                    group_num=i,
                    total_groups=4,
                    compress_images=True,
                    image_quality=image_quality,
                )
                if zip_path:  # We don't check size here, this is the last resort
                    log.info(
                        f"[{subfolder_name}] Success: Created part {i}/4 '{os.path.basename(zip_path)}' ({zip_size:.2f} MB)"
                    )
                    final_paths_4.append(zip_path)
                else:
                    log.error(
                        f"[{subfolder_name}] Attempt 3 failed: Could not create part {i}/4. Aborting for this subfolder."
                    )
                    success_4 = False
                    # Clean up any parts created so far for attempt 4
                    for path in final_paths_4:
                        if os.path.exists(path):
                            os.remove(path)
                    break

            if success_4:
                zip_files_created[subfolder_name] = final_paths_4
            # Else: error already logged

        except Exception as e:
            log.error(
                f"An unexpected error occurred processing subfolder '{subfolder_name}': {e}",
                exc_info=True,
            )
        finally:
            # Cleanup temp directory if it still exists
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    log.info("Zip creation process finished.")
    return zip_files_created


# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create zip archives containing images directly within subfolders, splitting if necessary."
    )
    parser.add_argument(
        "--source_folder",
        required=True,
        help="Path to the base folder containing the subfolders with images to zip (e.g., 'input').",
    )
    parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum size (MB) for each zip file part.",
    )
    parser.add_argument(
        "--image_quality",
        type=int,
        default=75,  # Adjusted default slightly lower
        choices=range(1, 101),
        metavar="[1-100]",
        help="Image compression quality (1-100, lower is smaller/lower quality).",
    )
    args = parser.parse_args()

    results = create_zip_files(
        source_base_folder=args.source_folder,
        max_size_mb=args.max_size_mb,
        image_quality=args.image_quality,
    )

    log.info("--- Zip Creation Summary ---")
    if results:
        for folder, zips in results.items():
            log.info(
                f"'{folder}': {len(zips)} zip(s) created -> {[os.path.basename(p) for p in zips]}"
            )
    else:
        log.info("No zip files were created.")
    log.info("--------------------------")
