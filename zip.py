import os
import zipfile
import shutil

def create_zip_group(files, subfolder_path, zipped_folder, sanitized_subfolder_name, group_num, total_groups):
    """Helper function to create a single zip file"""
    zip_filename = f"{sanitized_subfolder_name}_part{group_num}of{total_groups}.zip"
    zip_path = os.path.join(zipped_folder, zip_filename)
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for img in files:
            img_path = os.path.join(subfolder_path, img)
            zipf.write(img_path, os.path.basename(img_path))
    
    return zip_path, os.path.getsize(zip_path) / (1024 * 1024)

def create_zip_files(input_folder):
    """
    Creates two zip files for each subfolder containing 12 images (6 images per zip).

    Args:
        input_folder (str): Path to the input folder containing subfolders with images

    Returns:
        dict: Dictionary with subfolder names as keys and list of created zip paths as values
    """
    zip_files_created = {}

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if not os.path.isdir(subfolder_path):
            continue

        sanitized_subfolder_name = subfolder.replace(" ", "_")

        # Use original subfolder path for zipped folder
        zipped_folder = os.path.join(subfolder_path, "zipped")
        os.makedirs(zipped_folder, exist_ok=True)

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
            # Try with 2 groups first
            zip_paths = []
            need_four_groups = False
            
            # Create temporary directory for zip attempts
            temp_zip_dir = os.path.join(zipped_folder, "temp")
            os.makedirs(temp_zip_dir, exist_ok=True)

            # Try two groups first
            first_half = sorted_files[:6]
            second_half = sorted_files[6:]
            
            for part, images in enumerate([first_half, second_half], 1):
                zip_path, zip_size = create_zip_group(
                    images, subfolder_path, temp_zip_dir, 
                    sanitized_subfolder_name, part, 2
                )
                
                if zip_size > 20:
                    need_four_groups = True
                    break
                zip_paths.append(zip_path)

            # If any zip was too large, delete them and create 4 groups instead
            if need_four_groups:
                print(f"Files too large for 2 groups, splitting into 4 groups...")
                zip_paths = []
                quarter_size = len(sorted_files) // 4
                groups = [sorted_files[i:i + quarter_size] for i in range(0, len(sorted_files), quarter_size)]
                
                for part, images in enumerate(groups, 1):
                    zip_path, zip_size = create_zip_group(
                        images, subfolder_path, zipped_folder,
                        sanitized_subfolder_name, part, 4
                    )
                    zip_paths.append(zip_path)
                    print(f"Created {os.path.basename(zip_path)} ({zip_size:.1f}MB)")
            else:
                # Move successful 2-group zips to final location
                for zip_path in zip_paths:
                    final_path = os.path.join(zipped_folder, os.path.basename(zip_path))
                    shutil.move(zip_path, final_path)
                    zip_size = os.path.getsize(final_path) / (1024 * 1024)
                    print(f"Created {os.path.basename(final_path)} ({zip_size:.1f}MB)")

            # Cleanup temp directory
            shutil.rmtree(temp_zip_dir, ignore_errors=True)
            
            zip_files_created[sanitized_subfolder_name] = zip_paths
            print(f"Created zip files for '{sanitized_subfolder_name}': {', '.join(os.path.basename(p) for p in zip_paths)}")
        else:
            print(f"Warning: Subfolder '{subfolder}' does not have exactly 12 images.")

    return zip_files_created


if __name__ == "__main__":
    input_folder = "input"
    create_zip_files(input_folder)
