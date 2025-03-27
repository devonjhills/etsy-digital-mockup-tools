import os
import glob
import cv2  # Make sure opencv-python is installed: pip install opencv-python numpy
from PIL import Image, ImageFont, ImageDraw, ImageEnhance  # Pillow: pip install Pillow
import numpy as np
from typing import List, Tuple, Optional
import traceback  # For detailed error reporting

# --- Constants ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")

# Mockup Dimensions
OUTPUT_SIZE: Tuple[int, int] = (3000, 2250)
GRID_2x2_SIZE: Tuple[int, int] = (2000, 2000)
CELL_PADDING: int = 10

# Asset Paths
DEFAULT_LOGO_PATH: str = os.path.join(
    SCRIPT_DIR, "logo.png"
)  # Optional: used for watermark
CANVAS_PATH: str = os.path.join(SCRIPT_DIR, "canvas.png")  # Background canvas image
OVERLAY_PATH: str = os.path.join(
    SCRIPT_DIR, "clip_overlay.png"
)  # Path to your specific title overlay
TRANSPARENCY_MOCKUP_PATH: str = os.path.join(
    SCRIPT_DIR, "transparency_mock.png"
)  # Background for transparency demo
FONT_PATH: str = os.path.join(
    SCRIPT_DIR, "fonts/Free Version Angelina.ttf"  # Path to your desired TTF font file
)

# Watermark Settings (if using logo.png)
WATERMARK_DEFAULT_OPACITY: int = 45
WATERMARK_SPACING_MULTIPLIER: int = 3
WATERMARK_SIZE_RATIO: float = 1 / 12

# Title Settings
TITLE_STARTING_FONT_SIZE: int = 250  # Initial size to try for the title
TITLE_MIN_FONT_SIZE: int = 20  # Smallest font size allowed
TITLE_LINE_SPACING: int = 20  # Vertical pixels between the two lines of the title
TITLE_FONT_STEP: int = 5  # How much to decrease font size when trying to fit text

# --- Dynamic Text Area Detection Settings ---
# Threshold to consider a pixel non-background (0-255). Adjust if overlay analysis fails.
BOUNDS_DETECTION_THRESHOLD: int = 20
# Inner padding from the detected overlay bounds to the actual text box.
# Adjust this value (e.g., 20-50) to control text proximity to the overlay frame.
TEXT_AREA_INNER_PADDING: int = 35

# Video Settings
VIDEO_TARGET_SIZE: Tuple[int, int] = (2000, 2000)  # Output resolution for video
VIDEO_FPS: int = 30  # Frames per second
VIDEO_TRANSITION_FRAMES: int = 30  # Duration of cross-fade (in frames)
VIDEO_DISPLAY_FRAMES: int = 60  # Duration each image is shown (in frames)

# --- Helper Functions ---


def safe_load_image(path: str, mode: str = "RGBA") -> Optional[Image.Image]:
    """Loads an image safely, returning None if file not found or invalid."""
    if not os.path.exists(path):
        print(f"Warning: Asset not found at {path}")
        return None
    try:
        img = Image.open(path)
        # Ensure image has an alpha channel for consistent processing
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        return img
    except Exception as e:
        print(f"Warning: Could not load or convert image at {path}. Error: {e}")
        return None


# --- Core Image Processing Functions ---


def load_images(image_paths: List[str]) -> List[Image.Image]:
    """Load images from paths, skipping invalid ones."""
    loaded = []
    for path in image_paths:
        img = safe_load_image(path, "RGBA")
        if img:
            loaded.append(img)
    return loaded


