import cv2
import numpy as np
from pathlib import Path
from skimage import measure
import matplotlib.pyplot as plt
import os


# --- create_output_dir and delete_identifier_files remain the same ---
def create_output_dir():
    """Create output directory if it doesn't exist"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    # Also create debug directory within the output directory
    debug_dir = output_dir / "debug"
    debug_dir.mkdir(exist_ok=True)
    return output_dir, debug_dir


def delete_identifier_files(input_dir):
    """Delete all .Identifier files in the input directory"""
    try:
        for file in input_dir.glob("*.Identifier"):
            file.unlink()
            print(f"Deleted: {file}")
    except Exception as e:
        print(f"Error deleting .Identifier files: {e}")


# --------------------------------------------------------------------


def extract_illustrations(image_path, output_dir, debug_dir):
    """
    Extracts individual clip art images from a composite image.
    Handles both transparent backgrounds (via alpha channel) and
    solid white/near-white backgrounds.
    """
    # Read image, preserving alpha channel if it exists
    img_bgra = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img_bgra is None:
        print(f"Error: Failed to load image: {image_path}")
        return

    height, width, channels = img_bgra.shape[
        :3
    ]  # Use slicing to avoid error if only 2 dims exist
    has_alpha = channels == 4

    print(f"Processing '{image_path.name}'...")

    mask = None
    img_bgr = None  # Will store the 3-channel version if needed

    # --- Method 1: Try Alpha Channel ---
    if has_alpha:
        alpha = img_bgra[:, :, 3]
        # Check if alpha channel has significant transparency
        # If min alpha is high (e.g., >= 250), it's likely opaque or near-opaque
        if np.min(alpha) < 250:
            print("   Using alpha channel for masking.")
            alpha_threshold = 1  # Pixels with alpha > 0 are non-transparent
            mask = (alpha >= alpha_threshold).astype(np.uint8) * 255
            img_bgr = img_bgra[:, :, :3]  # Get BGR channels for potential later use
        else:
            print(
                "   Alpha channel present but appears opaque. Attempting background removal."
            )
            img_bgr = img_bgra[:, :, :3]  # Use the BGR part
            has_alpha = False  # Treat as if it doesn't have useful alpha
    else:
        print("   No alpha channel detected. Attempting background removal.")
        img_bgr = img_bgra  # Input is already BGR (or potentially grayscale)
        if channels != 3:
            print(
                f"   Warning: Image has {channels} channels but no alpha. Assuming BGR conversion is okay or it's grayscale."
            )
            # If grayscale, convert to BGR for consistency with color thresholding?
            if channels == 1:
                img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_GRAY2BGR)
                print("   Converted grayscale to BGR.")
            # Add handling for other channel counts if necessary

    # --- Method 2: Solid Background Removal (if alpha wasn't useful) ---
    # This part executes if mask is still None
    if mask is None and img_bgr is not None:
        print("   Attempting white background removal using Flood Fill.")

        # Make a copy for flood fill not to modify the original BGR needed later
        img_floodfill = img_bgr.copy()

        # Define parameters for flood fill
        # Background color assumption: White-ish. Check top-left pixel.
        # A more robust check could average corners or use dominant color.
        bg_color_sample = img_floodfill[0, 0]
        print(f"   Sample background color (top-left): {bg_color_sample}")

        # Tolerance for flood fill: how much the color can deviate
        # Adjust these values if background removal is not accurate
        # Lower values are stricter, higher values are more permissive.
        tolerance = (15, 15, 15)  # Allow some deviation from the seed color

        # Create a mask for flood fill (must be 2 pixels larger)
        h, w = img_floodfill.shape[:2]
        flood_mask = np.zeros((h + 2, w + 2), np.uint8)

        # Perform flood fill from the top-left corner (seed point)
        # cv2.FLOODFILL_MASK_ONLY means it doesn't change the image, only the mask
        # The filled area in flood_mask will be 1.
        try:
            cv2.floodFill(
                img_floodfill,
                flood_mask,
                (0, 0),
                newVal=1,
                loDiff=tolerance,
                upDiff=tolerance,
                flags=cv2.FLOODFILL_MASK_ONLY | (1 << 8),
            )  # newVal=1, flag sets mask[x,y]=1
        except Exception as e:
            print(f"   Error during flood fill: {e}. Trying simple thresholding.")
            # --- Fallback: Simple White Thresholding (Less Robust) ---
            lower_white = np.array([240, 240, 240], dtype=np.uint8)
            upper_white = np.array([255, 255, 255], dtype=np.uint8)
            background_mask_simple = cv2.inRange(img_bgr, lower_white, upper_white)
            mask = cv2.bitwise_not(background_mask_simple)  # Objects are white
            if np.sum(mask) == 0:  # Check if thresholding failed completely
                print(
                    f"   White thresholding failed to find any foreground objects for {image_path.name}."
                )
                return  # Skip this image

        if (
            mask is None
        ):  # If flood fill didn't error and simple thresholding wasn't used
            # The flood fill mask has 1 where the background was filled.
            # Extract the relevant part (excluding the 1-pixel border)
            # Invert it so objects are white (255) and background is black (0)
            mask = (1 - flood_mask[1:-1, 1:-1]).astype(np.uint8) * 255

            # Check if flood fill identified anything as foreground
            if np.sum(mask) == 0:
                print(
                    f"   Flood fill did not find any foreground objects for {image_path.name}. Is the background uniform and connected to the corner?"
                )
                # Optional: Save debug images of img_bgr and flood_mask here
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_floodfill_input.png"), img_bgr)
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_floodfill_mask_raw.png"), flood_mask * 255)
                return  # Skip this image

    # If no mask could be generated by either method, skip
    if mask is None:
        print(f"   Could not generate a mask for {image_path.name}. Skipping.")
        return

    # --- Morphological Operations to Clean Mask (Applied to mask from either method) ---
    kernel_size = 3
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask_opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_cleaned = cv2.morphologyEx(
        mask_opened, cv2.MORPH_CLOSE, kernel, iterations=2
    )  # Maybe 2 iterations for closing

    # --- Find Connected Components (Individual Clip Arts) ---
    labels = measure.label(mask_cleaned, connectivity=2, background=0)

    # --- Filter and Extract Regions ---
    regions = measure.regionprops(labels)
    min_area_ratio = 0.001  # Adjust as needed - smaller value allows smaller objects
    min_size = max(
        50, height * width * min_area_ratio
    )  # Ensure a minimum pixel area too
    valid_regions = [r for r in regions if r.area >= min_size]

    if not valid_regions:
        print(
            f"   Warning: No distinct regions found in '{image_path.name}' above the minimum size threshold ({min_size} pixels)."
        )
        debug_mask_path = (
            debug_dir / f"{image_path.stem}_debug_mask_cleaned_no_regions.png"
        )
        cv2.imwrite(str(debug_mask_path), mask_cleaned)
        print(f"   Saved cleaned mask for debugging: {debug_mask_path}")
        return

    valid_regions.sort(key=lambda x: (x.centroid[0], x.centroid[1]))
    print(f"   Found {len(valid_regions)} potential illustrations.")

    # --- Extract, Pad, and Save Each Region ---
    for i, region in enumerate(valid_regions):
        minr, minc, maxr, maxc = region.bbox
        padding = 10
        minr_pad = max(0, minr - padding)
        minc_pad = max(0, minc - padding)
        maxr_pad = min(height, maxr + padding)  # Use height/width from original image
        maxc_pad = min(width, maxc + padding)

        # --- Create a refined mask for the *extracted* region ---
        region_mask = (
            labels[minr_pad:maxr_pad, minc_pad:maxc_pad] == region.label
        ).astype(np.uint8) * 255

        # --- Create the final illustration with transparency ---
        # We need the BGR(A) data from the *original* loaded image
        # If original had alpha, use it, otherwise use the BGR version
        source_img_for_extraction = img_bgra if has_alpha else img_bgr

        # Extract the padded region from the source image (might be 3 or 4 channel)
        illustration_extracted = source_img_for_extraction[
            minr_pad:maxr_pad, minc_pad:maxc_pad
        ]

        # Ensure we have BGR channels
        if illustration_extracted.shape[2] == 4:
            illustration_bgr_part = illustration_extracted[:, :, :3]
        else:
            illustration_bgr_part = illustration_extracted

        # Create the final 4-channel BGRA image
        # Merge the BGR channels with the specific region_mask as the alpha channel
        if (
            illustration_bgr_part.shape[0] == region_mask.shape[0]
            and illustration_bgr_part.shape[1] == region_mask.shape[1]
        ):
            try:
                final_illustration = cv2.merge((illustration_bgr_part, region_mask))
            except Exception as merge_error:
                print(
                    f"Error merging BGR and mask for region {i+1} of {image_path.name}: {merge_error}"
                )
                print(
                    f"BGR part shape: {illustration_bgr_part.shape}, Mask shape: {region_mask.shape}"
                )
                continue  # Skip this region if merge fails
        else:
            print(f"   Skipping region {i+1} due to shape mismatch during final merge:")
            print(f"      BGR shape: {illustration_bgr_part.shape}")
            print(f"      Mask shape: {region_mask.shape}")
            continue  # Skip this region

        # Generate output filename
        base_name = image_path.stem
        output_filename = f"{base_name}_illustration_{i+1}.png"
        output_path = output_dir / output_filename

        # Save the illustration as PNG (which supports alpha)
        try:
            if final_illustration.size == 0:
                print(f"   Skipping empty region {i+1} for {image_path.name}")
                continue
            # Add a check: if the region mask is all black, maybe skip saving?
            if np.sum(region_mask) < 10:  # Avoid saving tiny specs or empty masks
                print(
                    f"   Skipping region {i+1} for {image_path.name} due to near-empty mask."
                )
                continue

            cv2.imwrite(str(output_path), final_illustration)
            print(f"   Saved: {output_path}")
        except Exception as e:
            print(f"   Error saving {output_path}: {e}")

        # --- Optional: Debug Visualization ---
        # (Keep the debug plot logic mostly the same, but ensure images are displayable)
        try:
            plt.figure(figsize=(15, 5))

            plt.subplot(1, 4, 1)
            plt.imshow(mask_cleaned, cmap="gray")
            plt.title("Cleaned Mask (Overall)")

            plt.subplot(1, 4, 2)
            plt.imshow(region_mask, cmap="gray")
            plt.title(f"Region {i+1} Mask")

            plt.subplot(1, 4, 3)
            if final_illustration.size > 0:
                # Convert BGRA to RGBA for matplotlib
                display_img = cv2.cvtColor(final_illustration, cv2.COLOR_BGRA2RGBA)
                plt.imshow(display_img)
            plt.title(f"Extracted {i+1}")
            plt.axis("off")

            plt.subplot(1, 4, 4)
            # Draw on the BGR version of the original image
            debug_img_draw = img_bgr.copy()  # Use the 3-channel version
            cv2.rectangle(
                debug_img_draw,
                (minc_pad, minr_pad),
                (maxc_pad, maxr_pad),
                (0, 255, 0),
                2,
            )  # Padded box
            cv2.rectangle(
                debug_img_draw, (minc, minr), (maxc, maxr), (0, 0, 255), 1
            )  # Original bbox
            plt.imshow(cv2.cvtColor(debug_img_draw, cv2.COLOR_BGR2RGB))
            plt.title("Detection on Original (BGR)")

            debug_plot_path = debug_dir / f"{base_name}_debug_region_{i+1}.png"
            plt.tight_layout()
            plt.savefig(str(debug_plot_path))
            plt.close()
        except Exception as e:
            print(f"   Error generating debug plot for region {i+1}: {e}")
            plt.close()


def main():
    """Main function to process all images in input directory"""
    input_dir = Path("input")
    output_dir, debug_dir = create_output_dir()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory '{input_dir}' not found or is not a directory.")
        print("Please create it and add image files.")
        return

    delete_identifier_files(input_dir)

    # Process common image types that might contain clipart
    image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
    images = [
        f
        for f in input_dir.iterdir()
        if f.suffix.lower() in image_extensions and f.is_file()
    ]

    if not images:
        print(
            f"No images found with extensions {image_extensions} in input directory '{input_dir}'."
        )
        return

    print(f"Found {len(images)} candidate images to process...")

    for image_path in images:
        extract_illustrations(image_path, output_dir, debug_dir)

    print("\nProcessing complete!")


if __name__ == "__main__":
    main()
