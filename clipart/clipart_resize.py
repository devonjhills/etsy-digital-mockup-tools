import os
from PIL import Image
import argparse


def trim(im):
    """Remove empty space around an image with transparency"""
    bbox = im.convert("RGBA").getbbox()
    if bbox:
        return im.crop(bbox)
    return im


def meets_requirements(img_path, max_size):
    """Check if image meets all requirements: size, DPI, and naming"""
    try:
        with Image.open(img_path) as img:
            # Check if PNG format
            if img.format != "PNG":
                print("Failed: Not PNG format")
                return False

            # Check dimensions
            width, height = img.size
            if width > max_size or height > max_size:
                print("Failed: Image too large")
                return False

            # Check filename format
            dirname = os.path.dirname(img_path)
            basename = os.path.basename(dirname)
            safe_name = basename.replace(" ", "_").lower()
            current_name = os.path.basename(img_path)
            expected_prefix = f"{safe_name}_"

            if not current_name.startswith(expected_prefix):
                print("Failed: Wrong filename prefix")
                return False

            try:
                index = int(current_name[len(expected_prefix) : -4])  # Remove .png
                expected_name = f"{safe_name}_{index}.png"
                if not current_name == expected_name:
                    print("Failed: Wrong filename format")
                    return False
            except ValueError:
                print("Failed: Invalid index number in filename")
                return False

            return True

    except Exception as e:
        print(f"Failed with error: {str(e)}")
        return False


def process_images(input_folder, max_size):
    """
    Processes images: converts to PNG, trims empty space, and resizes if needed.
    Sets DPI to 300 for all images. Skips already processed files.

    Parameters:
        input_folder (str): Path to the input folder containing subfolders with images.
        max_size (int): Maximum size for the longest edge while maintaining aspect ratio.
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
                new_name = f"{safe_subfolder_name}_{index}.png"
                new_path = os.path.join(subfolder_path, new_name)

                # Skip if file meets all requirements
                if meets_requirements(image_path, max_size):
                    continue

                try:
                    with Image.open(image_path) as img:
                        # Convert to RGBA to ensure transparency support
                        img = img.convert("RGBA")

                        # Trim empty space
                        img = trim(img)

                        width, height = img.size
                        needs_resize = width > max_size or height > max_size

                        if needs_resize:
                            # Calculate new size maintaining aspect ratio
                            if width > height:
                                new_width = max_size
                                new_height = int(height * (max_size / width))
                            else:
                                new_height = max_size
                                new_width = int(width * (max_size / height))

                            # Resize image
                            img = img.resize((new_width, new_height), Image.LANCZOS)

                        # Set DPI to 300
                        img.info["dpi"] = (300, 300)

                        # Save as PNG with new name
                        img.save(new_path, format="PNG", dpi=(300, 300))

                        # Remove the original file if the name has changed
                        if new_path != image_path:
                            os.remove(image_path)

                        print(f"Processed: {new_path}")

                except Exception as e:
                    print(f"Error processing {image_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize clipart images")
    parser.add_argument(
        "--input_folder", default="input", help="Path to the input folder"
    )
    parser.add_argument(
        "--max_size", type=int, default=1500, help="Maximum size for the longest edge"
    )
    args = parser.parse_args()
    process_images(args.input_folder, args.max_size)
