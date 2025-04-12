import os
import numpy as np
from PIL import Image
from scipy import ndimage


def extract_distinct_elements(image_path, output_dir="output", padding=5, min_size=100):
    """
    Extracts any number of distinct visual elements from an image.
    Works with any type of image containing separate visual elements.

    Args:
        image_path (str): Path to the input image
        output_dir (str): Directory to save the extracted elements
        padding (int): Padding to add around each element
        min_size (int): Minimum pixel area for an element to be considered valid
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open the image and convert to RGBA
    img = Image.open(image_path).convert("RGBA")

    # Convert to numpy array for processing
    img_array = np.array(img)

    # Extract alpha channel - non-zero values indicate content
    alpha_channel = img_array[:, :, 3]

    # Create binary mask where content exists
    binary_mask = alpha_channel > 0

    # Label connected components
    labeled_array, num_features = ndimage.label(binary_mask)

    # Get base filename for output
    base_filename = os.path.splitext(os.path.basename(image_path))[0]

    # Process each labeled component
    elements_saved = 0
    for label_idx in range(1, num_features + 1):
        # Get coordinates of this component
        component_mask = labeled_array == label_idx
        component_pixels = np.sum(component_mask)

        # Skip components that are too small
        if component_pixels < min_size:
            continue

        # Find bounding box
        rows = np.any(component_mask, axis=1)
        cols = np.any(component_mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            continue

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]

        # Add padding, but stay within image boundaries
        rmin = max(0, rmin - padding)
        rmax = min(img_array.shape[0] - 1, rmax + padding)
        cmin = max(0, cmin - padding)
        cmax = min(img_array.shape[1] - 1, cmax + padding)

        # Extract the element with padding
        height = rmax - rmin + 1
        width = cmax - cmin + 1

        # Create new image with transparent background
        element_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Copy pixels from the original image
        for y in range(height):
            for x in range(width):
                orig_y = rmin + y
                orig_x = cmin + x
                if (
                    0 <= orig_y < img_array.shape[0]
                    and 0 <= orig_x < img_array.shape[1]
                ):
                    pixel = tuple(img_array[orig_y, orig_x])
                    element_img.putpixel((x, y), pixel)

        # Save the element
        elements_saved += 1
        output_path = os.path.join(
            output_dir, f"{base_filename}_element_{elements_saved}.png"
        )
        element_img.save(output_path)
        print(f"Saved element {elements_saved} to {output_path}")

    if elements_saved == 0:
        print("No valid elements found in the image.")
    else:
        print(f"Successfully extracted {elements_saved} elements from {image_path}")


def process_folder(
    input_folder="input", output_folder="output", padding=5, min_size=100
):
    """
    Process all images in the input folder and extract distinct elements from each.

    Args:
        input_folder (str): Folder containing input images
        output_folder (str): Folder to save extracted elements
        padding (int): Padding to add around each element
        min_size (int): Minimum pixel area for an element to be considered valid
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get list of image files
    image_files = []
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(
            (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
        ):
            image_files.append(os.path.join(input_folder, filename))

    if not image_files:
        print(f"No image files found in {input_folder}")
        return

    print(f"Found {len(image_files)} images to process")

    # Process each image
    for image_path in image_files:
        print(f"\nProcessing {image_path}...")
        try:
            extract_distinct_elements(image_path, output_folder, padding, min_size)
        except Exception as e:
            print(f"Error processing {image_path}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract distinct visual elements from images"
    )
    parser.add_argument(
        "--padding", type=int, default=5, help="Padding around extracted elements"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=100,
        help="Minimum pixel area for valid elements",
    )

    args = parser.parse_args()

    input_folder = "input"
    output_folder = "output"

    # Clean up identifier files using the utility function
    try:
        # Add the project root to the Python path to import utils
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        import sys

        sys.path.insert(0, project_root)
        from utils.common import clean_identifier_files

        num_removed = clean_identifier_files(input_folder)
        print(f"Deleted {num_removed} identifier/system files")
    except ImportError:
        print("Could not import clean_identifier_files from utils.common")
        print("Skipping identifier file cleanup")

    # Process each immediate subfolder within the input folder
    top_level = next(os.walk(input_folder))
    subfolders = top_level[1]
    for subfolder in subfolders:
        input_subfolder = os.path.join(input_folder, subfolder)
        output_subfolder = os.path.join(output_folder, subfolder)
        print(f"Processing folder: {input_subfolder} -> {output_subfolder}")
        process_folder(input_subfolder, output_subfolder, args.padding, args.min_size)
