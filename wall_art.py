import os
import math
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import warnings

# Suppress PIL DecompressionBombWarning
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)


def process_image(image_path, target_info, output_dir):
    """Process a single image for a specific target aspect ratio."""
    name, ratio_str, target_aspect, target_width, target_height = target_info

    try:
        # Create output folder named after the input image
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        output_subfolder = os.path.join(output_dir, base_filename)
        os.makedirs(output_subfolder, exist_ok=True)

        # Output filename includes the aspect ratio
        output_filename = f"{base_filename}_{ratio_str.replace(':', '-')}.jpg"
        output_path = os.path.join(output_subfolder, output_filename)

        with Image.open(image_path) as img:
            width, height = img.size
            current_aspect = width / height

            # Crop to target aspect ratio
            if current_aspect > target_aspect:
                # Image is wider than target, crop width
                new_width = int(height * target_aspect)
                left = (width - new_width) // 2
                img_cropped = img.crop((left, 0, left + new_width, height))
            else:
                # Image is taller than target, crop height
                new_height = int(width / target_aspect)
                top = (height - new_height) // 2
                img_cropped = img.crop((0, top, width, top + new_height))

            # Resize to target dimensions
            resized_img = img_cropped.resize(
                (target_width, target_height), Image.Resampling.LANCZOS
            )

            # Save the processed image as jpg
            resized_img.convert("RGB").save(output_path, format="JPEG", quality=95)
            return f"Saved {output_filename} in {output_subfolder}"
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return (
            f"Error processing {os.path.basename(image_path)} for {ratio_str}: {str(e)}"
        )


def main():
    # Fixed input and output directories
    input_dir = "input"
    output_dir = "output"

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define target aspect ratios and sizes with exact values
    portrait_targets = [
        ("US_4-5", "4:5_ratio", 4 / 5, 7200, 9000),
        ("US_2-3", "2:3_ratio", 2 / 3, 7200, 10800),
        ("US_3-4", "3:4_ratio", 3 / 4, 7200, 9600),
        ("A-series_portrait", "ISO_ratio", 1 / math.sqrt(2), 7016, 9937),
    ]

    landscape_targets = [
        ("US_5-4", "5:4_ratio", 5 / 4, 9000, 7200),
        ("US_3-2", "3:2_ratio", 3 / 2, 10800, 7200),
        ("US_4-3", "4:3_ratio ", 4 / 3, 9600, 7200),
        ("A-series_landscape", "ISO_ratio", math.sqrt(2), 9937, 7016),
    ]

    # Find all valid image files
    image_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                image_files.append(os.path.join(root, file))

    if not image_files:
        print(f"No images found in {input_dir}")
        return

    print(f"Found {len(image_files)} images to process")

    # Process images in parallel
    tasks = []
    for image_path in image_files:
        # Determine image orientation first
        with Image.open(image_path) as img:
            width, height = img.size
            targets = portrait_targets if height > width else landscape_targets

        # Add tasks for each target aspect ratio
        for target_info in targets:
            tasks.append((image_path, target_info, output_dir))

    # Process tasks in parallel with 4 workers
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for image_path, target_info, output_dir in tasks:
            results.append(
                executor.submit(process_image, image_path, target_info, output_dir)
            )

    # Print results
    for result in results:
        try:
            message = result.result()
            if message:
                print(message)
        except Exception as e:
            print(f"Task failed: {str(e)}")

    print("All images processed successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user. Exiting.")
