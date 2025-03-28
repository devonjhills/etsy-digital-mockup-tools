# clipart/utils.py

import os
import traceback
from typing import Tuple, Optional, List, Dict, Any
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import cv2  # Import OpenCV

# Import configuration constants using relative import
from . import config


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