def apply_watermark(
    image: Image.Image,
    logo_path: str = DEFAULT_LOGO_PATH,
    opacity: int = WATERMARK_DEFAULT_OPACITY,
    spacing_multiplier: int = WATERMARK_SPACING_MULTIPLIER,
    logo_size_ratio: float = WATERMARK_SIZE_RATIO,
) -> Image.Image:
    """
    Apply logo watermark in a grid pattern to the image.

    Args:
        image: The PIL Image to watermark.
        logo_path: Path to the logo file.
        opacity: Watermark opacity percentage (0-100).
        spacing_multiplier: Multiplier for spacing based on logo size.
        logo_size_ratio: Desired logo width as a fraction of the image width.

    Returns:
        The watermarked PIL Image.
    """
    if not isinstance(image, Image.Image):
        print("Warning: Invalid image passed to apply_watermark.")
        return image  # Return original if invalid

    base_image = image.convert("RGBA")
    watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))

    # Load and resize logo
    logo = safe_load_image(logo_path, "RGBA")
    if not logo:
        print("Warning: Watermark logo could not be loaded. Skipping watermark.")
        return base_image

    logo_width = int(base_image.width * logo_size_ratio)
    if logo_width <= 0:
        print("Warning: Calculated logo width is zero or negative. Skipping watermark.")
        return base_image
    try:
        logo_height = int(logo_width * logo.height / logo.width)
        if logo_height <= 0:
            print(
                "Warning: Calculated logo height is zero or negative. Skipping watermark."
            )
            return base_image
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    except ZeroDivisionError:
        print("Warning: Logo has zero width or height. Skipping watermark.")
        return base_image
    except Exception as e:
        print(f"Warning: Error resizing logo: {e}. Skipping watermark.")
        return base_image

    # Set opacity
    try:
        alpha = logo.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(
            max(0, min(100, opacity)) / 100.0
        )
        logo.putalpha(alpha)
    except IndexError:
        print(
            "Warning: Could not process logo alpha channel (might not have one). Using original transparency."
        )
    except Exception as e:
        print(f"Warning: Error setting watermark opacity: {e}")

    # Create watermark grid
    spacing_x = int(logo_width * spacing_multiplier)
    spacing_y = int(logo_height * spacing_multiplier)

    # Ensure spacing is positive
    if spacing_x <= 0:
        spacing_x = logo_width * 2
    if spacing_y <= 0:
        spacing_y = logo_height * 2

    # Extend range slightly for better edge coverage
    y_start, y_end = -int(logo_height * 1.5), base_image.height + spacing_y
    x_start, x_end = -int(logo_width * 1.5), base_image.width + spacing_x

    for y in range(y_start, y_end, spacing_y):
        # Offset every other row
        offset_x = (y // spacing_y % 2) * (spacing_x // 2)
        for x in range(x_start + offset_x, x_end + offset_x, spacing_x):
            try:
                # Use logo alpha channel as mask for transparency
                watermark_layer.paste(logo, (x, y), logo)
            except Exception as e:
                print(f"Warning: Error pasting watermark at ({x},{y}): {e}")

    return Image.alpha_composite(base_image, watermark_layer)


def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = GRID_2x2_SIZE,
    padding: int = CELL_PADDING,
) -> Image.Image:
    """
    Create a 2x2 grid layout from the first 4 image paths on a canvas.

    Args:
        input_image_paths: List of paths to input images.
        canvas_bg_image: The background canvas PIL Image (already loaded and sized).
        grid_size: The target size of the grid canvas.
        padding: Padding around each cell image.

    Returns:
        The 2x2 grid PIL Image.
    """
    grid_img = canvas_bg_image.copy()

    if not input_image_paths:
        print("Info: No input images provided for 2x2 grid.")
        return grid_img

    num_cols, num_rows = 2, 2

    # Calculate cell dimensions
    total_padding_width = padding * (num_cols + 1)
    total_padding_height = padding * (num_rows + 1)
    cell_width = (grid_size[0] - total_padding_width) // num_cols
    cell_height = (grid_size[1] - total_padding_height) // num_rows

    if cell_width <= 0 or cell_height <= 0:
        print(
            "Warning: Grid size too small for padding and cells. Returning blank canvas."
        )
        return grid_img

    for idx, img_path in enumerate(input_image_paths[:4]):
        row, col = idx // num_cols, idx % num_cols

        cell_x_start = padding + col * (cell_width + padding)
        cell_y_start = padding + row * (cell_height + padding)

        img = safe_load_image(img_path, "RGBA")
        if not img:
            print(f"Warning: Skipping image {img_path} in 2x2 grid (load failed).")
            continue

        # Calculate resize dimensions preserving aspect ratio
        target_width, target_height = cell_width, cell_height
        try:
            img_aspect = img.width / img.height
            cell_aspect = cell_width / cell_height

            if img_aspect > cell_aspect:  # Image wider than cell
                target_height = int(cell_width / img_aspect)
            else:  # Image taller than cell
                target_width = int(cell_height * img_aspect)
        except ZeroDivisionError:
            print(f"Warning: Skipping image {img_path} due to zero dimension.")
            continue

        # Ensure positive dimensions
        if target_width <= 0 or target_height <= 0:
            print(f"Warning: Skipping image {img_path} due to invalid resize calc.")
            continue

        resized = img.resize((target_width, target_height), Image.LANCZOS)

        # Center resized image within the cell
        x_offset = (cell_width - target_width) // 2
        y_offset = (cell_height - target_height) // 2
        paste_x = cell_x_start + x_offset
        paste_y = cell_y_start + y_offset

        try:
            # Use resized image's alpha as mask
            grid_img.paste(resized, (paste_x, paste_y), resized)
        except Exception as e:
            print(f"Warning: Error pasting image {img_path} into 2x2 grid: {e}")

    return grid_img


