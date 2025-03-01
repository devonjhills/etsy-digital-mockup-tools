import os
import zipfile
import shutil
from PIL import Image


def verify_image(img_path):
    """Verify that an image can be properly loaded"""
    try:
        with Image.open(img_path) as img:
            img.load()
        return True
    except Exception as e:
        print(f"Error verifying image {img_path}: {e}")
        return False


def verify_zip(zip_path):
    """Verify zip file integrity and ability to extract all files"""
    try:
        with zipfile.ZipFile(zip_path, "r") as zipf:
            if zipf.testzip() is not None:
                raise Exception("Zip file is corrupted")
            for filename in zipf.namelist():
                with zipf.open(filename) as f:
                    f.read()
        return True
    except Exception as e:
        print(f"Error verifying zip {zip_path}: {e}")
        return False


def create_zip_group(
    files, subfolder_path, output_dir, sanitized_name, group_num=None, total_groups=None
):
    """Helper function to create a single zip file with verification"""
    # Verify all images before creating zip
    valid_files = []
    for img in files:
        img_path = os.path.join(subfolder_path, img)
        if verify_image(img_path):
            valid_files.append(img)
        else:
            print(f"Skipping invalid image: {img}")

    if not valid_files:
        raise Exception("No valid images to zip")

    # Create filename based on whether this is a part or full archive
    if group_num and total_groups:
        zip_filename = f"{sanitized_name}_part{group_num}of{total_groups}.zip"
    else:
        zip_filename = f"{sanitized_name}.zip"

    zip_path = os.path.join(output_dir, zip_filename)

    # Create zip file
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipf:
        for img in valid_files:
            img_path = os.path.join(subfolder_path, img)
            zipf.write(img_path, os.path.basename(img_path))

    # Verify zip after creation
    if not verify_zip(zip_path):
        os.remove(zip_path)
        raise Exception(f"Failed to create valid zip file: {zip_filename}")

    return zip_path, os.path.getsize(zip_path) / (1024 * 1024)


def create_zip_files(input_folder, max_size_mb=20):
    """
    Creates zip files for each subfolder. Makes a single zip if under max_size_mb,
    otherwise splits into multiple parts.

    Args:
        input_folder (str): Path to the input folder containing subfolders with images
        max_size_mb (float): Maximum size in MB for a single zip file

    Returns:
        dict: Dictionary with subfolder names as keys and list of created zip paths as values
    """
    zip_files_created = {}

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if not os.path.isdir(subfolder_path):
            continue

        sanitized_name = subfolder.replace(" ", "_")
        zipped_folder = os.path.join(subfolder_path, "zipped")
        os.makedirs(zipped_folder, exist_ok=True)

        # Create temp directory for zip attempts
        temp_dir = os.path.join(zipped_folder, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        image_files = [
            f
            for f in os.listdir(subfolder_path)
            if f.lower().endswith(("jpg", "jpeg", "png", "gif", "bmp", "tiff"))
        ]

        # Sort files by the index number in their names
        numbered_files = []
        for img in image_files:
            try:
                # Extract number from filename (assuming format: name_X.ext)
                num = int(img.split("_")[-1].split(".")[0])
                numbered_files.append((num, img))
            except (ValueError, IndexError):
                print(f"Warning: File '{img}' does not follow naming convention")
                continue

        # Sort by extracted number and get just the filenames
        numbered_files.sort(key=lambda x: x[0])
        sorted_files = [f for _, f in numbered_files]

        if len(sorted_files) == 12:
            # First try creating a single zip file
            try:
                zip_path, zip_size = create_zip_group(
                    sorted_files, subfolder_path, temp_dir, sanitized_name
                )

                if zip_size <= max_size_mb:
                    # Single zip is small enough, keep it
                    final_path = os.path.join(zipped_folder, os.path.basename(zip_path))
                    shutil.move(zip_path, final_path)
                    print(
                        f"Created single zip: {os.path.basename(final_path)} ({zip_size:.1f}MB)"
                    )
                    zip_files_created[sanitized_name] = [final_path]
                else:
                    # Single zip is too large, try with 2 groups
                    os.remove(zip_path)
                    print(
                        f"Single zip too large ({zip_size:.1f}MB > {max_size_mb}MB), trying to split..."
                    )

                    # Try two groups
                    zip_paths = []
                    need_four_groups = False

                    first_half = sorted_files[:6]
                    second_half = sorted_files[6:]

                    for part, images in enumerate([first_half, second_half], 1):
                        zip_path, zip_size = create_zip_group(
                            images, subfolder_path, temp_dir, sanitized_name, part, 2
                        )

                        if zip_size > max_size_mb:
                            need_four_groups = True
                            break
                        zip_paths.append(zip_path)

                    # If any zip was too large, delete them and create 4 groups instead
                    if need_four_groups:
                        for path in zip_paths:
                            if os.path.exists(path):
                                os.remove(path)

                        print(
                            f"Files too large for 2 groups, splitting into 4 groups..."
                        )
                        zip_paths = []
                        quarter_size = len(sorted_files) // 4
                        groups = [
                            sorted_files[i : i + quarter_size]
                            for i in range(0, len(sorted_files), quarter_size)
                        ]

                        for part, images in enumerate(groups, 1):
                            zip_path, zip_size = create_zip_group(
                                images,
                                subfolder_path,
                                zipped_folder,
                                sanitized_name,
                                part,
                                4,
                            )
                            zip_paths.append(zip_path)
                            print(
                                f"Created {os.path.basename(zip_path)} ({zip_size:.1f}MB)"
                            )
                    else:
                        # Move successful 2-group zips to final location
                        for zip_path in zip_paths:
                            final_path = os.path.join(
                                zipped_folder, os.path.basename(zip_path)
                            )
                            shutil.move(zip_path, final_path)
                            print(
                                f"Created {os.path.basename(final_path)} ({os.path.getsize(final_path) / (1024 * 1024):.1f}MB)"
                            )
                        zip_paths = [
                            os.path.join(zipped_folder, os.path.basename(p))
                            for p in zip_paths
                        ]

                    zip_files_created[sanitized_name] = zip_paths
            except Exception as e:
                print(f"Error processing subfolder '{subfolder}': {e}")

            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"Warning: Subfolder '{subfolder}' does not have exactly 12 images.")

    return zip_files_created


if __name__ == "__main__":
    input_folder = "input"
    create_zip_files(input_folder)
