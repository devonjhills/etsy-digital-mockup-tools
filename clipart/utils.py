# clipart/utils.py

import os
import traceback
from typing import Tuple, Optional, List, Dict, Any
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import cv2  # Import OpenCV

# Import configuration constants using relative import
from . import config

# --- Image Loading and Saving (Keep existing functions) ---


def safe_load_image(path: str, mode: str = "RGBA") -> Optional[Image.Image]:
    """Safely loads an image, converts mode if needed, handles errors."""
    if not os.path.exists(path):
        print(f"Warn: Image file not found at {path}")
        return None
    try:
        img = Image.open(path)
        if img.width <= 0 or img.height <= 0:
            print(f"Warn: Image has zero dimensions: {path} ({img.size})")
            return None
        if img.mode != mode:
            img = img.convert(mode)
        return img
    except FileNotFoundError:
        print(f"Warn: Image file not found during open: {path}")
        return None
    except Exception as e:
        print(f"Warn: Failed to load/convert image {path}: {e}")
        traceback.print_exc()
        return None


def load_images(image_paths: List[str]) -> List[Image.Image]:
    """Loads multiple images from paths, skipping failures."""
    loaded = []
    print(f"Loading {len(image_paths)} images...")
    for i, path in enumerate(image_paths):
        img = safe_load_image(path, "RGBA")
        if img:
            if img.width > 0 and img.height > 0:
                loaded.append(img)
            else:
                pass  # Warning printed by safe_load_image
        else:
            print(f"Warn: Failed to load image {path}, skipping.")
    print(f"Successfully loaded {len(loaded)} valid images.")
    return loaded


# --- Font Handling (Keep existing function) ---


