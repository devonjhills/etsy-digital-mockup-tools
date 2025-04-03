# zip.py
import os
import zipfile
import shutil
from PIL import Image
import io
import argparse
import logging
import math  # For ceiling division
import time  # For potential retry delays

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)  # Use a specific logger


# --- Helper Functions (Compress, Verify Image, Verify Zip, Split Files) ---
def compress_image(img_path, quality=85):
    """Compress an image with reduced quality but maintaining dimensions"""
    try:
        # Retry mechanism for potential file access issues
        max_retries = 3
        for attempt in range(max_retries):
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
                        # Optimize reduces size, compression level further reduces (but slower)
                        save_kwargs = {
                            "optimize": True,
                            "compress_level": 6,
                        }  # 0=none, 9=max

                    img.save(buffer, format=img_format, **save_kwargs)
                    buffer.seek(0)  # Reset buffer position
                    return buffer.getvalue()  # Success
            except OSError as e:
                # Specific check for file locking/access issues common on some systems
                if (
                    "cannot identify image file" in str(e)
                    or "Errno 9" in str(e)
                    or "Errno 2" in str(e)
                ):
                    log.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed to open/process {img_path}: {e}. Retrying..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff slightly
                    else:
                        log.error(
                            f"Final attempt failed to compress image {img_path} due to OS error: {e}",
                            exc_info=True,
                        )
                        return None  # Failed after retries
                else:
                    # Different OS error, fail immediately
                    log.error(
                        f"Error compressing image {img_path} (OS Error): {e}",
                        exc_info=True,
                    )
                    return None
            except Exception as e:
                log.error(f"Error compressing image {img_path}: {e}", exc_info=True)
                return None  # Failed due to other exception

    except FileNotFoundError:
        log.error(f"Compression failed: File not found {img_path}")
        return None
    except Exception as e:
        # Catch potential issues before even entering the retry loop (e.g., invalid path)
        log.error(
            f"Unexpected error accessing image {img_path} for compression: {e}",
            exc_info=True,
        )
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
    except zipfile.BadZipFile as e:
        log.error(
            f"Verification failed: Bad zip file format {zip_path}: {e}", exc_info=True
        )
        return False
    except Exception as e:
        log.error(f"Error verifying zip {zip_path}: {e}", exc_info=True)
        return False


def split_files_into_groups(file_list, num_groups):
    """Splits a list of files into roughly equal groups."""
    if num_groups <= 0:
        return []
    total_files = len(file_list)
    if total_files == 0:
        return []
    if num_groups >= total_files:  # Handle case where we need more groups than files
        return [[f] for f in file_list]  # Each file becomes its own group

    base_size = total_files // num_groups
    remainder = total_files % num_groups
    groups = []
    start_index = 0
    for i in range(num_groups):
        end_index = start_index + base_size + (1 if i < remainder else 0)
        groups.append(file_list[start_index:end_index])
        start_index = end_index
    return groups


