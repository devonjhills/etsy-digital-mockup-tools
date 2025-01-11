import os
from PIL import Image


def process_images(input_folder, target_size=(3600, 3600), dpi=(300, 300)):
    """
    Resizes images only if larger than target size, otherwise just renames them.

    Parameters:
        input_folder (str): Path to the input folder containing subfolders with images.
        target_size (tuple): Maximum image size (width, height) in pixels.
        dpi (tuple): Desired DPI for the images.
    """
    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if os.path.isdir(subfolder_path):
            safe_subfolder_name = subfolder.replace(" ", "_").lower()

            image_files = [
                f
                for f in os.listdir(subfolder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            for index, image_file in enumerate(image_files, start=1):
                image_path = os.path.join(subfolder_path, image_file)
                new_name = f"{safe_subfolder_name}_{index}.jpg"
                new_path = os.path.join(subfolder_path, new_name)

                # Skip if file is already processed
                if image_path == new_path:
                    print(f"Skipping already processed: {image_path}")
                    continue

                try:
                    with Image.open(image_path) as img:
                        # Skip if file exists and is already correct size
                        if os.path.exists(new_path):
                            with Image.open(new_path) as existing_img:
                                if existing_img.size == target_size:
                                    print(f"Skipping existing correct size: {new_path}")
                                    continue

                        needs_resize = any(
                            dim > target for dim, target in zip(img.size, target_size)
                        )

                        if needs_resize:
                            img = img.resize(target_size, Image.LANCZOS)
                            print(f"Resizing: {image_path}")

                        # Set DPI
                        img.info["dpi"] = dpi

                        # Save image with new name
                        img.save(new_path, format="JPEG", dpi=dpi, quality=100)

                        # Remove the original file if the name has changed
                        if new_path != image_path:
                            os.remove(image_path)
                            action = (
                                "Resized and renamed" if needs_resize else "Renamed"
                            )
                            print(f"{action}: {new_path}")

                except Exception as e:
                    print(f"Error processing {image_path}: {e}")


if __name__ == "__main__":
    input_folder = "input"  # Replace with your input folder path

    process_images(input_folder)
