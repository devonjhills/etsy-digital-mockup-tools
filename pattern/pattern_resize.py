import os
from PIL import Image
import sys  # Added for robustness if running as a script directly


def process_images(input_folder, max_size=(3600, 3600), dpi=(300, 300)):
    """
    Resizes images to fit within max dimensions while maintaining aspect ratio.

    Parameters:
        input_folder (str): Path to the input folder containing subfolders with images.
        max_size (tuple): Maximum image size (width, height) in pixels.
        dpi (tuple): Desired DPI for the images.
    """
    # Ensure the input folder exists
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder not found at '{input_folder}'")
        return

    print(f"Processing images in: {input_folder}")

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if os.path.isdir(subfolder_path):
            print(f"\nProcessing subfolder: {subfolder}")
            safe_subfolder_name = subfolder.replace(" ", "_").lower()

            image_files = [
                f
                for f in os.listdir(subfolder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            if not image_files:
                print(f"  No image files found in {subfolder}.")
                continue

            processed_count = 0
            skipped_count = 0
            error_count = 0

            for index, image_file in enumerate(image_files, start=1):
                image_path = os.path.join(subfolder_path, image_file)
                # Keep original extension temporarily, decide format on save
                original_name, original_ext = os.path.splitext(image_file)
                # New name will always be .jpg as per save format
                new_name = f"{safe_subfolder_name}_{index}.jpg"
                new_path = os.path.join(subfolder_path, new_name)

                # --- Check if the target file exists and is already correct ---
                # This logic prevents reprocessing if script is run multiple times
                # or if a file was manually named according to the convention.
                if os.path.exists(new_path):
                    try:
                        with Image.open(new_path) as existing_img:
                            # Check if existing file meets size criteria
                            if (
                                existing_img.size[0] <= max_size[0]
                                and existing_img.size[1] <= max_size[1]
                            ):
                                # If the existing correct file *is not* the current source file,
                                # maybe remove the source file if it's different.
                                # Otherwise, just skip.
                                if image_path != new_path:
                                    print(
                                        f"  Skipping {image_file}: Correctly named/sized file {new_name} already exists."
                                    )
                                    # Optionally remove the original if it wasn't the target file already
                                    # try:
                                    #     os.remove(image_path)
                                    #     print(f"  Removed original unprocessed file: {image_file}")
                                    # except OSError as e:
                                    #     print(f"  Warning: Could not remove original {image_file}: {e}")
                                else:
                                    print(
                                        f"  Skipping already processed file: {new_name}"
                                    )
                                skipped_count += 1
                                continue  # Skip to next image file
                    except Exception as e:
                        print(
                            f"  Warning: Could not check existing file {new_path}: {e}"
                        )
                        # Decide whether to continue and potentially overwrite, or skip
                        # For safety, let's skip if we can't verify the existing file
                        # skipped_count += 1
                        # continue

                # --- Process the image ---
                try:
                    with Image.open(image_path) as img:
                        # Convert RGBA to RGB before saving as JPEG to avoid errors
                        if img.mode == "RGBA":
                            print(f"  Converting {image_file} from RGBA to RGB.")
                            # Create a white background image
                            bg = Image.new("RGB", img.size, (255, 255, 255))
                            # Paste the image onto the background using the alpha channel as mask
                            bg.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                            img = bg
                        elif img.mode != "RGB":
                            print(f"  Converting {image_file} from {img.mode} to RGB.")
                            img = img.convert("RGB")

                        # Calculate new size maintaining aspect ratio
                        width, height = img.size
                        ratio = min(max_size[0] / width, max_size[1] / height)

                        needs_resize = ratio < 1
                        if needs_resize:
                            new_width = int(width * ratio)
                            new_height = int(height * ratio)
                            print(
                                f"  Resizing: {image_file} ({width}x{height}) to {new_width}x{new_height}"
                            )
                            img = img.resize(
                                (new_width, new_height), Image.Resampling.LANCZOS
                            )  # Use Resampling enum

                        # Set DPI (ensure img.info exists)
                        if "dpi" not in img.info:
                            img.info["dpi"] = dpi
                        else:
                            # Only update if different, though overwriting is fine
                            img.info["dpi"] = dpi

                        # Save image with optimized settings
                        print(f"  Saving: {new_name} (Quality: 85, DPI: {dpi})")
                        img.save(
                            new_path,
                            format="JPEG",
                            dpi=dpi,
                            quality=85,
                            optimize=True,
                            subsampling="4:2:0",  # Standard chroma subsampling for JPEG
                        )
                        processed_count += 1

                        # Remove original file ONLY if it's different from the new file
                        if new_path != image_path:
                            try:
                                os.remove(image_path)
                                action = (
                                    "Resized and renamed"
                                    if needs_resize
                                    else "Converted/Renamed"
                                )
                                print(
                                    f"  {action}: {image_file} -> {new_name} (Original removed)"
                                )
                            except OSError as e:
                                print(
                                    f"  Warning: Could not remove original file {image_path}: {e}"
                                )
                        else:
                            print(f"  Processed inplace: {new_name}")

                except FileNotFoundError:
                    print(f"  Error: File not found during processing: {image_path}")
                    error_count += 1
                except Exception as e:
                    print(f"  Error processing {image_path}: {e}")
                    error_count += 1

            print(
                f"  Finished {subfolder}: Processed={processed_count}, Skipped={skipped_count}, Errors={error_count}"
            )


if __name__ == "__main__":
    # --- Determine the correct path to the 'input' folder ---
    # Get the directory where the script itself is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the 'input' folder (it's in the parent directory)
    input_folder_path = os.path.join(script_dir, "..", "input")
    # Normalize the path (e.g., resolves "..")
    input_folder_path = os.path.normpath(input_folder_path)

    # --- Call the processing function ---
    process_images(input_folder_path)
    print("\nImage processing complete.")