# --- Zip Creation Function ---
def create_zip_group(
    files_to_zip,  # List of filenames (relative to subfolder_path)
    subfolder_path,  # Absolute path to the source subfolder
    output_dir,  # Directory where the zip file should be created (temporary or final)
    base_zip_name,  # Base name for the zip (e.g., "ocean_nursery")
    group_num=None,
    total_groups=None,
    compress_images=True,
    image_quality=80,
):
    """Helper function to create a single zip file with verification and compression"""
    valid_files_data = {}  # {filename: data_or_path}
    has_errors = False

    # Validate images and prepare data
    for filename in files_to_zip:
        img_path = os.path.join(subfolder_path, filename)
        # Basic check, main filter is earlier
        if not os.path.isfile(img_path):
            log.warning(
                f"Item '{filename}' is not a file. Skipping during zip group creation."
            )
            continue  # Skip non-files
        if not verify_image(img_path):
            log.warning(f"Skipping invalid image during zip creation: {filename}")
            has_errors = True  # Mark error but continue trying others? Or fail group? Let's mark and continue.
            continue  # Skip bad images

        if compress_images:
            compressed_data = compress_image(img_path, image_quality)
            if compressed_data:
                valid_files_data[filename] = compressed_data
            else:
                log.warning(
                    f"Compression failed for {filename}, trying to use original."
                )
                # Fallback: attempt to use original if compression fails
                if verify_image(img_path):  # Re-verify just in case
                    valid_files_data[filename] = img_path  # Path to original
                else:
                    log.error(
                        f"Cannot use original for {filename} either after compression failure. Skipping."
                    )
                    has_errors = True  # Critical failure for this file
        else:
            if verify_image(img_path):
                valid_files_data[filename] = img_path  # Path
            else:
                log.warning(f"Skipping invalid image {filename} (non-compressed path).")
                has_errors = True
                continue

    if not valid_files_data:
        log.error(
            f"No valid images to zip for group {group_num or 'single'} of {base_zip_name}. Group creation failed."
        )
        return None, 0, True  # Indicate critical failure for the group

    # Create filename
    if group_num is not None and total_groups is not None and total_groups > 1:
        zip_filename = f"{base_zip_name}_part{group_num}of{total_groups}.zip"
    else:
        zip_filename = f"{base_zip_name}.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    # Create zip file
    try:
        os.makedirs(output_dir, exist_ok=True)  # Ensure output dir exists
        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zipf:
            for filename, data_or_path in valid_files_data.items():
                arcname = filename  # Keep original filename inside zip
                try:
                    if isinstance(data_or_path, bytes):
                        zipf.writestr(arcname, data_or_path)
                    else:  # It's a path to the original file
                        zipf.write(data_or_path, arcname)
                except Exception as write_e:
                    log.error(
                        f"Error writing file '{filename}' to zip '{zip_filename}': {write_e}",
                        exc_info=True,
                    )
                    has_errors = True  # Mark error for this specific file write
                    # Optionally: decide if one failed write should fail the whole zip

        # Verification should happen *after* the 'with' block closes the file
        if not verify_zip(zip_path):
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except OSError as rm_e:
                    log.error(f"Failed to remove corrupted zip {zip_path}: {rm_e}")
            raise Exception(f"Failed verification for created zip file: {zip_filename}")

        zip_size_bytes = os.path.getsize(zip_path)
        zip_size_mb = zip_size_bytes / (1024 * 1024)
        log.debug(
            f"Successfully created and verified: {zip_filename} ({zip_size_mb:.2f} MB)"
        )
        # Return path, size, and whether any non-critical errors occurred during processing
        return zip_path, zip_size_mb, has_errors

    except Exception as e:
        log.error(f"Failed to create zip file {zip_filename}: {e}", exc_info=True)
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)  # Clean up failed attempt
            except OSError as rm_e:
                log.error(
                    f"Failed to remove partially created/failed zip {zip_path}: {rm_e}"
                )
        return None, 0, True  # Indicate critical failure for the group