def create_main_grid(
    images: List[Image.Image],
    canvas_bg_image: Image.Image,
    canvas_size: Tuple[int, int] = OUTPUT_SIZE,
) -> Image.Image:
    """
    Create a main grid layout (2x3 or 3x2) for up to 6 images.

    Args:
        images: List of loaded PIL Images (up to 6).
        canvas_bg_image: The background canvas PIL Image (already loaded and sized).
        canvas_size: The target size of the main grid canvas.

    Returns:
        The main grid PIL Image.
    """
    canvas = canvas_bg_image.copy()
    images_to_use = images[:6]

    if not images_to_use:
        print("Info: No images provided for main grid.")
        return canvas

    # Determine grid layout based on average aspect ratio
    try:
        aspect_ratios = [
            img.width / img.height for img in images_to_use if img.height > 0
        ]
        avg_aspect = sum(aspect_ratios) / len(aspect_ratios) if aspect_ratios else 1.0
    except ZeroDivisionError:
        avg_aspect = 1.0  # Default if height is zero

    grid_cols = 3 if avg_aspect <= 1 else 2  # More columns for portrait/square
    grid_rows = 2 if avg_aspect <= 1 else 3  # More rows for landscape

    if grid_cols <= 0 or grid_rows <= 0:
        print("Warning: Invalid grid dimensions calculated for main grid.")
        return canvas

    cell_width = canvas_size[0] // grid_cols
    cell_height = canvas_size[1] // grid_rows

    if cell_width <= 0 or cell_height <= 0:
        print("Warning: Calculated main grid cell dimensions invalid.")
        return canvas

    scale_factor = 1.1  # Slight overlap for collage effect

    for idx, img in enumerate(images_to_use):
        row, col = idx // grid_cols, idx % grid_cols

        center_x = col * cell_width + cell_width // 2
        center_y = row * cell_height + cell_height // 2

        target_cell_width = int(cell_width * scale_factor)
        target_cell_height = int(cell_height * scale_factor)

        # Resize image to fit scaled cell, preserving aspect ratio
        try:
            img_aspect = img.width / img.height
            if img_aspect > (target_cell_width / target_cell_height):
                target_width = target_cell_width
                target_height = int(target_width / img_aspect)
            else:
                target_height = target_cell_height
                target_width = int(target_height * img_aspect)
        except ZeroDivisionError:
            print(f"Warning: Skipping image {idx} in main grid (zero height).")
            continue

        if target_width <= 0 or target_height <= 0:
            print(f"Warning: Skipping image {idx} in main grid (invalid resize calc).")
            continue

        resized = img.resize((target_width, target_height), Image.LANCZOS)

        # Position centered in the original cell's center
        x = center_x - target_width // 2
        y = center_y - target_height // 2

        try:
            # Use resized image's alpha as mask
            canvas.paste(resized, (x, y), resized)
        except Exception as e:
            print(f"Warning: Error pasting image {idx} into main grid: {e}")

    return canvas