def get_font(font_name: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Loads a font by name from AVAILABLE_FONTS, with fallback."""
    font_path = config.AVAILABLE_FONTS.get(font_name)
    fallback_used = False
    if not font_path or not os.path.exists(font_path):
        print(f"Warn: Font '{font_name}' path not found or invalid: {font_path}")
        found_fallback = False
        for key, path in config.AVAILABLE_FONTS.items():
            if os.path.exists(path):
                print(f"Warn: Using fallback font '{key}' instead.")
                font_path = path
                font_name = key
                found_fallback = True
                fallback_used = True
                break
        if not found_fallback:
            print(
                f"Error: No fonts found at configured paths: {list(config.AVAILABLE_FONTS.values())}"
            )
            return None
    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        font_status = f"(using fallback '{font_name}')" if fallback_used else ""
        print(f"Error loading font {font_path} {font_status} at size {size}: {e}")
        return None


# --- Background Generation (Keep existing functions) ---


def generate_background(
    size: Tuple[int, int], color: Tuple[int, int, int] = config.DEFAULT_BG_COLOR
) -> Image.Image:
    """Generates a solid color background image."""
    return Image.new("RGB", size, color).convert("RGBA")


def generate_gradient_background(
    size: Tuple[int, int], color1: Tuple, color2: Tuple
) -> Image.Image:
    """Generates a vertical gradient background."""
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    w, h = size
    w = max(1, w)
    h = max(1, h)
    h_blend = max(1, h - 1)
    c1_rgba = color1 if len(color1) == 4 else color1 + (255,)
    c2_rgba = color2 if len(color2) == 4 else color2 + (255,)
    for i in range(h):
        blend = i / h_blend if h_blend > 0 else 0.0
        r = int(c1_rgba[0] * (1 - blend) + c2_rgba[0] * blend)
        g = int(c1_rgba[1] * (1 - blend) + c2_rgba[1] * blend)
        b = int(c1_rgba[2] * (1 - blend) + c2_rgba[2] * blend)
        a = int(c1_rgba[3] * (1 - blend) + c2_rgba[3] * blend)
        draw.line([(0, i), (w, i)], fill=(r, g, b, a))
    return base


def generate_checkerboard(
    size: Tuple[int, int],
    square_size: int = config.CHECKERBOARD_SIZE,
    color1: Tuple = config.CHECKERBOARD_COLOR1,
    color2: Tuple = config.CHECKERBOARD_COLOR2,
) -> Image.Image:
    """Generates a checkerboard pattern background."""
    w, h = size
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            pixels[x, y] = (
                color1 if (x // square_size) % 2 == (y // square_size) % 2 else color2
            )
    return img.convert("RGBA")


# --- Effects (Keep existing function) ---


def add_simulated_shadow(
    image: Image.Image,
    offset: Tuple[int, int] = config.GRID_ITEM_SHADOW_OFFSET,
    color: Tuple = config.GRID_ITEM_SHADOW_COLOR,
) -> Image.Image:
    """Adds a simple, blurred offset shadow based on the image's alpha."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    if image.width <= 0 or image.height <= 0:
        return image
    alpha = image.split()[-1]
    shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    try:
        small_w = max(1, alpha.width // 4)
        small_h = max(1, alpha.height // 4)
        alpha_blurred = alpha.resize((small_w, small_h), Image.Resampling.NEAREST)
        alpha_blurred = alpha_blurred.resize(alpha.size, Image.Resampling.BILINEAR)
    except Exception as e:
        print(f"Warn: Shadow blur resize failed: {e}. Using original alpha.")
        alpha_blurred = alpha
    shadow_solid = Image.new("RGBA", image.size, color)
    shadow_layer.paste(shadow_solid, (0, 0), alpha_blurred)
    final_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    final_image.paste(shadow_layer, offset)
    final_image.paste(image, (0, 0), image)
    return final_image


# --- Contour and Bounding Box Utilities --- ADDED SECTION ---


def get_contour_info(
    image: Image.Image, threshold: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Finds the largest contour, its rotated bounding box, and the axis-aligned
    bounding box of that rotated box's vertices.
    Args:
        image: PIL Image (RGBA).
        threshold: Alpha threshold (0-255).
    Returns:
        Dictionary containing:
         'contour': The largest contour points.
         'rotated_rect': ((center_x, center_y), (width, height), angle)
         'box_points': 4 corner points [[x,y],...] of the rotated rect.
         'bounding_rect': (x, y, w, h) axis-aligned bounding box of box_points.
         'area': Area calculated from rotated_rect width/height.
        Returns None if no alpha or no contour found.
    """
    if image.mode != "RGBA":
        return None

    try:
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)
        alpha = img_cv[:, :, 3]
        _, thresh = cv2.threshold(alpha, threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        largest_contour = max(contours, key=cv2.contourArea)

        # Get the minimum area rotated rectangle
        rotated_rect = cv2.minAreaRect(largest_contour)
        # ((center_x, center_y), (width, height), angle)

        # Get the 4 vertices of the rotated rectangle
        box_points = cv2.boxPoints(
            rotated_rect
        )  # Returns [[x1,y1],[x2,y2],...] float32
        box_points_int = np.intp(
            box_points
        )  # Convert to integer points for bounding rect

        # Get the axis-aligned bounding box *of the rotated rectangle's vertices*
        x, y, w, h = cv2.boundingRect(box_points_int)
        bounding_rect = (
            max(0, x),
            max(0, y),
            max(1, w),
            max(1, h),
        )  # Ensure positive, within bounds?

        # Calculate area from rotated rect dimensions for sorting
        rect_width, rect_height = rotated_rect[1]
        area = rect_width * rect_height

        return {
            "contour": largest_contour,
            "rotated_rect": rotated_rect,
            "box_points": box_points_int,
            "bounding_rect": bounding_rect,  # Use this for placement overlap checks
            "area": area,  # Use this for sorting
        }

    except Exception as e:
        print(f"Error during contour detection: {e}")
        traceback.print_exc()
        return None


def check_overlap(
    box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]
) -> Tuple[bool, float]:
    """Checks axis-aligned bounding boxes overlap and intersection area."""
    # ... (Implementation remains the same) ...
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    x_intersect = max(x1, x2)
    y_intersect = max(y1, y2)
    w_intersect = min(x1 + w1, x2 + w2) - x_intersect
    h_intersect = min(y1 + h1, y2 + h2) - y_intersect
    if w_intersect > 0 and h_intersect > 0:
        return True, float(w_intersect * h_intersect)
    else:
        return False, 0.0