# --- Main Processing Function ---
def create_zip_files(source_base_folder, max_size_mb=20, image_quality=75):
    """
    Creates zip files containing ONLY the images directly within each subfolder
    found in source_base_folder. Creates a single zip if possible. If the single
    zip exceeds max_size_mb, it splits the files into the minimum number of
    parts required, attempting to keep each part below the limit.

    Args:
        source_base_folder (str): Path to the folder containing subfolders with images.
        max_size_mb (float): Maximum target size in MB for a single zip file part.
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
    # Define folders to ignore relative to source_base_folder
    folders_to_ignore = {
        "mocks",
        "zipped",
        "temp_zip_creation",
        ".git",  # Common examples
        "__pycache__",
        ".DS_Store",
    }

    for item_name in os.listdir(source_base_folder):
        subfolder_path = os.path.join(source_base_folder, item_name)

        # --- Skip non-directories and ignored folder names ---
        if not os.path.isdir(subfolder_path):
            log.debug(f"Skipping non-directory item: {item_name}")
            continue
        # Check against base name for ignored folders
        if os.path.basename(item_name) in folders_to_ignore:
            log.debug(f"Skipping ignored directory: {item_name}")
            continue

        subfolder_name = item_name
        log.info(f"Processing subfolder: {subfolder_name}")
        sanitized_name = subfolder_name.replace(" ", "_")

        # --- Output folders INSIDE the subfolder being processed ---
        zipped_folder = os.path.join(subfolder_path, "zipped")
        temp_dir = os.path.join(zipped_folder, "temp_zip_creation")

        # --- Clean up/create output dirs ---
        try:
            if os.path.exists(zipped_folder):
                # Optionally remove old zips first? Or keep them? Let's keep for now.
                # Clean only the temp dir
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            else:
                os.makedirs(zipped_folder)  # Create zipped if not exists
            os.makedirs(temp_dir)  # Always create a fresh temp dir
        except OSError as e:
            log.error(
                f"[{subfolder_name}] Error setting up output directories: {e}. Skipping folder."
            )
            continue

        try:
            # --- Get and Sort Image Files ---
            all_items_in_subfolder = os.listdir(subfolder_path)
            image_files_in_subfolder = []
            for f_name in all_items_in_subfolder:
                item_path = os.path.join(subfolder_path, f_name)
                # Ensure it's a file AND has a valid image extension
                if os.path.isfile(item_path) and f_name.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".webp")
                ):  # Added webp
                    image_files_in_subfolder.append(f_name)

            log.debug(
                f"[{subfolder_name}] Found potential image files: {image_files_in_subfolder}"
            )

            # --- Sort files based on number in filename (e.g., name_X.ext) ---
            # Allows consistent splitting if needed
            numbered_files = []
            skipped_files = []
            for img_filename in image_files_in_subfolder:
                try:
                    name_part = os.path.splitext(img_filename)[0]
                    # Handle potential multiple underscores or non-numeric endings gracefully
                    parts = name_part.split("_")
                    if len(parts) > 1 and parts[-1].isdigit():
                        num = int(parts[-1])
                        numbered_files.append((num, img_filename))
                    else:
                        skipped_files.append(img_filename)
                except (ValueError, IndexError):
                    skipped_files.append(img_filename)

            # Sort by extracted number
            numbered_files.sort(key=lambda x: x[0])
            sorted_files = [f for _, f in numbered_files]

            if skipped_files:
                log.warning(
                    f"[{subfolder_name}] Files skipped due to non-standard naming (expected 'name_X.ext'): {skipped_files}"
                )
            if not sorted_files:
                log.warning(
                    f"[{subfolder_name}] No valid, numbered image files found to zip. Skipping."
                )
                continue  # Skip folder if no sortable images found

            log.info(
                f"[{subfolder_name}] Found {len(sorted_files)} numbered image files to process."
            )

            # --- Attempt 1: Single Zip ---
            log.info(f"[{subfolder_name}] Attempting to create a single zip...")
            single_zip_path, single_zip_size_mb, single_zip_errors = create_zip_group(
                sorted_files,
                subfolder_path,
                temp_dir,  # Create in temp first
                sanitized_name,
                compress_images=True,
                image_quality=image_quality,
            )

            # --- Handle Single Zip Result ---
            final_zip_paths_for_folder = []
            if single_zip_path and single_zip_size_mb <= max_size_mb:
                # Success with single zip
                final_path = os.path.join(
                    zipped_folder, os.path.basename(single_zip_path)
                )
                try:
                    shutil.move(single_zip_path, final_path)
                    log.info(
                        f"[{subfolder_name}] Success: Created single zip '{os.path.basename(final_path)}' ({single_zip_size_mb:.2f} MB)"
                    )
                    final_zip_paths_for_folder = [final_path]
                    zip_files_created[subfolder_name] = final_zip_paths_for_folder
                except Exception as move_e:
                    log.error(
                        f"[{subfolder_name}] Failed to move successful single zip {single_zip_path} to {final_path}: {move_e}"
                    )
                    # Zip might be left in temp dir, cleanup will handle later

            elif single_zip_path:  # Single zip created but too large
                log.info(
                    f"[{subfolder_name}] Single zip is too large ({single_zip_size_mb:.2f} MB > {max_size_mb} MB). Attempting to split."
                )
                # Clean up the large single zip from temp
                try:
                    os.remove(single_zip_path)
                except OSError as e:
                    log.warning(
                        f"[{subfolder_name}] Could not remove oversized single zip from temp: {e}"
                    )

                # --- Dynamic Splitting Logic ---
                num_files = len(sorted_files)
                # Start estimate: theoretical minimum groups based on oversized zip size
                current_num_groups = math.ceil(single_zip_size_mb / max_size_mb)
                # Ensure at least 2 groups if splitting is needed
                current_num_groups = max(2, int(current_num_groups))

                splitting_succeeded = False
                split_attempt_paths = []

                while current_num_groups <= num_files:
                    log.info(
                        f"[{subfolder_name}] Splitting attempt: Trying {current_num_groups} parts..."
                    )
                    split_groups = split_files_into_groups(
                        sorted_files, current_num_groups
                    )
                    split_attempt_paths = []  # Paths for this specific attempt
                    split_attempt_sizes = []
                    all_parts_ok = True
                    any_part_failed_creation = False

                    for i, group_files in enumerate(split_groups, 1):
                        if (
                            not group_files
                        ):  # Skip empty groups if splitting resulted in them
                            log.warning(
                                f"[{subfolder_name}] Skipping empty group {i}/{current_num_groups} during split."
                            )
                            continue

                        part_zip_path, part_zip_size_mb, part_errors = create_zip_group(
                            group_files,
                            subfolder_path,
                            temp_dir,  # Create parts in temp dir first
                            sanitized_name,
                            group_num=i,
                            total_groups=current_num_groups,
                            compress_images=True,
                            image_quality=image_quality,
                        )

                        if part_zip_path:
                            split_attempt_paths.append(part_zip_path)
                            split_attempt_sizes.append(part_zip_size_mb)
                            if part_zip_size_mb > max_size_mb:
                                log.warning(
                                    f"[{subfolder_name}] Split part {i}/{current_num_groups} is still too large ({part_zip_size_mb:.2f} MB). Need more parts."
                                )
                                all_parts_ok = False
                                break  # No need to create more parts for this attempt
                            # Log success for this part even if we might retry with more groups
                            log.debug(
                                f"[{subfolder_name}] Created split part {i}/{current_num_groups} ({part_zip_size_mb:.2f} MB) in temp."
                            )
                        else:
                            log.error(
                                f"[{subfolder_name}] Failed to create split part {i}/{current_num_groups}."
                            )
                            all_parts_ok = False
                            any_part_failed_creation = True  # Critical failure
                            break  # Stop this attempt

                    # --- Evaluate outcome of the splitting attempt ---
                    if all_parts_ok:
                        # Success! Move all parts from temp to final destination
                        log.info(
                            f"[{subfolder_name}] Successfully created {current_num_groups} zip parts within size limits."
                        )
                        moved_paths = []
                        move_error = False
                        for i, temp_path in enumerate(split_attempt_paths):
                            final_part_path = os.path.join(
                                zipped_folder, os.path.basename(temp_path)
                            )
                            try:
                                shutil.move(temp_path, final_part_path)
                                moved_paths.append(final_part_path)
                                log.info(
                                    f"[{subfolder_name}] Finalized part {i+1}/{current_num_groups}: '{os.path.basename(final_part_path)}' ({split_attempt_sizes[i]:.2f} MB)"
                                )
                            except Exception as move_e:
                                log.error(
                                    f"[{subfolder_name}] Failed to move successful part {temp_path} to {final_part_path}: {move_e}"
                                )
                                move_error = True
                                # Try to clean up already moved parts if error occurs? Complex. Log and mark failure.
                                break  # Stop moving if one fails

                        if not move_error:
                            final_zip_paths_for_folder = moved_paths
                            zip_files_created[subfolder_name] = (
                                final_zip_paths_for_folder
                            )
                            splitting_succeeded = True
                        else:
                            log.error(
                                f"[{subfolder_name}] Failed to finalize all parts due to move error. Manual cleanup of '{zipped_folder}' and '{temp_dir}' might be needed."
                            )
                            # Cleanup temp dir for this attempt
                            for p in split_attempt_paths:
                                if os.path.exists(p):
                                    os.remove(p)

                        break  # Exit the while loop (splitting succeeded or failed critically during move)

                    else:
                        # Attempt failed (either too large or creation error)
                        # Clean up parts created during *this* failed attempt from temp dir
                        log.warning(
                            f"[{subfolder_name}] Cleaning up failed attempt with {current_num_groups} parts..."
                        )
                        for p in split_attempt_paths:
                            if os.path.exists(p):
                                try:
                                    os.remove(p)
                                except OSError as e:
                                    log.warning(
                                        f"[{subfolder_name}] Could not remove temp part {p}: {e}"
                                    )

                        if any_part_failed_creation:
                            log.error(
                                f"[{subfolder_name}] Aborting splitting for this folder due to critical error creating a part."
                            )
                            break  # Exit while loop, splitting failed critically

                        # If failure was due to size, increment group count and loop again
                        current_num_groups += 1
                        if current_num_groups > num_files:
                            log.error(
                                f"[{subfolder_name}] Cannot split further (tried {current_num_groups-1} parts, max possible is {num_files}). Zipping failed. One or more individual files might be too large when compressed."
                            )
                            # This means even zipping one file per archive might exceed the limit, or an error occurred.
                            break  # Exit while loop

                if not splitting_succeeded and not final_zip_paths_for_folder:
                    log.error(
                        f"[{subfolder_name}] Failed to create zip files satisfying the size constraints after trying to split."
                    )
                    # final_zip_paths_for_folder remains empty

            elif not single_zip_path:  # Failed to create single zip initially
                log.error(
                    f"[{subfolder_name}] Attempt 1 failed: Could not create initial zip. Zipping aborted for this folder."
                )
                # final_zip_paths_for_folder remains empty

            # --- End of processing for a subfolder ---
            if not final_zip_paths_for_folder:
                log.warning(
                    f"[{subfolder_name}] No zip files were successfully created for this folder."
                )

        except Exception as e:
            log.error(
                f"An unexpected error occurred processing subfolder '{subfolder_name}': {e}",
                exc_info=True,
            )
        finally:
            # --- Final Cleanup for the subfolder ---
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    log.debug(
                        f"[{subfolder_name}] Cleaned up temporary directory: {temp_dir}"
                    )
                except OSError as e:
                    log.error(
                        f"[{subfolder_name}] Failed to clean up temporary directory {temp_dir}: {e}"
                    )

    log.info("Zip creation process finished.")
    return zip_files_created


# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create zip archives of images in subfolders, splitting dynamically based on max size."
    )
    parser.add_argument(
        "--source_folder",
        required=True,
        help="Path to the base folder containing the subfolders with images (e.g., 'input').",
    )
    parser.add_argument(
        "--max_size_mb",
        type=float,
        default=20.0,
        help="Maximum target size (MB) for each zip file part.",
    )
    parser.add_argument(
        "--image_quality",
        type=int,
        default=80,  # Slightly higher default quality
        choices=range(1, 101),
        metavar="[1-100]",
        help="Image compression quality (1-100, lower is smaller/lower quality). Affects JPEG and potentially some PNG optimizations.",
    )
    args = parser.parse_args()

    # --- Input validation ---
    if not os.path.isdir(args.source_folder):
        print(
            f"Error: Source folder '{args.source_folder}' not found or is not a directory."
        )
        exit(1)
    if args.max_size_mb <= 0:
        print("Error: --max_size_mb must be a positive value.")
        exit(1)
    if not (1 <= args.image_quality <= 100):
        print("Error: --image_quality must be between 1 and 100.")
        exit(1)

    results = create_zip_files(
        source_base_folder=args.source_folder,
        max_size_mb=args.max_size_mb,
        image_quality=args.image_quality,
    )

    log.info("--- Zip Creation Summary ---")
    if results:
        total_zips = 0
        for folder, zips in results.items():
            count = len(zips)
            total_zips += count
            log.info(
                f"'{folder}': {count} zip(s) created -> {[os.path.basename(p) for p in zips]}"
            )
        log.info(f"Total zip files created: {total_zips}")
    else:
        log.info("No zip files were created.")
    log.info("--------------------------")