def find_text_area_bounds(
    overlay_image: Image.Image,
    threshold: int = BOUNDS_DETECTION_THRESHOLD,
    inner_padding: int = TEXT_AREA_INNER_PADDING,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Analyzes the overlay image to find the central non-background bounding box.

    Args:
        overlay_image: The PIL Image of the overlay (RGBA).
        threshold: Pixel value above which a channel is considered non-background.
        inner_padding: Pixels to shrink the detected box inwards.

    Returns:
        A tuple (x1, y1, x2, y2) representing the text area, or None if not found.
    """
    if overlay_image.mode != "RGBA":
        print("Warning: Overlay image must be RGBA for bounds detection.")
        return None

    try:
        overlay_np = np.array(overlay_image)
        alpha_channel = overlay_np[:, :, 3]
        # Mask where R, G, B, or Alpha is above threshold
        mask = (
            (overlay_np[:, :, 0] > threshold)
            | (overlay_np[:, :, 1] > threshold)
            | (overlay_np[:, :, 2] > threshold)
            | (alpha_channel > threshold)
        )

        rows, cols = np.where(mask)
        if rows.size == 0 or cols.size == 0:
            print("Warning: Could not find any non-background area in the overlay.")
            return None

        y1, y2 = np.min(rows), np.max(rows)
        x1, x2 = np.min(cols), np.max(cols)

        # Apply inner padding
        text_x1, text_y1 = x1 + inner_padding, y1 + inner_padding
        text_x2, text_y2 = x2 - inner_padding, y2 - inner_padding

        if text_x1 >= text_x2 or text_y1 >= text_y2:
            print(
                f"Warning: Inner padding ({inner_padding}px) too large for detected overlay bounds. Cannot define text area."
            )
            return None

        return text_x1, text_y1, text_x2, text_y2

    except Exception as e:
        print(f"Error during overlay bounds detection: {e}")
        return None


def add_overlay_and_title(
    image: Image.Image,
    title: str,
    overlay_image: Image.Image,
    font_path: str = FONT_PATH,
    start_font_size: int = TITLE_STARTING_FONT_SIZE,
    min_font_size: int = TITLE_MIN_FONT_SIZE,
    line_spacing: int = TITLE_LINE_SPACING,
    font_step: int = TITLE_FONT_STEP,
) -> Image.Image:
    """
    Add overlay and title text, dynamically finding text area, adjusting font size,
    and forcing title onto exactly two lines centered within the calculated area.
    """
    if not isinstance(image, Image.Image):
        print("Warning: Invalid image passed to add_overlay_and_title.")
        return image
    if not isinstance(overlay_image, Image.Image) or overlay_image.mode != "RGBA":
        print(
            "Warning: Invalid or non-RGBA overlay image passed. Skipping overlay and title."
        )
        return image
    if image.size != overlay_image.size:
        print(
            f"Warning: Image size {image.size} doesn't match overlay size {overlay_image.size}. Overlay may misalign."
        )
        # Consider resizing overlay here if appropriate, or just proceed.

    # --- Dynamically Find Text Area ---
    dynamic_text_box_rect = find_text_area_bounds(overlay_image)

    if dynamic_text_box_rect is None:
        print("Warning: Could not determine text area from overlay. Skipping title.")
        try:
            # Still apply overlay if possible
            return Image.alpha_composite(image.convert("RGBA"), overlay_image)
        except ValueError as e:
            print(f"Error applying overlay even without text area: {e}.")
            return image.convert("RGBA")  # Fallback

    dynamic_max_width = dynamic_text_box_rect[2] - dynamic_text_box_rect[0]
    dynamic_max_height = dynamic_text_box_rect[3] - dynamic_text_box_rect[1]
    # print(f"-> Detected text area: Rect={dynamic_text_box_rect}, MaxW={dynamic_max_width}, MaxH={dynamic_max_height}")

    # Composite the overlay first
    try:
        output_image = Image.alpha_composite(image.convert("RGBA"), overlay_image)
    except ValueError as e:
        print(f"Error applying overlay: {e}.")
        output_image = image.convert("RGBA")  # Fallback

    if not title or not font_path or not os.path.exists(font_path):
        print("Warning: No title or font not found. Skipping title drawing.")
        return output_image  # Return image with overlay, no title

    draw = ImageDraw.Draw(output_image)
    words = title.split()
    if not words:
        return output_image
    if len(words) < 2:
        print(
            f"Warning: Title '{title}' < 2 words. Cannot force 2 lines. Skipping title."
        )
        return output_image

    best_lines: Optional[List[str]] = None
    best_font: Optional[ImageFont.FreeTypeFont] = None

    # --- Text Fitting Helper Functions ---
    def get_text_block_size(
        lines: List[str],
        font: ImageFont.FreeTypeFont,
        current_draw: ImageDraw.ImageDraw,
    ) -> Tuple[int, int]:
        if len(lines) != 2:
            return 0, 0
        max_w, total_h = 0, 0
        try:
            bbox1 = current_draw.textbbox((0, 0), lines[0], font=font)
            line1_h = bbox1[3] - bbox1[1]
            bbox2 = current_draw.textbbox((0, 0), lines[1], font=font)
            line2_h = bbox2[3] - bbox2[1]
            max_w = max(bbox1[2] - bbox1[0], bbox2[2] - bbox2[0])
            total_h = line1_h + line_spacing + line2_h
        except Exception as e:
            print(f"Warning: Error calculating text bbox for lines '{lines}': {e}")
            return dynamic_max_width + 1, dynamic_max_height + 1  # Ensure failure
        return max_w, total_h

    def check_fit(
        lines: List[str],
        font: ImageFont.FreeTypeFont,
        current_draw: ImageDraw.ImageDraw,
    ) -> bool:
        if len(lines) != 2:
            return False
        block_width, block_height = get_text_block_size(lines, font, current_draw)
        return block_width <= dynamic_max_width and block_height <= dynamic_max_height

    # --- End Text Fitting Helpers ---

    # --- Font Size and Line Break Search ---
    current_font_size = start_font_size
    while current_font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, current_font_size)
        except IOError:
            print(f"Error: Could not load font {font_path}. Skipping title.")
            return output_image

        found_two_line_fit = False
        for i in range(1, len(words)):  # Try all split points
            candidate_lines = [" ".join(words[:i]), " ".join(words[i:])]
            if check_fit(candidate_lines, font, draw):
                best_lines, best_font = candidate_lines, font
                found_two_line_fit = True
                break  # First fit for this size is good enough

        if found_two_line_fit:
            break  # Found best size and split
        current_font_size -= font_step

    # --- Drawing ---
    if not best_lines or not best_font:
        print(
            f"Warning: Title '{title}' couldn't fit 2 lines (W:{dynamic_max_width},H:{dynamic_max_height}, MinFont:{min_font_size}pt). Skipping title."
        )
        return output_image
    else:
        final_font_size = best_font.size
        print(f"-> Title '{title}': Using font size {final_font_size}pt.")

    # Calculate drawing position centered in dynamic box
    text_box_center_x = dynamic_text_box_rect[0] + dynamic_max_width // 2
    text_box_center_y = dynamic_text_box_rect[1] + dynamic_max_height // 2

    _, total_text_height = get_text_block_size(best_lines, best_font, draw)
    bbox1 = draw.textbbox((0, 0), best_lines[0], font=best_font)
    line1_height = bbox1[3] - bbox1[1]

    # Start Y for the block
    current_y = text_box_center_y - total_text_height // 2

    try:
        draw.text(
            (text_box_center_x, current_y),
            best_lines[0],
            font=best_font,
            fill=(0, 0, 0, 255),
            anchor="mt",
            align="center",
        )
        current_y += line1_height + line_spacing
        draw.text(
            (text_box_center_x, current_y),
            best_lines[1],
            font=best_font,
            fill=(0, 0, 0, 255),
            anchor="mt",
            align="center",
        )
    except Exception as e:
        print(f"Error drawing text lines '{best_lines}': {e}")

    return output_image


def create_transparency_demo(
    image_path: str,
    mockup_bg_image: Image.Image,
) -> Optional[Image.Image]:
    """Place input image onto a mockup background to demonstrate transparency."""
    if not isinstance(mockup_bg_image, Image.Image):
        print("Warning: Invalid mockup background for transparency_demo.")
        return None

    mockup_image = mockup_bg_image.copy()
    input_image = safe_load_image(image_path, "RGBA")
    if not input_image:
        print(
            f"Warning: Could not load input image {image_path} for transparency demo."
        )
        return mockup_image  # Return mockup as is

    # --- Positioning & Resizing Logic (Example: Fit in left 2/3rds) ---
    mockup_w, mockup_h = mockup_image.size
    target_area_w = int(mockup_w * 0.6)
    target_area_h = int(mockup_h * 0.8)
    target_area_x_offset = int(mockup_w * 0.05)
    target_area_y_offset = (mockup_h - target_area_h) // 2

    img_w, img_h = input_image.size
    if img_w <= 0 or img_h <= 0:
        print(f"Warning: Invalid dimensions for image {image_path}. Skipping.")
        return mockup_image

    aspect = img_w / img_h
    target_aspect = target_area_w / target_area_h

    if aspect > target_aspect:  # Image wider than target area
        new_w = target_area_w
        new_h = int(new_w / aspect) if aspect != 0 else 0
    else:  # Image taller than target area
        new_h = target_area_h
        new_w = int(new_h * aspect) if img_h != 0 else 0

    if new_w <= 0 or new_h <= 0:
        print(f"Warning: Calculated invalid dimensions for {image_path} in demo.")
        return mockup_image

    resized_input_image = input_image.resize((new_w, new_h), Image.LANCZOS)

    # Center within the target area
    paste_x = target_area_x_offset + (target_area_w - new_w) // 2
    paste_y = target_area_y_offset + (target_area_h - new_h) // 2
    # --- End Positioning ---

    try:
        # Paste using alpha mask
        mockup_image.paste(resized_input_image, (paste_x, paste_y), resized_input_image)
    except Exception as e:
        print(f"Error pasting image {image_path} onto transparency mockup: {e}")

    return mockup_image


def create_video_mockup(
    image_paths: List[str],
    output_path: str,
    target_size: Tuple[int, int] = VIDEO_TARGET_SIZE,
    fps: int = VIDEO_FPS,
    num_transition_frames: int = VIDEO_TRANSITION_FRAMES,
    display_frames: int = VIDEO_DISPLAY_FRAMES,
) -> None:
    """Create an MP4 video with cross-fade transitions between images."""
    if not image_paths:
        print("No images provided for video creation.")
        return

    cv2_images = []
    pad_color = (255, 255, 255)  # White BGR for OpenCV padding

    for img_path in image_paths:
        try:
            # Load with alpha if available
            img_cv = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            if img_cv is None:
                print(f"Warning: OpenCV couldn't read {img_path}. Skipping.")
                continue

            h, w = img_cv.shape[:2]
            if h <= 0 or w <= 0:
                print(f"Warning: Image {img_path} has invalid dimension. Skipping.")
                continue

            # Handle alpha channel: blend onto white background
            if img_cv.shape[2] == 4:
                alpha = img_cv[:, :, 3] / 255.0
                rgb = img_cv[:, :, :3]
                bg = np.ones_like(rgb, dtype=np.uint8) * pad_color  # BGR
                blended_rgb = (
                    rgb * alpha[..., np.newaxis] + bg * (1 - alpha[..., np.newaxis])
                ).astype(np.uint8)
                img_to_resize = blended_rgb
            elif img_cv.shape[2] == 3:
                img_to_resize = img_cv  # Already BGR
            else:
                print(
                    f"Warning: Image {img_path} has unexpected channels ({img_cv.shape[2]}). Skipping."
                )
                continue

            h, w = img_to_resize.shape[:2]  # Re-check dimensions
            aspect = w / h if h != 0 else 0

            target_w, target_h = target_size
            target_aspect = target_w / target_h if target_h != 0 else 0

            # Calculate resize dimensions fitting within target_size
            if aspect == 0:  # Prevent division by zero
                new_w, new_h = 0, 0
            elif aspect > target_aspect:
                new_w = target_w
                new_h = int(target_w / aspect)
            else:
                new_h = target_h
                new_w = int(target_h * aspect)

            if new_w <= 0 or new_h <= 0:
                print(
                    f"Warning: Invalid calculated video frame size for {img_path}. Skipping."
                )
                continue

            resized = cv2.resize(
                img_to_resize, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4
            )

            # Calculate padding
            pad_y_top = (target_h - new_h) // 2
            pad_y_bottom = target_h - new_h - pad_y_top
            pad_x_left = (target_w - new_w) // 2
            pad_x_right = target_w - new_w - pad_x_left

            padded = cv2.copyMakeBorder(
                resized,
                pad_y_top,
                pad_y_bottom,
                pad_x_left,
                pad_x_right,
                cv2.BORDER_CONSTANT,
                value=pad_color,
            )

            # Ensure final size exactly matches target
            final_frame = cv2.resize(
                padded, target_size, interpolation=cv2.INTER_NEAREST
            )
            cv2_images.append(final_frame)

        except Exception as e:
            print(f"Error processing image {img_path} for video: {e}")
            traceback.print_exc()

    if not cv2_images:
        print("No valid images processed for video creation.")
        return

    # Initialize video writer
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Common MP4 codec
        out = cv2.VideoWriter(output_path, fourcc, float(fps), target_size)
        if not out.isOpened():
            print("Warning: 'mp4v' codec failed. Trying 'avc1'...")  # Alternative
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            out = cv2.VideoWriter(output_path, fourcc, float(fps), target_size)
            if not out.isOpened():
                print(
                    f"Error: Could not open video writer for {output_path}. Check codecs/permissions."
                )
                return
    except Exception as e:
        print(f"Error initializing video writer: {e}")
        return

    # Write frames with transitions
    num_images = len(cv2_images)
    for i in range(num_images):
        # Hold frame
        for _ in range(display_frames):
            out.write(cv2_images[i])

        # Transition (if not last frame and transitions enabled)
        if i < num_images - 1 and num_transition_frames > 0:
            img_current, img_next = cv2_images[i], cv2_images[i + 1]
            for j in range(1, num_transition_frames + 1):
                alpha = j / float(num_transition_frames)
                try:
                    if (
                        img_current.shape != img_next.shape
                        or img_current.dtype != img_next.dtype
                    ):
                        print(
                            f"Warning: Frame shape/type mismatch transition {i}. Using next frame."
                        )
                        blended = img_next  # Fallback
                    else:
                        blended = cv2.addWeighted(
                            img_current, 1.0 - alpha, img_next, alpha, 0
                        )
                    out.write(blended)
                except Exception as e:
                    print(f"Error blending video frame {j} of transition {i}: {e}")
                    out.write(img_next)  # Fallback

    # Ensure last frame holds if no transitions were made
    if num_images > 0 and num_transition_frames == 0:
        for _ in range(display_frames):
            out.write(cv2_images[-1])

    out.release()
    cv2.destroyAllWindows()  # Cleanup OpenCV windows
    print(f"Video saved to {output_path}")


# --- Main Orchestration Function ---


def grid_mockup(input_folder: str, title: str) -> List[str]:
    """Main function to find images, create various mockups, and save them."""
    output_folder = os.path.join(input_folder, "mocks")
    try:
        os.makedirs(output_folder, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory {output_folder}: {e}")
        return []

    output_filenames: List[str] = []
    video_source_filenames: List[str] = []

    # --- Pre-load Assets ---
    canvas_bg_main = safe_load_image(CANVAS_PATH, "RGBA")
    if canvas_bg_main:
        canvas_bg_main = canvas_bg_main.resize(OUTPUT_SIZE, Image.LANCZOS)

    canvas_bg_2x2 = safe_load_image(CANVAS_PATH, "RGBA")
    if canvas_bg_2x2:
        canvas_bg_2x2 = canvas_bg_2x2.resize(GRID_2x2_SIZE, Image.LANCZOS)

    overlay_image = safe_load_image(OVERLAY_PATH, "RGBA")
    if overlay_image and canvas_bg_main:
        if overlay_image.size != canvas_bg_main.size:
            print(
                f"Resizing overlay from {overlay_image.size} to {canvas_bg_main.size}"
            )
            overlay_image = overlay_image.resize(canvas_bg_main.size, Image.LANCZOS)
    elif not overlay_image:
        print("Warning: Overlay image failed load. Main mockup won't have title frame.")

    transparency_mockup_bg = safe_load_image(TRANSPARENCY_MOCKUP_PATH, "RGBA")
    # Optional: Resize transparency BG if needed, e.g., transparency_mockup_bg.resize(OUTPUT_SIZE, Image.LANCZOS)

    # --- Find and Load Input Images ---
    input_image_paths = sorted(glob.glob(os.path.join(input_folder, "*.png")))
    if not input_image_paths:
        print(f"No PNG images found in {input_folder}")

    loaded_main_images = load_images(
        input_image_paths[:6]
    )  # Load only needed for main grid

    # --- Create Main Mockup (Grid + Title) ---
    if canvas_bg_main:
        print("Creating main mockup...")
        main_mockup_base = create_main_grid(
            loaded_main_images, canvas_bg_main, OUTPUT_SIZE
        )

        if overlay_image and title:
            print(f"Applying overlay and title '{title}'...")
            main_mockup_final = add_overlay_and_title(
                main_mockup_base, title, overlay_image
            )
        else:
            main_mockup_final = main_mockup_base  # Use base grid
            if not overlay_image:
                print("Skipping overlay/title: Overlay not loaded.")
            elif not title:
                print("Skipping title: No title provided.")

        output_main = os.path.join(output_folder, "main.png")
        try:
            main_mockup_final.save(output_main, "PNG")
            print(f"Saved: {output_main}")
            output_filenames.append(output_main)
        except Exception as e:
            print(f"Error saving main mockup {output_main}: {e}")
    else:
        print("Skipping main mockup: Base canvas failed to load.")

    # --- Create 2x2 Grid Mockups (with Watermark) ---
    if canvas_bg_2x2:
        print("Creating 2x2 grid mockups...")
        if not input_image_paths:
            print("Skipping 2x2 grids: No input images found.")
        else:
            num_images = len(input_image_paths)
            for i in range(0, num_images, 4):
                batch_paths = input_image_paths[i : i + 4]
                if not batch_paths:
                    continue

                mockup_2x2 = create_2x2_grid(batch_paths, canvas_bg_2x2)
                mockup_2x2_watermarked = apply_watermark(
                    mockup_2x2
                )  # Watermark applied here

                suffix = "no_text" if i == 0 else f"{i//4 + 1}"
                output_filename = os.path.join(output_folder, f"mockup_{suffix}.png")

                try:
                    mockup_2x2_watermarked.save(output_filename, "PNG")
                    print(f"Saved: {output_filename}")
                    output_filenames.append(output_filename)
                    video_source_filenames.append(output_filename)  # Add to video list
                except Exception as e:
                    print(f"Error saving 2x2 mockup {output_filename}: {e}")
    else:
        print("Skipping 2x2 grid creation: 2x2 canvas failed to load.")

    # --- Create Transparency Demo ---
    if input_image_paths and transparency_mockup_bg:
        print("Creating transparency demo...")
        trans_demo = create_transparency_demo(
            input_image_paths[0], transparency_mockup_bg
        )
        if trans_demo:
            output_trans_demo = os.path.join(output_folder, "transparency_demo.png")
            try:
                trans_demo.save(output_trans_demo, "PNG")
                print(f"Saved: {output_trans_demo}")
                output_filenames.append(output_trans_demo)
                video_source_filenames.append(output_trans_demo)  # Add to video list
            except Exception as e:
                print(f"Error saving transparency demo {output_trans_demo}: {e}")
    elif not transparency_mockup_bg:
        print("Skipping transparency demo: Mockup background failed load.")
    elif not input_image_paths:
        print("Skipping transparency demo: No input images found.")

    # --- Create Video ---
    if len(video_source_filenames) > 1:
        print("Creating video mockup...")
        video_path = os.path.join(output_folder, "mockup_video.mp4")
        create_video_mockup(video_source_filenames, video_path)
        if os.path.exists(video_path):
            output_filenames.append(video_path)  # Add if created
    elif video_source_filenames:
        print("Skipping video creation: Only one source image available.")
    else:
        print("Skipping video creation: No valid source images generated for video.")

    return output_filenames


# --- Script Execution ---

if __name__ == "__main__":
    print("Starting mockup generation process...")
    processed_count = 0

    # --- Clean Input Folder (Optional) ---
    delete_identifiers = True  # Set to False to disable cleaning
    if delete_identifiers:
        print(
            f"Searching for and removing '.Identifier', '.DS_Store' files in {INPUT_DIR}..."
        )
        files_removed = 0
        try:
            for root, _, files in os.walk(INPUT_DIR):
                for file in files:
                    if file.endswith(".Identifier") or file == ".DS_Store":
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            files_removed += 1
                        except OSError as e:
                            print(f"Warning: Could not remove {file_path}: {e}")
            if files_removed > 0:
                print(f"Removed {files_removed} identifier/system files.")
        except Exception as e:
            print(f"Error during cleanup of identifier files: {e}")

    # --- Process Each Subfolder ---
    try:
        if not os.path.isdir(INPUT_DIR):
            raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")
        subfolders = [f.name for f in os.scandir(INPUT_DIR) if f.is_dir()]
    except FileNotFoundError as e:
        print(f"Error: {e}")
        subfolders = []
    except Exception as e:
        print(f"Error accessing input directory {INPUT_DIR}: {e}")
        subfolders = []

    if not subfolders:
        print(f"No subdirectories found in {INPUT_DIR}. Nothing to process.")
    else:
        print(f"Found subfolders: {', '.join(subfolders)}")

        for subfolder_name in subfolders:
            subfolder_path = os.path.join(INPUT_DIR, subfolder_name)
            # Generate title from folder name
            title = " ".join(
                word.capitalize()
                for word in subfolder_name.replace("_", " ").replace("-", " ").split()
            )

            print(f"\n--- Processing Folder: {subfolder_name} ---")
            print(f"Path: {subfolder_path}")
            print(f"Using Title: '{title}'")

            try:
                generated_files = grid_mockup(subfolder_path, title)
                if generated_files:
                    print(
                        f"Successfully generated {len(generated_files)} files for '{subfolder_name}'."
                    )
                    processed_count += 1
                else:
                    print(f"No files generated for '{subfolder_name}'.")
            except Exception as e:
                print(f"!!! Critical Error processing folder {subfolder_name}: {e}")
                traceback.print_exc()  # Print full traceback

    print(f"\n--- Processing Complete! ---")
    print(f"Processed {processed_count} subfolders.")
