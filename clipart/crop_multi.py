import cv2
import numpy as np
from pathlib import Path
from skimage import measure
import matplotlib.pyplot as plt  # Used for debug visualization


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
        # Try to use the centralized function from utils.common
        import sys
        import os

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        sys.path.insert(0, project_root)
        from utils.common import clean_identifier_files

        num_removed = clean_identifier_files(str(input_dir))
        print(f"Deleted {num_removed} identifier/system files")
    except ImportError:
        # Fallback to original implementation
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
    solid white/near-white backgrounds. Aims to preserve original alpha
    within extracted objects when available.
    """
    # Read image, preserving alpha channel if it exists
    img_original_unchanged = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img_original_unchanged is None:
        print(f"Error: Failed to load image: {image_path}")
        return

    # Store original shape and check for alpha
    if len(img_original_unchanged.shape) == 3 and img_original_unchanged.shape[2] == 4:
        height, width, _ = (
            img_original_unchanged.shape
        )  # _ for unused channels variable
        has_alpha = True
        img_bgr = img_original_unchanged[:, :, :3]  # Keep BGR for processing if needed
    elif (
        len(img_original_unchanged.shape) == 3 and img_original_unchanged.shape[2] == 3
    ):
        height, width, _ = (
            img_original_unchanged.shape
        )  # _ for unused channels variable
        has_alpha = False
        img_bgr = img_original_unchanged  # Already BGR
    elif len(img_original_unchanged.shape) == 2:  # Grayscale
        height, width = img_original_unchanged.shape
        # channels not needed here
        has_alpha = False
        img_bgr = cv2.cvtColor(
            img_original_unchanged, cv2.COLOR_GRAY2BGR
        )  # Convert for consistent processing
        print("   Converted grayscale to BGR for processing.")
    else:
        print(
            f"Error: Unexpected image shape {img_original_unchanged.shape} for {image_path.name}"
        )
        return

    print(f"Processing '{image_path.name}' ({width}x{height}, Alpha: {has_alpha})...")

    mask = None
    # mask_from_alpha flag was used for debugging but is no longer needed

    # --- Method 1: Try Alpha Channel ---
    if has_alpha:
        alpha = img_original_unchanged[:, :, 3]
        # Use a slightly more robust check: mean alpha < threshold OR min alpha very low
        if np.mean(alpha) < 250 or np.min(alpha) < 10:  # Adjust thresholds if needed
            print("   Using alpha channel for masking.")
            alpha_threshold = (
                1  # Pixels with alpha > 0 are considered part of an object
            )
            mask = (alpha >= alpha_threshold).astype(np.uint8) * 255
            # Flag was used for debugging but is no longer needed
        else:
            print(
                "   Alpha channel present but appears mostly opaque. Attempting background removal."
            )
            # Keep has_alpha=True, but mask_from_alpha remains False
            # We'll use img_bgr prepared earlier
    else:
        print("   No alpha channel detected. Attempting background removal.")
        # img_bgr is already prepared

    # --- Method 2: Solid Background Removal (if alpha wasn't useful) ---
    if mask is None:  # Executes if Method 1 didn't produce a mask
        print("   Attempting white background removal using Flood Fill.")
        # Ensure img_bgr exists (should always be true here if mask is None)
        if img_bgr is None:
            print(
                f"   Error: img_bgr not available for background removal on {image_path.name}"
            )
            return

        # Make a copy for flood fill not to modify the BGR image
        img_floodfill = img_bgr.copy()

        # Define parameters for flood fill (more robust check: check corners)
        corners = [
            img_floodfill[0, 0],
            img_floodfill[0, width - 1],
            img_floodfill[height - 1, 0],
            img_floodfill[height - 1, width - 1],
        ]
        # Let's assume the most frequent corner color is background, or just use top-left
        bg_color_sample = corners[0]  # Simple: use top-left
        # More robust: Calculate mode or average if they are similar
        # For now, stick to top-left for simplicity:
        print(f"   Sample background color (top-left): {bg_color_sample}")

        tolerance = (
            20,
            20,
            20,
            20,
        )  # Increased tolerance slightly (BGR + Alpha tolerance if needed, though not used here)
        # Create a mask for flood fill (must be 2 pixels larger)
        flood_mask = np.zeros((height + 2, width + 2), np.uint8)

        # Perform flood fill from the top-left corner
        try:
            cv2.floodFill(
                img_floodfill,
                flood_mask,
                (0, 0),
                newVal=1,  # Fill mask with 1
                loDiff=tolerance[:3],  # Use only BGR tolerance
                upDiff=tolerance[:3],
                flags=cv2.FLOODFILL_MASK_ONLY | (1 << 8),  # Write 1 to mask
            )
            # Check if flood fill actually did anything significant
            if np.sum(flood_mask) < (
                flood_mask.size * 0.01
            ):  # If less than 1% filled, maybe failed?
                print(
                    f"   Warning: Flood fill seemed ineffective (filled {np.sum(flood_mask)} pixels)."
                )
                # Optionally, try other corners or fallback to thresholding here
        except Exception as e:
            print(f"   Error during flood fill: {e}. Trying simple thresholding.")
            # --- Fallback: Simple White Thresholding (Less Robust) ---
            lower_white = np.array(
                [235, 235, 235], dtype=np.uint8
            )  # Slightly lower threshold
            upper_white = np.array([255, 255, 255], dtype=np.uint8)
            background_mask_simple = cv2.inRange(img_bgr, lower_white, upper_white)
            mask = cv2.bitwise_not(background_mask_simple)  # Objects are white
            if np.sum(mask) == 0:
                print(
                    f"   White thresholding failed to find any foreground objects for {image_path.name}."
                )
                return  # Skip this image
            else:
                print("   Used fallback simple white thresholding.")

        if mask is None:  # If flood fill ran without error and fallback wasn't used
            # The flood fill mask has 1 where the background was filled. Invert it.
            mask = (1 - flood_mask[1:-1, 1:-1]).astype(np.uint8) * 255

            # Check if flood fill identified anything as foreground
            if np.sum(mask) == 0:
                print(
                    f"   Flood fill did not find any foreground objects for {image_path.name}. Is the background uniform and connected to the corner?"
                )
                # Optional: Save debug images
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_floodfill_input.png"), img_bgr)
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_floodfill_mask_raw.png"), flood_mask[1:-1, 1:-1] * 255)
                return  # Skip this image
            else:
                print("   Used flood fill for masking.")

    # If no mask could be generated by any method, skip
    if mask is None:
        print(f"   Could not generate a mask for {image_path.name}. Skipping.")
        return

    # --- Morphological Operations to Clean Mask ---
    kernel_size = 3
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    # Opening removes small noise/speckles (erosion followed by dilation)
    mask_opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    # Closing fills small holes within objects (dilation followed by erosion)
    mask_cleaned = cv2.morphologyEx(
        mask_opened, cv2.MORPH_CLOSE, kernel, iterations=2
    )  # Increased iterations slightly

    # Optional: Save the intermediate masks for debugging
    # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_mask_initial.png"), mask)
    # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_mask_opened.png"), mask_opened)
    # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_mask_cleaned.png"), mask_cleaned)

    # --- Find Connected Components (Individual Clip Arts) ---
    labels = measure.label(mask_cleaned, connectivity=2, background=0)

    # --- Filter and Extract Regions ---
    regions = measure.regionprops(labels)
    min_area_ratio = 0.0005  # Reduced slightly to catch potentially smaller valid items
    min_abs_area = 30  # Absolute minimum pixel area
    min_size = max(
        min_abs_area, int(height * width * min_area_ratio)
    )  # Calculate min size
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

    valid_regions.sort(
        key=lambda x: (x.centroid[0], x.centroid[1])
    )  # Sort top-to-bottom, left-to-right
    print(f"   Found {len(valid_regions)} potential illustrations.")

    # --- Extract, Pad, and Save Each Region ---
    for i, region in enumerate(valid_regions):
        minr, minc, maxr, maxc = region.bbox
        padding = 5  # Reduced padding slightly, adjust if needed
        # Calculate padded coordinates, ensuring they stay within image bounds
        minr_pad = max(0, minr - padding)
        minc_pad = max(0, minc - padding)
        maxr_pad = min(height, maxr + padding)
        maxc_pad = min(width, maxc + padding)

        # --- Create a refined binary mask for *only this specific region* within the padded box ---
        # This isolates the current object from others that might be in the padded area
        region_mask = (
            labels[minr_pad:maxr_pad, minc_pad:maxc_pad] == region.label
        ).astype(np.uint8) * 255

        # --- Extract the corresponding region from the *original* image data ---
        # Always use the original loaded image (BGRA or BGR/Grayscale)
        illustration_extracted_padded = img_original_unchanged[
            minr_pad:maxr_pad, minc_pad:maxc_pad
        ]

        # --- Create the final illustration with proper transparency ---
        final_illustration = None
        try:
            # Separate BGR channels from the extracted padded region
            if (
                len(illustration_extracted_padded.shape) == 3
                and illustration_extracted_padded.shape[2] >= 3
            ):
                illustration_bgr_part = illustration_extracted_padded[:, :, :3]
            elif (
                len(illustration_extracted_padded.shape) == 2
            ):  # Handle case if original was grayscale and somehow extracted as 2D
                illustration_bgr_part = cv2.cvtColor(
                    illustration_extracted_padded, cv2.COLOR_GRAY2BGR
                )
            else:
                print(
                    f"  Skipping region {i+1}: Unexpected shape for extracted BGR part {illustration_extracted_padded.shape}"
                )
                continue

            # Ensure dimensions match before merging
            if illustration_bgr_part.shape[:2] != region_mask.shape[:2]:
                print(
                    f"  Skipping region {i+1}: Shape mismatch between BGR part {illustration_bgr_part.shape[:2]} and region mask {region_mask.shape[:2]}"
                )
                # This might happen if padding goes outside original image bounds in an unexpected way, though bounds check should prevent it.
                # Or if grayscale conversion wasn't handled correctly upstream.
                # Save debug images here if this error occurs frequently.
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_region_{i+1}_mismatch_bgr.png"), illustration_bgr_part)
                # cv2.imwrite(str(debug_dir / f"{image_path.stem}_debug_region_{i+1}_mismatch_mask.png"), region_mask)
                continue

            # *** KEY CHANGE HERE: Preserve original alpha if available and used ***
            if has_alpha:  # Original image had an alpha channel
                original_alpha_crop = illustration_extracted_padded[:, :, 3]
                # Combine original alpha with the region's mask using bitwise AND
                # This keeps original transparency *within* the object and makes *outside* transparent
                final_alpha = cv2.bitwise_and(original_alpha_crop, region_mask)
            else:  # Original had no alpha, or we didn't use it (used flood fill/threshold)
                # Use the derived binary region mask as the alpha channel
                final_alpha = region_mask

            # Merge the BGR channels with the calculated final alpha channel
            final_illustration = cv2.merge((illustration_bgr_part, final_alpha))

        except Exception as merge_error:
            print(
                f"Error processing/merging channels for region {i+1} of {image_path.name}: {merge_error}"
            )
            print(
                f"  Extracted padded shape: {illustration_extracted_padded.shape}, BGR part shape: {illustration_bgr_part.shape}, Region mask shape: {region_mask.shape}"
            )
            continue  # Skip this region if merge fails

        # --- Save the Result ---
        if final_illustration is None or final_illustration.size == 0:
            print(
                f"   Skipping empty or invalid final illustration for region {i+1} of {image_path.name}"
            )
            continue

        # Add a check: if the final alpha channel is nearly empty, skip saving
        # Use a small threshold to account for minor noise if needed
        if (
            np.sum(final_illustration[:, :, 3] > 10) < min_abs_area
        ):  # Check if significant pixels are non-transparent
            print(
                f"   Skipping region {i+1} for {image_path.name} due to near-empty final alpha channel."
            )
            continue

        # Generate output filename
        base_name = image_path.stem
        output_filename = f"{base_name}_illustration_{i+1}.png"
        output_path = output_dir / output_filename

        # Save the illustration as PNG (which supports alpha)
        try:
            cv2.imwrite(str(output_path), final_illustration)
            print(f"   Saved: {output_path}")
        except Exception as e:
            print(f"   Error saving {output_path}: {e}")
            print(
                f"   Final illustration shape before save: {final_illustration.shape}, dtype: {final_illustration.dtype}"
            )

        # --- Optional: Debug Visualization ---
        try:
            plt.figure(figsize=(18, 5))  # Adjusted size slightly

            plt.subplot(1, 4, 1)
            plt.imshow(mask_cleaned, cmap="gray")
            plt.title("Cleaned Mask (Overall)")

            plt.subplot(1, 4, 2)
            plt.imshow(region_mask, cmap="gray")
            plt.title(f"Region {i+1} Binary Mask")  # Clarified title

            plt.subplot(1, 4, 3)
            if final_illustration is not None and final_illustration.size > 0:
                # Convert final BGRA to RGBA for matplotlib display
                display_img = cv2.cvtColor(final_illustration, cv2.COLOR_BGRA2RGBA)
                plt.imshow(display_img)
                # Overlay a border representing the crop area
                # Get display image dims
                disp_h, disp_w = display_img.shape[:2]
                # Draw rectangle (coordinates are relative to the displayed image)
                rect = plt.Rectangle(
                    (0, 0),
                    disp_w - 1,
                    disp_h - 1,
                    fill=False,
                    edgecolor="lime",
                    linewidth=1,
                )
                plt.gca().add_patch(rect)

            plt.title(f"Extracted {i+1} (Final)")
            plt.axis("off")

            plt.subplot(1, 4, 4)
            # Draw bounding boxes on a BGR version of the original
            # Use the img_bgr we prepared earlier which is guaranteed 3-channel
            debug_img_draw = img_bgr.copy()
            # Draw padded box (green)
            cv2.rectangle(
                debug_img_draw,
                (minc_pad, minr_pad),
                (maxc_pad, maxr_pad),
                (0, 255, 0),
                2,  # Thicker line
            )
            # Draw original bbox (red) inside padded box
            cv2.rectangle(
                debug_img_draw,
                (minc, minr),
                (maxc, maxr),
                (0, 0, 255),
                1,
            )
            plt.imshow(cv2.cvtColor(debug_img_draw, cv2.COLOR_BGR2RGB))
            plt.title("Detection Boxes on Original (BGR)")

            debug_plot_path = debug_dir / f"{base_name}_debug_region_{i+1}.png"
            plt.tight_layout()
            plt.savefig(str(debug_plot_path))
            plt.close()  # Close the plot to free memory
        except Exception as e:
            print(f"   Error generating debug plot for region {i+1}: {e}")
            plt.close()  # Ensure plot is closed even if error occurs


def main():
    """Main function to process all images in input directory"""
    input_dir = Path("input")
    output_dir, debug_dir = create_output_dir()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory '{input_dir}' not found or is not a directory.")
        print("Please create it and add image files.")
        return

    delete_identifier_files(input_dir)  # Optional cleanup

    # Process common image types that might contain clipart
    image_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    )  # Added webp
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
