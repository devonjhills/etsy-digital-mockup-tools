import os
from PIL import Image


def process_images(input_folder, max_size=(3600, 3600), dpi=(300, 300)):
    """
    Resizes images to fit within max dimensions while maintaining aspect ratio.

    Parameters:
        input_folder (str): Path to the input folder containing subfolders with images.
        max_size (tuple): Maximum image size (width, height) in pixels.
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

                if image_path == new_path:
                    print(f"Skipping already processed: {image_path}")
                    continue

                try:
                    with Image.open(image_path) as img:
                        if os.path.exists(new_path):
                            with Image.open(new_path) as existing_img:
                                if existing_img.size[0] <= max_size[0] and existing_img.size[1] <= max_size[1]:
                                    print(f"Skipping existing correct size: {new_path}")
                                    continue

                        # Calculate new size maintaining aspect ratio
                        width, height = img.size
                        ratio = min(max_size[0] / width, max_size[1] / height)
                        
                        needs_resize = ratio < 1
                        if needs_resize:
                            new_width = int(width * ratio)
                            new_height = int(height * ratio)
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                            print(f"Resizing: {image_path} to {new_width}x{new_height}")

                        # Set DPI
                        img.info["dpi"] = dpi

                        # Save image with optimized settings
                        img.save(
                            new_path, 
                            format="JPEG", 
                            dpi=dpi, 
                            quality=85,
                            optimize=True,
                            subsampling='4:2:0'
                        )

                        if new_path != image_path:
                            os.remove(image_path)
                            action = "Resized and renamed" if needs_resize else "Renamed"
                            print(f"{action}: {new_path}")

                except Exception as e:
                    print(f"Error processing {image_path}: {e}")


if __name__ == "__main__":
    input_folder = "input"  # Replace with your input folder path
    process_images(input_folder)
