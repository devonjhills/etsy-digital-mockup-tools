# image_processing.py
import os
import traceback
import textwrap
import random
import math
import warnings
from typing import Tuple, Optional, List

import numpy as np
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    # ImageFilter
)

# Optional import for dynamic color selection (Unchanged)
try:
    from sklearn.cluster import KMeans
    from sklearn.exceptions import ConvergenceWarning

    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not found.")

# Relative imports (Unchanged)
from . import config
from . import utils


# --- Helper Functions ---
# _calculate_fit_score (Unchanged)
def _calculate_fit_score(image: Image.Image, alpha_threshold: int) -> Tuple[float, int]:
    try:
        bbox = image.getbbox()
        if not bbox:
            return float("inf"), 0
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        if bbox_width <= 0 or bbox_height <= 0:
            return float("inf"), 0
        content_area = bbox_width * bbox_height
        aspect_ratio = bbox_width / bbox_height
        squareness_score = (
            abs(math.log(aspect_ratio)) if aspect_ratio > 0 else float("inf")
        )
        fill_score = 0.5
        try:
            cropped = image.crop(bbox)
            if "A" in cropped.getbands():
                alpha = np.array(cropped.split()[-1])
                content_pixels = np.sum(alpha > alpha_threshold)
                fill_ratio = content_pixels / content_area if content_area > 0 else 0
                fill_score = 1.0 - fill_ratio
            else:
                fill_score = 0.0
        except Exception:
            pass
        fit_score = 0.6 * squareness_score + 0.4 * fill_score
        return fit_score, content_area
    except Exception:
        return float("inf"), 0


# --- Color Contrast Utilities ---
# (Unchanged)
def compute_colorfulness(image: Image.Image) -> float:
    image_rgb = image.convert("RGB")
    arr = np.array(image_rgb, dtype=float)
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    rg = R - G
    yb = 0.5 * (R + G) - B
    std_root = np.sqrt(np.std(rg) ** 2 + np.std(yb) ** 2)
    mean_root = np.sqrt(np.mean(rg) ** 2 + np.mean(yb) ** 2)
    return std_root + 0.3 * mean_root


def select_centerpiece_image(
    image_paths: List[str],
    alpha_threshold: int = 10,
) -> Optional[Image.Image]:
    print("Selecting candidate image for analysis (best colorful combination)...")
    if not image_paths:
        print("  Warn: No image paths provided.")
        return None
    items = []
    for path in image_paths:
        original_img = utils.safe_load_image(path)
        if not original_img or original_img.width <= 0 or original_img.height <= 0:
            print(f"  Warn: Skipping invalid image: {os.path.basename(path)}")
            continue
        fit_score, content_area = _calculate_fit_score(original_img, alpha_threshold)
        colorfulness = compute_colorfulness(original_img)
        combined_score = colorfulness / (fit_score + 1.0)
        items.append(
            {
                "path": path,
                "original_img": original_img,
                "fit_score": fit_score,
                "content_bbox_area": content_area,
                "colorfulness": colorfulness,
                "combined_score": combined_score,
            }
        )
    if not items:
        print("  Error: No images successfully loaded.")
        return None
    items.sort(key=lambda item: item["combined_score"], reverse=True)
    best_item = items[0]
    print(
        f"  Selected candidate image (Score: {best_item['combined_score']:.3f}): {os.path.basename(best_item['path'])}"
    )
    return best_item["original_img"]


