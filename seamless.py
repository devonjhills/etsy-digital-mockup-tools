import os
from PIL import Image

input_folder = "input"  # Parent directory containing subfolders with images


def create_single_image_grid():
    # Process each subfolder in the input directory
    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if not os.path.isdir(subfolder_path):
            continue

        print(f"Processing subfolder: {subfolder}")

        # Process all image files in the subfolder
        processed_files = []
        valid_extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

        for file in os.listdir(subfolder_path):
            file_path = os.path.join(subfolder_path, file)

            if not file.lower().endswith(valid_extensions):
                continue

            if not os.path.isfile(file_path):
                continue

            try:
                # Open and validate image
                with Image.open(file_path) as img:
                    if img.size != (1024, 1024):
                        print(f"  Skipping {file} - incorrect dimensions")
                        continue

                    # Create 4x4 grid
                    grid_image = Image.new("RGB", (4096, 4096))
                    img_rgb = img.convert("RGB")

                    # Paste image 16 times in grid pattern
                    for i in range(16):
                        row = i // 4
                        col = i % 4
                        x = col * 1024
                        y = row * 1024
                        grid_image.paste(img_rgb, (x, y))

                    # Save new grid image
                    base_name = os.path.splitext(file)[0]
                    output_path = os.path.join(subfolder_path, f"{base_name}_grid.png")
                    grid_image.save(output_path, "PNG")
                    print(f"  Created grid: {output_path}")

                    # Mark original for deletion
                    processed_files.append(file_path)

            except Exception as e:
                print(f"  Error processing {file}: {str(e)}")

        # Delete successfully processed originals
        deleted_count = 0
        for file_path in processed_files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"  Error deleting {file_path}: {str(e)}")

        print(f"  Deleted {deleted_count} original images\n")


if __name__ == "__main__":
    print("Deleting all .Identifier files...")
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".Identifier"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    create_single_image_grid()
