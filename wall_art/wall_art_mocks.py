import warnings
from PIL import Image, ImageDraw, ImageFont

warnings.simplefilter("ignore", Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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


def alpha_composite(foreground, background):
    alpha = foreground[:, :, 3] / 255.0
    for c in range(3):
        background[:, :, c] = (1.0 - alpha) * background[:, :, c] + alpha * foreground[
            :, :, c
        ]
    return background


#############################
# VIDEO MOCKUP FUNCTION
#############################


def alpha_composite(foreground, background):
    alpha = foreground[:, :, 3] / 255.0
    for c in range(3):
        background[:, :, c] = (1.0 - alpha) * background[:, :, c] + alpha * foreground[
            :, :, c
        ]
    return background


def create_video_mockup(
    input_img_path,
    output_video_path,
    fps=30,
    video_duration=10,
):
    video_width = 1080
    video_height = 1080
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    total_frames = int(fps * video_duration)

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

    # Simplified animation: start zoomed in to center, then zoom out
    # Initial zoom factor (more zoomed in)
    start_zoom = 0.3  # Small value = more zoomed in
    # Final zoom factor (zoomed out)
    end_zoom = 1.0  # Larger value = more zoomed out

    video_writer = cv2.VideoWriter(
        output_video_path, fourcc, fps, (video_width, video_height)
    )

    for i in range(total_frames):
        t = i / (total_frames - 1) if total_frames > 1 else 0
        # Interpolate zoom factor from start_zoom to end_zoom
        current_zoom = start_zoom + t * (end_zoom - start_zoom)

        # Calculate crop size based on current zoom
        crop_size = int(sq_w * current_zoom)

        # Center crop
        center_x = sq_w // 2
        center_y = sq_h // 2

        x1 = center_x - crop_size // 2
        y1 = center_y - crop_size // 2
        x2 = x1 + crop_size
        y2 = y1 + crop_size

        # Ensure crop is within image boundaries
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(sq_w, x2)
        y2 = min(sq_h, y2)

        # Extract and resize crop
        crop_frame = square[y1:y2, x1:x2]
        frame = cv2.resize(
            crop_frame, (video_width, video_height), interpolation=cv2.INTER_AREA
        )
        video_writer.write(frame)

    video_writer.release()
    print(f"Created video mockup: {output_video_path}")


def create_square_text_mockup(input_img_path, output_path):
    """
    Creates a 1:1 square mockup of the input image with text overlay.
    Final canvas size is 2048x2048 pixels.
    Adds "DIGITAL VEIL" (underlined) and "Vintage Art Collection" at the bottom.
    Text has a black bevel/shadow effect for readability.
    """
    # Load the input image
    img = Image.open(input_img_path)

    # Crop to square (from center)
    width, height = img.size
    if width > height:
        left = (width - height) // 2
        right = left + height
        img = img.crop((left, 0, right, height))
    elif height > width:
        top = (height - width) // 2
        bottom = top + width
        img = img.crop((0, top, width, bottom))

    # Resize to 2048x2048
    img = img.resize((2048, 2048), Image.LANCZOS)

    # Create a drawing context
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        main_font_size = 150
        secondary_font_size = 80
        font_main = ImageFont.truetype("./fonts/Clattering.ttf", main_font_size)
        font_secondary = ImageFont.truetype(
            "./fonts/Clattering.ttf", secondary_font_size
        )
    except Exception as e:
        print("Error loading font, using default font.", e)
        font_main = ImageFont.load_default()
        font_secondary = ImageFont.load_default()

    # Text to display
    main_text = "Digital Veil"
    secondary_text = "Vintage Art Collection"

    # Calculate text dimensions
    main_bbox = draw.textbbox((0, 0), main_text, font=font_main)
    main_text_width = main_bbox[2] - main_bbox[0]
    main_text_height = main_bbox[3] - main_bbox[1]

    sec_bbox = draw.textbbox((0, 0), secondary_text, font=font_secondary)
    sec_text_width = sec_bbox[2] - sec_bbox[0]
    sec_text_height = sec_bbox[3] - sec_bbox[1]

    # Calculate positions
    img_width = 2048
    img_height = 2048

    main_x = (img_width - main_text_width) // 2
    main_y = img_height - main_text_height - sec_text_height - 70  # 70px from bottom

    # Underline offset - increase this value to move the underline down
    underline_offset = 15  # Increased from 5

    sec_x = (img_width - sec_text_width) // 2
    sec_y = (
        main_y + main_text_height + underline_offset + 10
    )  # Adjusted to account for underline position

    # Draw text shadow/bevel effect for main text (offset by 2px)
    shadow_offset = 2
    draw.text(
        (main_x + shadow_offset, main_y + shadow_offset),
        main_text,
        font=font_main,
        fill=(0, 0, 0),
    )

    # Draw main text
    draw.text((main_x, main_y), main_text, font=font_main, fill=(255, 255, 255))

    # Draw underline for main text with shadow effect
    line_y = main_y + main_text_height + underline_offset
    line_thickness = 3
    draw.line(
        [
            (main_x + shadow_offset, line_y + shadow_offset),
            (main_x + main_text_width + shadow_offset, line_y + shadow_offset),
        ],
        fill=(0, 0, 0),
        width=line_thickness,
    )
    draw.line(
        [(main_x, line_y), (main_x + main_text_width, line_y)],
        fill=(255, 255, 255),
        width=line_thickness,
    )

    # Draw text shadow/bevel effect for secondary text
    draw.text(
        (sec_x + shadow_offset, sec_y + shadow_offset),
        secondary_text,
        font=font_secondary,
        fill=(0, 0, 0),
    )

    # Draw secondary text
    draw.text((sec_x, sec_y), secondary_text, font=font_secondary, fill=(255, 255, 255))

    # Save the result
    img.save(output_path)
    print(f"Created square text mockup: {output_path} (2048x2048)")
    return True


#############################
# MAIN PROCESSING
#############################


def process_all_mockups():
    """
    Processes images from /input:
      1. For each input image, creates a subfolder (named after the image's base name)
         inside /output.
      2. Within that folder, creates another subfolder named {base_name}_mocks
         to store all mockups.
      3. Creates image mockups using either 'mockups_portrait' or 'mockups_landscape'
         and saves them to the subfolder.
      4. Creates a square text mockup with "DIGITAL VEIL" text overlay.
      5. Creates a video mockup for the input image and saves it to the same subfolder.
    """
    input_dir = "input"
    mockups_portrait_dir = "mockups_portrait"
    mockups_landscape_dir = "mockups_landscape"
    output_dir = "output"

    # Ensure the main output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

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

        # Create /output/{base_name} folder
        output_base_folder = os.path.join(output_dir, base_name)
        Path(output_base_folder).mkdir(parents=True, exist_ok=True)

        # Create /output/{base_name}/{base_name}_mocks folder
        output_mocks_folder = os.path.join(output_base_folder, f"{base_name}_mocks")
        Path(output_mocks_folder).mkdir(parents=True, exist_ok=True)

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
                output_path = os.path.join(output_mocks_folder, output_filename)
                place_image_in_mockup(input_img_path, mockup_path, output_path)

        # Create square text mockup
        square_output_filename = f"{base_name}_digital_veil.png"
        square_output_path = os.path.join(output_mocks_folder, square_output_filename)
        create_square_text_mockup(input_img_path, square_output_path)

        # Process video mockup for this image
        video_output_filename = f"{base_name}_video.mp4"
        video_output_path = os.path.join(output_mocks_folder, video_output_filename)
        create_video_mockup(
            input_img_path,
            video_output_path,
            fps=30,
            video_duration=10,
        )

    print("All done processing both image and video mockups.")


if __name__ == "__main__":
    process_all_mockups()
