import warnings
from PIL import Image

warnings.simplefilter("ignore", Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

#############################
# IMAGE MOCKUP FUNCTIONS
#############################


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
    Reads a BGRA mockup with a transparent region, crops the input image (without warping)
    to match the transparent area's aspect ratio, resizes it to fill the area, and composites
    the mockup on top. Saves the result as a PNG.
    """
    input_bgr = cv2.imread(input_img_path)
    if input_bgr is None:
        print(f"Error loading input image: {input_img_path}")
        return False

    mockup_bgra = cv2.imread(mockup_img_path, cv2.IMREAD_UNCHANGED)
    if mockup_bgra is None or mockup_bgra.shape[2] < 4:
        print(f"Error loading mockup or no alpha channel: {mockup_img_path}")
        return False

    x, y, w, h = find_transparent_region(mockup_bgra)
    if w <= 0 or h <= 0:
        print(f"No valid transparent region found in mockup: {mockup_img_path}")
        return False

    input_h, input_w = input_bgr.shape[:2]
    target_aspect = w / float(h)
    input_aspect = input_w / float(input_h) if input_h != 0 else 1.0

    if input_aspect > target_aspect:
        new_width = int(input_h * target_aspect)
        offset_x = (input_w - new_width) // 2
        crop = input_bgr[:, offset_x : offset_x + new_width]
    elif input_aspect < target_aspect:
        new_height = int(input_w / target_aspect)
        offset_y = (input_h - new_height) // 2
        crop = input_bgr[offset_y : offset_y + new_height, :]
    else:
        crop = input_bgr

    resized_bgr = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)
    resized_bgra = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2BGRA)

    background_bgra = np.zeros_like(mockup_bgra, dtype=np.uint8)
    background_bgra[:, :, 0:3] = 255
    background_bgra[:, :, 3] = 255

    background_bgra[y : y + h, x : x + w] = resized_bgra
    final_bgra = alpha_composite(mockup_bgra, background_bgra)
    cv2.imwrite(output_path, final_bgra)
    print(f"Created image mockup: {output_path}")
    return True


#############################
# VIDEO MOCKUP FUNCTION
#############################


def create_video_mockup(
    input_img_path,
    output_video_path,
    fps=30,
    video_duration=10,
    horizontal_pan_factor=1.0,
    vertical_pan_factor=1.0,
):
    """
    Creates a video mockup that shows a high-detail view of the input image.

    The video is square (1080x1080) and has two segments:
      Segment 1 (Horizontal Pan): The crop window pans slowly from the image’s center toward the left.
      Segment 2 (Vertical Pan): Then the crop window pans slowly from the bottom (centered horizontally) up to the center.

    The input image is first cropped to a square (cover effect) and then further cropped with a fixed zoom factor.

    The horizontal_pan_factor and vertical_pan_factor parameters (values between 0 and 1)
    control the fraction of the maximum available pan distance to travel.
      - A factor of 1.0 pans the full distance from center to edge.
      - A factor less than 1.0 pans a shorter distance, resulting in a slower perceived movement.
    """
    video_width = 1080
    video_height = 1080
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    total_frames = int(fps * video_duration)

    # We'll divide the video into two segments:
    seg1_frames = total_frames // 2  # first half: horizontal pan from center to left
    seg2_frames = (
        total_frames - seg1_frames
    )  # second half: vertical pan from bottom to center

    # Load the input image and crop it to a square (cover effect)
    img = cv2.imread(input_img_path)
    if img is None:
        print(f"Error loading input image for video: {input_img_path}")
        return

    img_h, img_w = img.shape[:2]
    if img_w > img_h:
        offset_x = (img_w - img_h) // 2
        square = img[:, offset_x : offset_x + img_h]
    elif img_h > img_w:
        offset_y = (img_h - img_w) // 2
        square = img[offset_y : offset_y + img_w, :]
    else:
        square = img.copy()
    sq_h, sq_w = square.shape[:2]  # sq_h == sq_w

    # Set a zoom factor to show high detail; this determines the crop size used in animation.
    zoom_factor = 1
    crop_w_target = video_width / zoom_factor
    crop_h_target = video_height / zoom_factor

    # --- Segment 1: Horizontal Pan (center to left) ---
    # Original centers:
    center_start_x = sq_w / 2
    # Maximum travel would move the center to the far left, i.e. crop entirely flush:
    full_pan_distance = (sq_w / 2) - (crop_w_target / 2)
    # Apply horizontal_pan_factor to reduce travel distance:
    center_end_x = center_start_x - horizontal_pan_factor * full_pan_distance
    center_y_fixed = sq_h / 2

    seg1_frames_list = []
    for i in range(seg1_frames):
        t = i / (seg1_frames - 1) if seg1_frames > 1 else 0
        center_x = center_start_x + t * (center_end_x - center_start_x)
        center_y = center_y_fixed
        x1 = int(center_x - crop_w_target / 2)
        y1 = int(center_y - crop_h_target / 2)
        x2 = x1 + int(crop_w_target)
        y2 = y1 + int(crop_h_target)
        # Clamp crop within boundaries:
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(sq_w, x2)
        y2 = min(sq_h, y2)
        crop_frame = square[y1:y2, x1:x2]
        frame = cv2.resize(
            crop_frame, (video_width, video_height), interpolation=cv2.INTER_AREA
        )
        seg1_frames_list.append(frame)

    # --- Segment 2: Vertical Pan (bottom to center) ---
    # Original vertical centers:
    center_start_y = sq_h - (crop_h_target / 2)
    full_vertical_distance = center_start_y - (sq_h / 2)
    center_end_y = center_start_y - vertical_pan_factor * full_vertical_distance
    center_x_fixed = sq_w / 2

    seg2_frames_list = []
    for i in range(seg2_frames):
        t = i / (seg2_frames - 1) if seg2_frames > 1 else 0
        center_y = center_start_y + t * (center_end_y - center_start_y)
        center_x = center_x_fixed
        x1 = int(center_x - crop_w_target / 2)
        y1 = int(center_y - crop_h_target / 2)
        x2 = x1 + int(crop_w_target)
        y2 = y1 + int(crop_h_target)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(sq_w, x2)
        y2 = min(sq_h, y2)
        crop_frame = square[y1:y2, x1:x2]
        frame = cv2.resize(
            crop_frame, (video_width, video_height), interpolation=cv2.INTER_AREA
        )
        seg2_frames_list.append(frame)

    all_frames = seg1_frames_list + seg2_frames_list

    video_writer = cv2.VideoWriter(
        output_video_path, fourcc, fps, (video_width, video_height)
    )
    for frame in all_frames:
        video_writer.write(frame)
    video_writer.release()
    print(f"Created video mockup: {output_video_path}")


#############################
# MAIN PROCESSING
#############################


def process_all_mockups():
    """
    Processes images from /input:
      1. For each input image, creates a subfolder (named after the image's base name)
         inside /mockups_output.
      2. Creates image mockups using either 'mockups_portrait' or 'mockups_landscape'
         and saves them to the subfolder.
      3. Creates a video mockup for the input image and saves it to the same subfolder.
    """
    input_dir = "input"
    mockups_portrait_dir = "mockups_portrait"
    mockups_landscape_dir = "mockups_landscape"
    mockups_output_dir = "mockups_output"

    Path(mockups_output_dir).mkdir(parents=True, exist_ok=True)

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
        base_name = os.path.splitext(file)[0]
        output_subfolder = os.path.join(mockups_output_dir, base_name)
        Path(output_subfolder).mkdir(parents=True, exist_ok=True)

        with Image.open(input_img_path) as img:
            width, height = img.size
            is_portrait = height > width

        # Process image mockups
        if is_portrait:
            mockups = portrait_mockups
            mockups_dir = mockups_portrait_dir
        else:
            mockups = landscape_mockups
            mockups_dir = mockups_landscape_dir

        if not mockups:
            orientation_str = "portrait" if is_portrait else "landscape"
            print(
                f"No {orientation_str} mockups found for {file}, skipping image mockups."
            )
        else:
            for mockup_file in mockups:
                mockup_path = os.path.join(mockups_dir, mockup_file)
                mockup_name = os.path.splitext(mockup_file)[0]
                output_filename = f"{base_name}_in_{mockup_name}.png"
                output_path = os.path.join(output_subfolder, output_filename)
                place_image_in_mockup(input_img_path, mockup_path, output_path)

        # Process video mockup for this image.
        # Adjust the pan factors here to control speed:
        # For slower horizontal movement, use a smaller horizontal_pan_factor (e.g., 0.3)
        # For slower vertical movement, use a smaller vertical_pan_factor (e.g., 0.3)
        video_output_filename = f"{base_name}_video.mp4"
        video_output_path = os.path.join(output_subfolder, video_output_filename)
        create_video_mockup(
            input_img_path,
            video_output_path,
            fps=30,
            video_duration=10,
            horizontal_pan_factor=0.3,
            vertical_pan_factor=0.3,
        )

    print("All done processing both image and video mockups.")


if __name__ == "__main__":
    process_all_mockups()
