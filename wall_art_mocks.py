import warnings
from PIL import Image

warnings.simplefilter("ignore", Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image


def find_transparent_region(mockup_bgra):
    """
    Finds the bounding box of the largest fully-transparent region (alpha=0)
    in a BGRA mockup. Returns (x, y, w, h).
    If none found, returns (0, 0, 0, 0).
    """
    if mockup_bgra.shape[2] != 4:
        print("Mockup has no alpha channel (not a 4-channel image).")
        return 0, 0, 0, 0

    alpha = mockup_bgra[:, :, 3]
    transparent_mask = np.where(alpha == 0, 255, 0).astype(np.uint8)
    contours, _ = cv2.findContours(
        transparent_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        print("No transparent contours found in mockup.")
        return 0, 0, 0, 0

    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) < 10:
        print("Transparent contour is too small.")
        return 0, 0, 0, 0

    x, y, w, h = cv2.boundingRect(largest_contour)
    return x, y, w, h


def alpha_composite(foreground_bgra, background_bgra):
    """
    Alpha-composite foreground over background.
    Both images must be BGRA and the same size.
    Returns a BGRA result.
    """
    fg_b = foreground_bgra[:, :, 0].astype(float)
    fg_g = foreground_bgra[:, :, 1].astype(float)
    fg_r = foreground_bgra[:, :, 2].astype(float)
    fg_a = foreground_bgra[:, :, 3].astype(float) / 255.0

    bg_b = background_bgra[:, :, 0].astype(float)
    bg_g = background_bgra[:, :, 1].astype(float)
    bg_r = background_bgra[:, :, 2].astype(float)
    bg_a = background_bgra[:, :, 3].astype(float) / 255.0

    out_a = fg_a + bg_a * (1 - fg_a)
    eps = 1e-6

    out_r = (fg_r * fg_a + bg_r * bg_a * (1 - fg_a)) / (out_a + eps)
    out_g = (fg_g * fg_a + bg_g * bg_a * (1 - fg_a)) / (out_a + eps)
    out_b = (fg_b * fg_a + bg_b * bg_a * (1 - fg_a)) / (out_a + eps)

    out = np.zeros_like(foreground_bgra, dtype=np.uint8)
    out[:, :, 0] = np.clip(out_b, 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(out_g, 0, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(out_r, 0, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(out_a * 255, 0, 255).astype(np.uint8)
    return out


def place_image_in_mockup(input_img_path, mockup_img_path, output_path):
    """
    Reads a BGRA mockup that has a transparent rectangle for the "canvas".
    Crops the input image (without warping) to match the transparent area’s aspect ratio,
    then resizes the cropped region to exactly fill the area.
    The result is then composited with the mockup and saved as a PNG.
    """
    # Read input image as BGR
    input_bgr = cv2.imread(input_img_path)
    if input_bgr is None:
        print(f"Error loading input image: {input_img_path}")
        return False

    # Read mockup image with alpha channel
    mockup_bgra = cv2.imread(mockup_img_path, cv2.IMREAD_UNCHANGED)
    if mockup_bgra is None or mockup_bgra.shape[2] < 4:
        print(f"Error loading mockup or no alpha channel: {mockup_img_path}")
        return False

    # Find transparent region in the mockup
    x, y, w, h = find_transparent_region(mockup_bgra)
    if w <= 0 or h <= 0:
        print(f"No valid transparent region found in mockup: {mockup_img_path}")
        return False

    # Get dimensions of input image
    input_h, input_w = input_bgr.shape[:2]
    target_aspect = w / float(h)
    input_aspect = input_w / float(input_h) if input_h != 0 else 1.0

    # Crop the input image to match the target aspect ratio
    if input_aspect > target_aspect:
        # Input image is wider than needed; crop sides
        new_width = int(input_h * target_aspect)
        offset_x = (input_w - new_width) // 2
        crop = input_bgr[:, offset_x : offset_x + new_width]
    elif input_aspect < target_aspect:
        # Input image is taller; crop top and bottom
        new_height = int(input_w / target_aspect)
        offset_y = (input_h - new_height) // 2
        crop = input_bgr[offset_y : offset_y + new_height, :]
    else:
        # Aspect ratio matches exactly
        crop = input_bgr

    # Now, resize the cropped region to fill the transparent area exactly
    resized_bgr = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)
    # Convert resized image to BGRA
    resized_bgra = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2BGRA)

    # Prepare a background the same size as the mockup
    background_bgra = np.zeros_like(mockup_bgra, dtype=np.uint8)
    background_bgra[:, :, 0:3] = 255  # White background
    background_bgra[:, :, 3] = 255  # Fully opaque

    # Place the resized image into the transparent region
    background_bgra[y : y + h, x : x + w] = resized_bgra

    # Composite the mockup over the background
    final_bgra = alpha_composite(mockup_bgra, background_bgra)
    cv2.imwrite(output_path, final_bgra)
    print(f"Created mockup: {output_path}")
    return True


def process_input_images_with_mockups():
    """
    1. Reads images from /input.
    2. Checks orientation (portrait vs. landscape).
    3. Uses 'mockups_portrait' if portrait, 'mockups_landscape' if landscape.
    4. Saves results in 'mockups_output'.
    """
    input_dir = "input"
    mockups_portrait_dir = "mockups_portrait"
    mockups_landscape_dir = "mockups_landscape"
    mockups_output_dir = "mockups_output"

    Path(mockups_output_dir).mkdir(parents=True, exist_ok=True)

    # Gather mockups for portrait and landscape
    portrait_mockups = []
    landscape_mockups = []
    if os.path.exists(mockups_portrait_dir):
        portrait_mockups = [
            f for f in os.listdir(mockups_portrait_dir) if f.lower().endswith(".png")
        ]
    if os.path.exists(mockups_landscape_dir):
        landscape_mockups = [
            f for f in os.listdir(mockups_landscape_dir) if f.lower().endswith(".png")
        ]

    if not os.path.exists(input_dir):
        print(f"Input folder '{input_dir}' does not exist.")
        return

    for file in os.listdir(input_dir):
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        input_img_path = os.path.join(input_dir, file)
        with Image.open(input_img_path) as img:
            width, height = img.size
            is_portrait = height > width

        # Select the appropriate mockup directory based on orientation
        if is_portrait:
            mockups = portrait_mockups
            mockups_dir = mockups_portrait_dir
        else:
            mockups = landscape_mockups
            mockups_dir = mockups_landscape_dir

        if not mockups:
            orientation_str = "portrait" if is_portrait else "landscape"
            print(f"No {orientation_str} mockups found for {file}, skipping.")
            continue

        base_name = os.path.splitext(file)[0]
        for mockup_file in mockups:
            mockup_path = os.path.join(mockups_dir, mockup_file)
            mockup_name = os.path.splitext(mockup_file)[0]
            output_filename = f"{base_name}_in_{mockup_name}.png"
            output_path = os.path.join(mockups_output_dir, output_filename)
            place_image_in_mockup(input_img_path, mockup_path, output_path)

    print("All done.")


if __name__ == "__main__":
    process_input_images_with_mockups()