# --- Watermarking ---
# (Unchanged)
def apply_watermark(
    image: Image.Image,
    opacity: int = config.WATERMARK_DEFAULT_OPACITY,
    text: str = config.WATERMARK_TEXT,
    text_font_name: str = config.WATERMARK_TEXT_FONT_NAME,
    text_font_size: int = config.WATERMARK_TEXT_FONT_SIZE,
    text_color: Tuple[int, int, int] = config.WATERMARK_TEXT_COLOR,
    text_angle: float = config.WATERMARK_TEXT_ANGLE,
) -> Image.Image:
    if not isinstance(image, Image.Image):
        return image
    if opacity <= 0 or not text:
        return image
    base_image = image.copy().convert("RGBA")
    canvas_w, canvas_h = base_image.size
    final_alpha = max(0, min(255, opacity))
    font = utils.get_font(text_font_name, text_font_size)
    if not font:
        print("Error: Cannot load watermark font.")
        return base_image
    temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    try:
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = temp_draw.textsize(text, font=font)
    if text_width <= 0 or text_height <= 0:
        print(f"Error: Watermark text has zero dimensions.")
        return base_image
    margin = int(math.sqrt(text_width**2 + text_height**2) / 2) + 5
    tile_w, tile_h = text_width + 2 * margin, text_height + 2 * margin
    text_tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(text_tile)
    text_rgba = text_color + (final_alpha,)
    try:
        tile_draw.text(
            (tile_w / 2, tile_h / 2), text, font=font, fill=text_rgba, anchor="mm"
        )
    except TypeError:
        tile_draw.text(
            ((tile_w - text_width) / 2, (tile_h - text_height) / 2),
            text,
            font=font,
            fill=text_rgba,
        )
    except Exception as e:
        print(f"Error drawing text on tile: {e}.")
        tile_draw.text((margin, margin), text, font=font, fill=text_rgba)
    try:
        rotated_tile = text_tile.rotate(
            text_angle, expand=True, resample=Image.Resampling.BICUBIC
        )
    except Exception as e:
        print(f"Error rotating watermark tile: {e}.")
        return base_image
    rot_w, rot_h = rotated_tile.size
    if rot_w <= 0 or rot_h <= 0:
        print(f"Error: Rotated watermark tile has zero dimensions.")
        return base_image
    target_tiles_across = 5
    spc_x = max(rot_w // 2, canvas_w // target_tiles_across, 1)
    spc_y = max(rot_h // 2, canvas_h // target_tiles_across, 1)
    watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    start_offset_x, start_offset_y = -rot_w, -rot_h
    x_end, y_end = canvas_w + rot_w, canvas_h + rot_h
    paste_count = 0
    for y in range(start_offset_y, y_end, spc_y):
        row_offset_x = (y // spc_y % 2) * (spc_x // 3)
        for x in range(start_offset_x + row_offset_x, x_end + row_offset_x, spc_x):
            try:
                watermark_layer.paste(rotated_tile, (x, y), rotated_tile)
                paste_count += 1
            except Exception:
                pass
    if paste_count == 0:
        print("  Warning: No watermark instances pasted.")
    try:
        return Image.alpha_composite(base_image, watermark_layer)
    except ValueError as e:
        print(f"Error compositing watermark: {e}.")
        return base_image


# --- Grid Mockups ---
# (Unchanged)
def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = config.GRID_2x2_SIZE,
    padding: int = config.CELL_PADDING,
) -> Image.Image:
    grid_img = canvas_bg_image.copy().convert("RGBA")
    if not input_image_paths:
        return grid_img
    cols, rows = 2, 2
    total_pad_w = padding * (cols + 1)
    total_pad_h = padding * (rows + 1)
    cell_w = max(1, (grid_size[0] - total_pad_w) // cols)
    cell_h = max(1, (grid_size[1] - total_pad_h) // rows)
    if cell_w <= 1 or cell_h <= 1:
        print(f"Warn: Grid cell size ({cell_w}x{cell_h}) is too small.")
    images = utils.load_images(input_image_paths[:4])
    for idx, img in enumerate(images):
        img_path_for_log = (
            input_image_paths[idx] if idx < len(input_image_paths) else f"image {idx+1}"
        )
        if not img:
            print(f"Warn: Skipping invalid image {img_path_for_log}.")
            continue
        row, col = divmod(idx, cols)
        cell_x = padding + col * (cell_w + padding)
        cell_y = padding + row * (cell_h + padding)
        try:
            img_copy = img.copy()
            img_copy.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
            thumb_w, thumb_h = img_copy.size
            paste_x = cell_x + (cell_w - thumb_w) // 2
            paste_y = cell_y + (cell_h - thumb_h) // 2
            grid_img.paste(img_copy, (paste_x, paste_y), img_copy)
        except Exception as e:
            print(f"Warn: Pasting failed for {img_path_for_log}: {e}")
    return grid_img


# --- Transparency Demo ---
# (Unchanged)
def create_transparency_demo(
    image_path: str,
    canvas_path: str = "assets/transparency_mock.png",
    scale: float = config.TRANSPARENCY_DEMO_SCALE,
) -> Optional[Image.Image]:
    canvas = utils.safe_load_image(canvas_path, "RGBA")
    if not canvas:
        print(f"Error: Failed to load canvas {canvas_path}")
        return None
    img = utils.safe_load_image(image_path, "RGBA")
    if not img:
        print(f"Warn: Could not load image {image_path}")
        return canvas.copy()
    canvas_w, canvas_h = canvas.size
    max_w = int(canvas_w * 0.5 * scale)
    max_h = int(canvas_h * scale)
    if max_w <= 0 or max_h <= 0:
        print("Warn: Invalid scale/canvas size.")
        return canvas.copy()
    try:
        img_copy = img.copy()
        img_copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        img_w, img_h = img_copy.size
        paste_x = max(0, (canvas_w // 4) - (img_w // 2))
        paste_y = max(0, (canvas_h - img_h) // 2)
        canvas.paste(img_copy, (paste_x, paste_y), img_copy)
        return canvas
    except Exception as e:
        print(f"Error creating transparency demo: {e}")
        return canvas.copy()


# --- Title Bar and Text (REVISED with Border) ---


def add_title_bar_and_text(
    image: Image.Image,
    background_image: Image.Image,
    title: str,
    subtitle_top: str,
    subtitle_bottom: str,
    font_name: str = config.DEFAULT_TITLE_FONT,
    subtitle_font_name: str = config.DEFAULT_SUBTITLE_FONT,
    subtitle_font_size: int = config.SUBTITLE_FONT_SIZE,
    subtitle_spacing: int = config.SUBTITLE_SPACING,
    padding_x: int = config.TITLE_PADDING_X,
    max_font_size: int = config.TITLE_MAX_FONT_SIZE,
    min_font_size: int = config.TITLE_MIN_FONT_SIZE,
    line_spacing: int = config.TITLE_LINE_SPACING,
    font_step: int = config.TITLE_FONT_STEP,
    max_lines: int = config.TITLE_MAX_LINES,
    backdrop_padding_x: int = config.TITLE_BACKDROP_PADDING_X,
    backdrop_padding_y: int = config.TITLE_BACKDROP_PADDING_Y,
    backdrop_corner_radius: int = config.TITLE_BACKDROP_CORNER_RADIUS,
    backdrop_opacity: int = config.TITLE_BACKDROP_OPACITY,
    border_width: int = config.TITLE_BACKDROP_BORDER_WIDTH,  # *** NEW PARAMETER ***
    border_color: Tuple = config.TITLE_BACKDROP_BORDER_COLOR,  # *** NEW PARAMETER ***
    text_color: Tuple = config.TITLE_TEXT_COLOR,
    subtitle_text_color: Tuple = config.SUBTITLE_TEXT_COLOR,
) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    """
    Adds a centered text block with a soft, semi-transparent backdrop sampled
    from the background image, and an optional border.
    Returns modified image and backdrop bounds (x1, y1, x2, y2).
    """
    if not isinstance(image, Image.Image):
        print("Error: Invalid image input.")
        return None, None
    if not isinstance(background_image, Image.Image):
        print("Error: Invalid background_image input.")
        return image, None

    output_image = image.copy().convert("RGBA")
    canvas_w, canvas_h = output_image.size
    bg_w, bg_h = background_image.size
    if canvas_w <= 0 or canvas_h <= 0:
        print("Error: Input image has zero dimensions.")
        return output_image, None
    if bg_w != canvas_w or bg_h != canvas_h:
        try:
            background_image = background_image.resize(
                (canvas_w, canvas_h), Image.Resampling.LANCZOS
            )
        except Exception as resize_err:
            print(f"  Error resizing background image: {resize_err}.")

    final_text_color = text_color[:3]
    final_subtitle_color = subtitle_text_color[:3]
    final_border_color = border_color  # Expects RGBA tuple from config

    # --- Calculate Text Layout ---
    temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    subtitle_font = utils.get_font(subtitle_font_name, subtitle_font_size)
    if not subtitle_font:
        subtitle_top = subtitle_bottom = ""

    text_area_width = max(1, canvas_w - 2 * padding_x)
    best_main_font: Optional[ImageFont.FreeTypeFont] = None
    best_main_lines: List[str] = []
    final_main_font_size = 0

    # (Font size calculation loop - unchanged)
    for size in range(max_font_size, min_font_size - 1, -font_step):
        font = utils.get_font(font_name, size)
        if not font:
            continue
        try:
            test_str = "The quick brown fox"
            bbox_test = temp_draw.textbbox((0, 0), test_str, font=font)
            avg_char_width = (
                (bbox_test[2] - bbox_test[0]) / len(test_str)
                if bbox_test[2] > bbox_test[0]
                else 10
            )
            approx_chars = max(1, int(text_area_width / avg_char_width))
            wrapped_lines = textwrap.wrap(
                title, width=approx_chars, max_lines=max_lines, placeholder="..."
            )
            if not wrapped_lines:
                continue
            max_line_width = 0
            lines_fit = True
            for line in wrapped_lines:
                bbox_line = temp_draw.textbbox((0, 0), line, font=font)
                line_width = bbox_line[2] - bbox_line[0]
                max_line_width = max(max_line_width, line_width)
                if line_width > text_area_width:
                    lines_fit = False
                    break
            if lines_fit:
                best_main_font, best_main_lines, final_main_font_size = (
                    font,
                    wrapped_lines,
                    size,
                )
                break
        except Exception as e:
            print(f"Warn: Error during font size calculation at size {size}: {e}")

    if not best_main_font:
        font = utils.get_font(font_name, min_font_size)
        if font:
            best_main_font, final_main_font_size = font, min_font_size
            try:
                bbox_test = temp_draw.textbbox((0, 0), "a", font=font)
                avg_char_width = (
                    bbox_test[2] - bbox_test[0] if bbox_test[2] > bbox_test[0] else 10
                )
                approx_chars = max(1, int(text_area_width / avg_char_width))
                best_main_lines = textwrap.wrap(
                    title, width=approx_chars, max_lines=max_lines, placeholder="..."
                )
                if not best_main_lines and title:
                    best_main_lines = [
                        (
                            title[:approx_chars] + "..."
                            if len(title) > approx_chars
                            else title
                        )
                    ]
            except Exception:
                best_main_lines = [title] if title else []
        else:
            print(f"Error: Failed to load min title font '{font_name}'.")
            best_main_lines = []

    max_text_width = 0
    main_title_height = 0
    main_line_heights: List[int] = []
    if best_main_lines and best_main_font:
        for line in best_main_lines:
            bbox = temp_draw.textbbox((0, 0), line, font=best_main_font)
            line_width = bbox[2] - bbox[0]
            line_height = max(1, bbox[3] - bbox[1])
            main_line_heights.append(line_height)
            max_text_width = max(max_text_width, line_width)
        main_title_height = (
            sum(main_line_heights) + max(0, len(best_main_lines) - 1) * line_spacing
        )

    subtitle_top_height, subtitle_top_width = 0, 0
    if subtitle_top and subtitle_font:
        bbox = temp_draw.textbbox((0, 0), subtitle_top, font=subtitle_font)
        subtitle_top_width = bbox[2] - bbox[0]
        subtitle_top_height = max(1, bbox[3] - bbox[1])
        max_text_width = max(max_text_width, subtitle_top_width)

    subtitle_bottom_height, subtitle_bottom_width = 0, 0
    if subtitle_bottom and subtitle_font:
        bbox = temp_draw.textbbox((0, 0), subtitle_bottom, font=subtitle_font)
        subtitle_bottom_width = bbox[2] - bbox[0]
        subtitle_bottom_height = max(1, bbox[3] - bbox[1])
        max_text_width = max(max_text_width, subtitle_bottom_width)

    content_heights = [
        h
        for h in [subtitle_top_height, main_title_height, subtitle_bottom_height]
        if h > 0
    ]
    total_content_height = (
        sum(content_heights) + max(0, len(content_heights) - 1) * subtitle_spacing
    )

    if max_text_width <= 0 or total_content_height <= 0:
        print("Warn: No text content to render.")
        return output_image, None

    # --- Create Soft Backdrop & Border ---
    backdrop_width = max(1, int(max_text_width + 2 * backdrop_padding_x))
    backdrop_height = max(1, int(total_content_height + 2 * backdrop_padding_y))
    backdrop_x = (canvas_w - backdrop_width) // 2
    backdrop_y = (canvas_h - backdrop_height) // 2
    backdrop_x1 = max(0, backdrop_x)
    backdrop_y1 = max(0, backdrop_y)
    backdrop_x2 = min(canvas_w, backdrop_x + backdrop_width)
    backdrop_y2 = min(canvas_h, backdrop_y + backdrop_height)
    backdrop_width_clipped = backdrop_x2 - backdrop_x1
    backdrop_height_clipped = backdrop_y2 - backdrop_y1

    backdrop_bounds = None
    if backdrop_width_clipped > 0 and backdrop_height_clipped > 0:
        backdrop_bounds_clipped = (
            backdrop_x1,
            backdrop_y1,
            backdrop_x2,
            backdrop_y2,
        )  # Use clipped bounds for drawing
        # print(f"  Creating backdrop at {backdrop_bounds_clipped}") # Less verbose

        try:
            # --- Paste Backdrop ---
            background_crop = background_image.crop(backdrop_bounds_clipped)
            mask_fill_value = max(0, min(255, int(backdrop_opacity)))
            # if mask_fill_value < 255: print(f"  Applying backdrop opacity: {mask_fill_value}/255") # Less verbose
            mask = Image.new("L", (backdrop_width_clipped, backdrop_height_clipped), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle(
                (0, 0, backdrop_width_clipped, backdrop_height_clipped),
                fill=mask_fill_value,
                radius=backdrop_corner_radius,
            )
            output_image.paste(background_crop, (backdrop_x1, backdrop_y1), mask)

            # --- Draw Border (on top of pasted backdrop) ---
            if (
                border_width > 0
                and final_border_color
                and len(final_border_color) == 4
                and final_border_color[3] > 0
            ):
                print(
                    f"  Adding border (Width: {border_width}, Color: {final_border_color})"
                )
                border_draw = ImageDraw.Draw(
                    output_image
                )  # Draw directly on the output image
                border_draw.rounded_rectangle(
                    backdrop_bounds_clipped,  # Use the same clipped bounds
                    outline=final_border_color,
                    width=border_width,
                    radius=backdrop_corner_radius,
                )

        except Exception as e:
            print(f"Error creating backdrop/border: {e}")
            traceback.print_exc()
            backdrop_bounds_clipped = None  # Indicate drawing failed

    # --- Draw Text ---
    draw = ImageDraw.Draw(output_image)
    current_y = (
        backdrop_y + backdrop_padding_y
    )  # Use original calculated Y for text start
    text_center_x = backdrop_x + backdrop_width / 2  # Use original calculated X center

    # (Text drawing logic - unchanged)
    if subtitle_top_height > 0 and subtitle_font:
        try:
            draw.text(
                (text_center_x, current_y),
                subtitle_top,
                font=subtitle_font,
                fill=final_subtitle_color,
                anchor="mt",
                align="center",
            )
        except Exception as e:
            print(f"Error drawing subtitle_top: {e}")
        current_y += subtitle_top_height
        if main_title_height > 0 or subtitle_bottom_height > 0:
            current_y += subtitle_spacing

    if main_title_height > 0 and best_main_lines and best_main_font:
        try:
            for i, line in enumerate(best_main_lines):
                draw.text(
                    (text_center_x, current_y),
                    line,
                    font=best_main_font,
                    fill=final_text_color,
                    anchor="mt",
                    align="center",
                )
                current_y += main_line_heights[i]
                if i < len(best_main_lines) - 1:
                    current_y += line_spacing
            if subtitle_bottom_height > 0:
                current_y += subtitle_spacing
        except Exception as e:
            print(f"Error drawing title lines: {e}")

    if subtitle_bottom_height > 0 and subtitle_font:
        try:
            draw.text(
                (text_center_x, current_y),
                subtitle_bottom,
                font=subtitle_font,
                fill=final_subtitle_color,
                anchor="mt",
                align="center",
            )
        except Exception as e:
            print(f"Error drawing subtitle_bottom: {e}")

    # Return the modified image and the *intended logical* bounds for collage avoidance
    final_backdrop_bounds = (
        backdrop_x,
        backdrop_y,
        backdrop_x + backdrop_width,
        backdrop_y + backdrop_height,
    )
    return output_image, final_backdrop_bounds


# --- Collage Layout ---
# (Unchanged)
def create_collage_layout(
    image_paths: List[str],
    canvas: Image.Image,
    title_backdrop_bounds: Optional[Tuple[int, int, int, int]],
    surround_min_width_factor: float = config.COLLAGE_SURROUND_MIN_WIDTH_FACTOR,
    surround_max_width_factor: float = config.COLLAGE_SURROUND_MAX_WIDTH_FACTOR,
    centerpiece_scale_factor: float = config.COLLAGE_CENTERPIECE_SCALE_FACTOR,
    placement_step: int = config.COLLAGE_PLACEMENT_STEP,
    title_avoid_padding: int = config.COLLAGE_TITLE_AVOID_PADDING,
    centerpiece_avoid_padding: int = config.COLLAGE_CENTERPIECE_AVOID_PADDING,
    rescale_factor: float = config.COLLAGE_RESCALE_FACTOR,
    rescale_attempts: int = config.COLLAGE_RESCALE_ATTEMPTS,
    max_overlap_ratio_trigger: float = config.COLLAGE_MAX_ACCEPTABLE_OVERLAP_RATIO,
    min_absolute_scale: float = config.COLLAGE_MIN_SCALE_ABS,
    alpha_threshold: int = 10,
) -> Image.Image:
    print(f"Creating centerpiece collage layout for {len(image_paths)} images...")
    if not image_paths:
        return canvas.copy().convert("RGBA")
    base_canvas = canvas.copy().convert("RGBA")
    placement_canvas = Image.new("RGBA", base_canvas.size, (0, 0, 0, 0))
    canvas_w, canvas_h = base_canvas.size
    min_pixel_dim = 20
    if canvas_w <= 0 or canvas_h <= 0:
        print("  Error: Invalid canvas dimensions.")
        return base_canvas
    items = []
    for i, path in enumerate(image_paths):
        original_img = utils.safe_load_image(path)
        if not original_img or original_img.width <= 0 or original_img.height <= 0:
            continue
        fit_score, content_area = _calculate_fit_score(original_img, alpha_threshold)
        items.append(
            {
                "id": i,
                "path": path,
                "original_img": original_img,
                "fit_score": fit_score,
                "content_bbox_area": content_area,
            }
        )
    if not items:
        print("  Error: No images successfully loaded.")
        return base_canvas
    items.sort(key=lambda item: (item["fit_score"], -item["content_bbox_area"]))
    if items[0]["fit_score"] == float("inf"):
        items.sort(key=lambda item: -item.get("content_bbox_area", 0))
        if items[0].get("content_bbox_area", 0) == 0:
            print("  Error: No items with positive content area.")
            return base_canvas
    centerpiece_data = items.pop(0)
    surrounding_items = items
    placed_bounds: List[Tuple[int, int, int, int]] = []
    avoid_rect_title = None
    if title_backdrop_bounds:
        tx1, ty1, tx2, ty2 = title_backdrop_bounds
        avoid_rect_title = (
            max(0, tx1 - title_avoid_padding),
            max(0, ty1 - title_avoid_padding),
            min(canvas_w, tx2 + title_avoid_padding),
            min(canvas_h, ty2 + title_avoid_padding),
        )
    centerpiece_img = centerpiece_data["original_img"]
    avoid_rect_centerpiece = None
    try:
        target_dim = min(canvas_w, canvas_h) * centerpiece_scale_factor
        scale_factor = target_dim / max(
            centerpiece_img.width, centerpiece_img.height, 1
        )
        cp_w = max(min_pixel_dim, int(centerpiece_img.width * scale_factor))
        cp_h = max(min_pixel_dim, int(centerpiece_img.height * scale_factor))
        centerpiece_scaled = centerpiece_img.resize(
            (cp_w, cp_h), Image.Resampling.LANCZOS
        )
        cp_x, cp_y = (canvas_w - cp_w) // 2, (canvas_h - cp_h) // 2
        placement_canvas.paste(centerpiece_scaled, (cp_x, cp_y), centerpiece_scaled)
        cp_bbox = centerpiece_scaled.getbbox()
        if cp_bbox:
            cpl_x, cpl_y, cpl_x2, cpl_y2 = cp_bbox
            cpl_w = max(1, cpl_x2 - cpl_x)
            cpl_h = max(1, cpl_y2 - cpl_y)
            cp_content_bounds = (cp_x + cpl_x, cp_y + cpl_y, cpl_w, cpl_h)
            placed_bounds.append(cp_content_bounds)
            avoid_cp = (
                max(0, cp_content_bounds[0] - centerpiece_avoid_padding),
                max(0, cp_content_bounds[1] - centerpiece_avoid_padding),
                min(
                    canvas_w,
                    cp_content_bounds[0]
                    + cp_content_bounds[2]
                    + centerpiece_avoid_padding,
                ),
                min(
                    canvas_h,
                    cp_content_bounds[1]
                    + cp_content_bounds[3]
                    + centerpiece_avoid_padding,
                ),
            )
            if avoid_cp[2] > avoid_cp[0] and avoid_cp[3] > avoid_cp[1]:
                avoid_rect_centerpiece = avoid_cp
        if not cp_bbox:
            placed_bounds.append((cp_x, cp_y, cp_w, cp_h))
    except Exception as e:
        print(f"  Error placing centerpiece: {e}")
        traceback.print_exc()
    surrounding_prepared = []
    for item in surrounding_items:
        try:
            img = item["original_img"]
            min_target_w = canvas_w * surround_min_width_factor
            max_target_w = canvas_w * surround_max_width_factor
            target_w = random.uniform(min_target_w, max_target_w)
            scale = max(target_w / max(img.width, 1), min_absolute_scale)
            new_w = max(min_pixel_dim, int(img.width * scale))
            new_h = max(min_pixel_dim, int(img.height * scale))
            scaled_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            item["initial_scaled_img"] = scaled_img
            item["initial_scale"] = scale
            bbox = scaled_img.getbbox()
            item["initial_content_area"] = (
                max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                if bbox
                else new_w * new_h
            )
            surrounding_prepared.append(item)
        except Exception as e:
            print(
                f"  Warn: Failed to prepare image '{os.path.basename(item['path'])}': {e}"
            )
    surrounding_prepared.sort(
        key=lambda item: item["initial_content_area"], reverse=True
    )

    def find_best_spot(
        image_to_place: Image.Image,
    ) -> Tuple[Optional[Tuple[int, int]], float]:
        img_w, img_h = image_to_place.size
        min_overlap = float("inf")
        best_pos = None
        cb = image_to_place.getbbox()
        if cb:
            cb_x, cb_y, cb_x2, cb_y2 = cb
            cb_w, cb_h = max(1, cb_x2 - cb_x), max(1, cb_y2 - cb_y)
        else:
            cb_x, cb_y, cb_w, cb_h = 0, 0, img_w, img_h
        for py in range(0, canvas_h - img_h + 1, placement_step):
            for px in range(0, canvas_w - img_w + 1, placement_step):
                current_bounds = (px + cb_x, py + cb_y, cb_w, cb_h)
                center_x = current_bounds[0] + cb_w / 2
                center_y = current_bounds[1] + cb_h / 2
                if avoid_rect_title and (
                    avoid_rect_title[0] <= center_x < avoid_rect_title[2]
                    and avoid_rect_title[1] <= center_y < avoid_rect_title[3]
                ):
                    continue
                if avoid_rect_centerpiece and (
                    avoid_rect_centerpiece[0] <= center_x < avoid_rect_centerpiece[2]
                    and avoid_rect_centerpiece[1]
                    <= center_y
                    < avoid_rect_centerpiece[3]
                ):
                    continue
                overlap_total = 0.0
                for pb in placed_bounds:
                    overlaps, area = utils.check_overlap(current_bounds, pb)
                    overlap_total += area if overlaps else 0
                if overlap_total < min_overlap:
                    min_overlap = overlap_total
                    best_pos = (px, py)
                if min_overlap == 0:
                    return best_pos, 0.0
        return best_pos, min_overlap

    for item in surrounding_prepared:
        log_prefix = f"Item {item['id']} ({os.path.basename(item['path'])})"
        current_img = item["initial_scaled_img"]
        current_scale = item["initial_scale"]
        best_pos, overlap_area = find_best_spot(current_img)
        cb = current_img.getbbox()
        current_content_area = (
            max(1.0, float((cb[2] - cb[0]) * (cb[3] - cb[1])))
            if cb
            else float(current_img.size[0] * current_img.size[1])
        )
        overlap_ratio = (
            (overlap_area / current_content_area)
            if current_content_area > 0
            else float("inf")
        )
        if best_pos is not None and overlap_ratio > max_overlap_ratio_trigger:
            best_pos_rescaled = best_pos
            best_overlap_rescaled = overlap_area
            final_img_rescaled = current_img
            for attempt in range(rescale_attempts):
                new_scale = current_scale * (rescale_factor ** (attempt + 1))
                if new_scale < min_absolute_scale:
                    break
                try:
                    new_w = max(
                        min_pixel_dim, int(item["original_img"].width * new_scale)
                    )
                    new_h = max(
                        min_pixel_dim, int(item["original_img"].height * new_scale)
                    )
                    rescaled_img = item["original_img"].resize(
                        (new_w, new_h), Image.Resampling.LANCZOS
                    )
                except Exception as e:
                    break
                pos_r, overlap_r = find_best_spot(rescaled_img)
                if pos_r is not None:
                    cb_r = rescaled_img.getbbox()
                    area_r = (
                        max(1.0, float((cb_r[2] - cb_r[0]) * (cb_r[3] - cb_r[1])))
                        if cb_r
                        else float(new_w * new_h)
                    )
                    overlap_ratio_r = (
                        (overlap_r / area_r) if area_r > 0 else float("inf")
                    )
                    if (
                        overlap_ratio_r <= max_overlap_ratio_trigger
                        or overlap_r < best_overlap_rescaled
                    ):
                        best_overlap_rescaled = overlap_r
                        best_pos_rescaled = pos_r
                        final_img_rescaled = rescaled_img
                        if overlap_ratio_r <= max_overlap_ratio_trigger:
                            break
            best_pos, current_img, overlap_area = (
                best_pos_rescaled,
                final_img_rescaled,
                best_overlap_rescaled,
            )
        if best_pos is not None:
            px, py = best_pos
            try:
                placement_canvas.paste(current_img, (px, py), current_img)
                final_bbox = current_img.getbbox()
                if final_bbox:
                    fb_x, fb_y, fb_x2, fb_y2 = final_bbox
                    fb_w, fb_h = max(1, fb_x2 - fb_x), max(1, fb_y2 - fb_y)
                    placed_bounds.append((px + fb_x, py + fb_y, fb_w, fb_h))
                else:
                    placed_bounds.append(
                        (px, py, current_img.width, current_img.height)
                    )
            except Exception as e:
                print(f"    Error pasting {log_prefix} at ({px},{py}): {e}")
    final_image = Image.alpha_composite(base_canvas, placement_canvas)
    print("Finished centerpiece collage layout.")
    return final_image
