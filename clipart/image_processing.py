import os
import traceback
import math
import textwrap
import random
from typing import Tuple, Optional, List, Dict, Any  # Added Dict, Any
from PIL import Image, ImageDraw, ImageEnhance, ImageOps
import numpy as np

# Import configuration and utilities using relative imports
from . import config
from . import utils

# --- Watermarking ---


def apply_watermark(
    image: Image.Image,
    logo_path: str = config.DEFAULT_LOGO_PATH,
    opacity: int = config.WATERMARK_DEFAULT_OPACITY,
    spacing_multiplier: int = config.WATERMARK_SPACING_MULTIPLIER,
    logo_size_ratio: float = config.WATERMARK_SIZE_RATIO,
) -> Image.Image:
    """Applies a tiled watermark logo to an image."""
    if not isinstance(image, Image.Image):
        print("Error: Invalid input image for watermark.")
        return image
    base_image = image.convert("RGBA")
    watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    logo = utils.safe_load_image(logo_path, "RGBA")
    if not logo:
        print("Warn: Watermark logo not found or failed to load. Skipping watermark.")
        return base_image

    try:
        logo_w = int(base_image.width * logo_size_ratio)
        logo_h = int(logo_w * logo.height / max(1, logo.width))
        if logo_w <= 0 or logo_h <= 0:
            raise ValueError(f"Invalid logo size calculated: ({logo_w}x{logo_h})")
        logo = logo.resize(
            (logo_w, logo_h), Image.Resampling.LANCZOS
        )  # Updated resampling
    except Exception as e:
        print(f"Warn: Resizing watermark logo failed: {e}. Skipping watermark.")
        return base_image

    try:
        alpha_val = max(0, min(100, opacity)) / 100.0
        if len(logo.split()) == 4:
            alpha = logo.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(alpha_val)
            logo.putalpha(alpha)
        else:
            logo.putalpha(Image.new("L", logo.size, int(255 * alpha_val)))
    except Exception as e:
        print(f"Warn: Setting watermark opacity failed: {e}.")

    spc_x, spc_y = max(1, int(logo_w * spacing_multiplier)), max(
        1, int(logo_h * spacing_multiplier)
    )
    y_s, y_e = -int(logo_h * 0.7), base_image.height + spc_y
    x_s, x_e = -int(logo_w * 0.7), base_image.width + spc_x
    for y in range(y_s, y_e, spc_y):
        off_x = (y // spc_y % 2) * (spc_x // 2)
        for x in range(x_s + off_x, x_e + off_x, spc_x):
            try:
                watermark_layer.paste(logo, (x, y), logo)
            except Exception:
                pass

    try:
        return Image.alpha_composite(base_image, watermark_layer)
    except ValueError as e:
        print(f"Error compositing watermark: {e}. Returning original image.")
        return base_image


# --- Grid Mockups ---


def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = config.GRID_2x2_SIZE,
    padding: int = config.CELL_PADDING,
    add_shadows: bool = True,
) -> Image.Image:
    """Creates a 2x2 grid mockup from the first 4 images."""
    grid_img = canvas_bg_image.copy()
    if not input_image_paths:
        print("Warn: No input images provided for 2x2 grid.")
        return grid_img

    cols, rows = 2, 2
    pad_w = padding * (cols + 1)
    pad_h = padding * (rows + 1)
    cell_w = max(1, (grid_size[0] - pad_w) // cols)
    cell_h = max(1, (grid_size[1] - pad_h) // rows)

    if cell_w <= 1 or cell_h <= 1:
        print("Warn: Grid cell size is too small. Grid may look incorrect.")

    images_to_place = utils.load_images(input_image_paths[:4])

    for idx, img in enumerate(images_to_place):
        row, col = divmod(idx, cols)
        x_start = padding + col * (cell_w + padding)
        y_start = padding + row * (cell_h + padding)

        try:
            img_copy = img.copy()
            img_copy.thumbnail(
                (cell_w, cell_h), Image.Resampling.LANCZOS
            )  # Updated resampling
            t_w, t_h = img_copy.size
            off_x = (cell_w - t_w) // 2
            off_y = (cell_h - t_h) // 2
            px, py = x_start + off_x, y_start + off_y
            img_to_paste = (
                utils.add_simulated_shadow(img_copy) if add_shadows else img_copy
            )
            grid_img.paste(img_to_paste, (px, py), img_to_paste)
        except Exception as e:
            img_path = (
                input_image_paths[idx]
                if idx < len(input_image_paths)
                else f"image {idx+1}"
            )
            print(f"Warn: Pasting in 2x2 grid failed for {img_path}: {e}")
            traceback.print_exc()

    return grid_img


# --- Transparency Demo ---


def create_transparency_demo(
    image_path: str,
    output_size: Tuple[int, int] = config.OUTPUT_SIZE,
    scale: float = config.TRANSPARENCY_DEMO_SCALE,
) -> Optional[Image.Image]:
    """Creates a mockup showing an image on a checkerboard background."""
    bg = utils.generate_checkerboard(output_size)
    if not bg:
        print("Error: Failed to generate checkerboard background.")
        return None

    img = utils.safe_load_image(image_path, "RGBA")
    if not img:
        print(f"Warn: Could not load image {image_path} for transparency demo.")
        return bg

    max_w = int(output_size[0] * scale)
    max_h = int(output_size[1] * scale)
    if max_w <= 0 or max_h <= 0:
        print(f"Warn: Invalid scale/output size for transparency demo.")
        return bg

    try:
        img_copy = img.copy()
        img_copy.thumbnail(
            (max_w, max_h), Image.Resampling.LANCZOS
        )  # Updated resampling
        img_w, img_h = img_copy.size
        px = (output_size[0] - img_w) // 2
        py = (output_size[1] - img_h) // 2
        bg.paste(img_copy, (px, py), img_copy)
    except Exception as e:
        print(f"Error creating transparency demo for {image_path}: {e}")
        traceback.print_exc()
        return bg

    return bg


# --- Title Bar and Text ---


def add_title_bar_and_text(
    image: Image.Image,
    title: str,
    subtitle_top: str,
    subtitle_bottom: str,
    num_images_for_subtitle: int,
    font_name: str = config.DEFAULT_TITLE_FONT,
    subtitle_font_name: str = config.DEFAULT_SUBTITLE_FONT,
    subtitle_font_size: int = config.SUBTITLE_FONT_SIZE,
    subtitle_text_color: Tuple = config.SUBTITLE_TEXT_COLOR,
    subtitle_spacing: int = config.SUBTITLE_SPACING,
    bar_color: Tuple = config.TITLE_BAR_COLOR,
    bar_gradient: Optional[Tuple[Tuple, Tuple]] = config.TITLE_BAR_GRADIENT,
    bar_opacity: int = config.TITLE_BAR_OPACITY,
    text_color: Tuple = config.TITLE_TEXT_COLOR,
    padding_x: int = config.TITLE_PADDING_X,
    padding_y: int = config.TITLE_PADDING_Y,
    max_font_size: int = config.TITLE_MAX_FONT_SIZE,
    min_font_size: int = config.TITLE_MIN_FONT_SIZE,
    line_spacing: int = config.TITLE_LINE_SPACING,
    font_step: int = config.TITLE_FONT_STEP,
    max_lines: int = config.TITLE_MAX_LINES,
    backdrop_padding_x: int = config.TITLE_BACKDROP_PADDING_X,
    backdrop_padding_y: int = config.TITLE_BACKDROP_PADDING_Y,
    backdrop_corner_radius: int = config.TITLE_BACKDROP_CORNER_RADIUS,
) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    """
    Adds a centered text block (title, subtitles) with a rounded backdrop.
    Returns the modified image and the bounding box (x1, y1, x2, y2) of the backdrop.
    """
    if not isinstance(image, Image.Image):
        print("Error: Invalid image input to add_title_bar_and_text.")
        return None, None

    output_image = image.copy().convert("RGBA")  # Ensure RGBA for compositing
    temp_img_for_measure = Image.new("RGBA", (1, 1))
    temp_draw_for_measure = ImageDraw.Draw(temp_img_for_measure)

    canvas_width, canvas_height = output_image.size
    if canvas_width <= 0 or canvas_height <= 0:
        print("Error: Input image has zero dimensions.")
        return output_image, None

    def apply_opacity(color_tuple: Tuple, opacity_level: int) -> Tuple:
        # (Implementation as before)
        if not (0 <= opacity_level <= 255):
            opacity_level = 255
        alpha_multiplier = opacity_level / 255.0
        base_alpha = color_tuple[3] if len(color_tuple) == 4 else 255
        final_alpha = int(min(base_alpha, 255) * alpha_multiplier)
        return color_tuple[:3] + (final_alpha,)

    transparent_bar_color = apply_opacity(bar_color, bar_opacity)
    transparent_gradient = None
    if bar_gradient:
        try:
            if len(bar_gradient) == 2:
                transparent_gradient = (
                    apply_opacity(bar_gradient[0], bar_opacity),
                    apply_opacity(bar_gradient[1], bar_opacity),
                )
            else:
                print(f"Warn: Expected 2 colors for gradient, got {len(bar_gradient)}.")
        except Exception as e:
            print(f"Warn: Could not process gradient colors: {e}.")

    subtitle_font = utils.get_font(subtitle_font_name, subtitle_font_size)
    if not subtitle_font:
        subtitle_top, subtitle_bottom = "", ""

    text_area_width_initial = max(1, canvas_width - 2 * padding_x)
    best_main_font, best_main_lines, final_main_font_size = None, [], 0
    found_fitting_size = False

    for current_font_size in range(max_font_size, min_font_size - 1, -font_step):
        font = utils.get_font(font_name, current_font_size)
        if not font:
            continue
        try:
            test_str = "abc...XYZ012..."  # A representative string
            # Use textlength for Pillow >= 9.2.0, fallback to getlength otherwise
            try:
                test_len = font.getlength(test_str)
            except AttributeError:
                test_bbox = temp_draw_for_measure.textbbox((0, 0), test_str, font=font)
                test_len = test_bbox[2] - test_bbox[0]

            avg_char_width = (test_len / len(test_str)) if test_len > 0 else 10
            approx_chars_per_line = max(
                1, int(text_area_width_initial / max(1, avg_char_width))
            )

            wrapped_lines = textwrap.wrap(
                title, width=approx_chars_per_line, max_lines=max_lines
            )

            if not wrapped_lines or len(wrapped_lines) > max_lines:
                continue

            max_line_w_check = 0
            valid_lines = True
            for line in wrapped_lines:
                bbox = temp_draw_for_measure.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                max_line_w_check = max(max_line_w_check, w)
                if w > text_area_width_initial:
                    valid_lines = False
                    break
            if valid_lines:
                best_main_font, best_main_lines, final_main_font_size = (
                    font,
                    wrapped_lines,
                    current_font_size,
                )
                found_fitting_size = True
                break
        except Exception as e:
            print(
                f"Warn: Error during font size calculation (size {current_font_size}): {e}"
            )

    if not found_fitting_size:
        print(f"Warn: Could not fit title '{title}' within constraints.")
        font = utils.get_font(font_name, min_font_size)
        if font:
            best_main_font = font
            final_main_font_size = min_font_size
            # Aggressive wrapping as fallback
            avg_char_width = max(
                1,
                (
                    font.getlength("a")
                    if hasattr(font, "getlength")
                    else temp_draw_for_measure.textbbox((0, 0), "a", font=font)[2]
                ),
            )
            approx_chars_per_line = max(
                1, int(text_area_width_initial / avg_char_width)
            )
            best_main_lines = textwrap.wrap(
                title, width=approx_chars_per_line, max_lines=max_lines
            )
            if not best_main_lines:
                best_main_lines = []
        else:
            best_main_lines = []

    max_text_content_width, main_title_height = 0, 0
    main_title_line_heights = []
    if best_main_lines and best_main_font:
        try:
            for line in best_main_lines:
                bbox = temp_draw_for_measure.textbbox((0, 0), line, font=best_main_font)
                main_title_line_heights.append(bbox[3] - bbox[1])
                max_text_content_width = max(max_text_content_width, bbox[2] - bbox[0])
            main_title_height = (
                sum(main_title_line_heights)
                + max(0, len(best_main_lines) - 1) * line_spacing
            )
        except Exception as e:
            print(f"Error calculating main title dims: {e}")
            main_title_height, best_main_lines = 0, []

    subtitle_top_height, subtitle_top_width = 0, 0
    if subtitle_top and subtitle_font:
        try:
            bbox = temp_draw_for_measure.textbbox(
                (0, 0), subtitle_top, font=subtitle_font
            )
            subtitle_top_height = bbox[3] - bbox[1]
            subtitle_top_width = bbox[2] - bbox[0]
            max_text_content_width = max(max_text_content_width, subtitle_top_width)
        except Exception as e:
            print(f"Error calculating subtitle top dims: {e}")
            subtitle_top_height = 0

    subtitle_bottom_height, subtitle_bottom_width = 0, 0
    if subtitle_bottom and subtitle_font:
        try:
            bbox = temp_draw_for_measure.textbbox(
                (0, 0), subtitle_bottom, font=subtitle_font
            )
            subtitle_bottom_height = bbox[3] - bbox[1]
            subtitle_bottom_width = bbox[2] - bbox[0]
            max_text_content_width = max(max_text_content_width, subtitle_bottom_width)
        except Exception as e:
            print(f"Error calculating subtitle bottom dims: {e}")
            subtitle_bottom_height = 0

    content_blocks = []
    if subtitle_top_height > 0:
        content_blocks.append(subtitle_top_height)
    if main_title_height > 0:
        content_blocks.append(main_title_height)
    if subtitle_bottom_height > 0:
        content_blocks.append(subtitle_bottom_height)
    total_content_height = (
        sum(content_blocks) + max(0, len(content_blocks) - 1) * subtitle_spacing
    )

    if max_text_content_width <= 0 or total_content_height <= 0:
        print("Warn: No text content. Skipping backdrop and text.")
        return output_image, None

    backdrop_width = max(1, int(max_text_content_width + 2 * backdrop_padding_x))
    backdrop_height = max(1, int(total_content_height + 2 * backdrop_padding_y))
    backdrop_x_start = (canvas_width - backdrop_width) // 2
    backdrop_y_start = (canvas_height - backdrop_height) // 2
    final_backdrop_bounds = (
        backdrop_x_start,
        backdrop_y_start,
        backdrop_x_start + backdrop_width,
        backdrop_y_start + backdrop_height,
    )

    backdrop_layer = Image.new("RGBA", output_image.size, (0, 0, 0, 0))
    backdrop_draw = ImageDraw.Draw(backdrop_layer)

    try:
        if transparent_gradient:
            gradient_fill = utils.generate_gradient_background(
                (backdrop_width, backdrop_height),
                transparent_gradient[0],
                transparent_gradient[1],
            )
            mask = Image.new("L", (backdrop_width, backdrop_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle(
                (0, 0, backdrop_width, backdrop_height),
                fill=255,
                radius=backdrop_corner_radius,
            )
            backdrop_layer.paste(
                gradient_fill, (backdrop_x_start, backdrop_y_start), mask
            )
        else:
            backdrop_draw.rounded_rectangle(
                final_backdrop_bounds,
                fill=transparent_bar_color,
                radius=backdrop_corner_radius,
            )
        output_image = Image.alpha_composite(output_image, backdrop_layer)
    except Exception as e:
        print(f"Error drawing backdrop: {e}.")
        traceback.print_exc()

    draw = ImageDraw.Draw(output_image, "RGBA")
    current_y = backdrop_y_start + backdrop_padding_y
    text_area_center_x = canvas_width // 2

    if subtitle_top_height > 0 and subtitle_font:
        try:
            draw.text(
                (text_area_center_x, current_y),
                subtitle_top,
                font=subtitle_font,
                fill=subtitle_text_color,
                anchor="mt",
                align="center",
            )
            current_y += subtitle_top_height
            if main_title_height > 0 or subtitle_bottom_height > 0:
                current_y += subtitle_spacing
        except Exception as e:
            print(f"Error drawing subtitle_top: {e}")

    if main_title_height > 0 and best_main_lines and best_main_font:
        if final_main_font_size > 0:
            print(
                f"-> Title '{title}': Font '{font_name}' at {final_main_font_size}pt."
            )
        try:
            for i, line in enumerate(best_main_lines):
                draw.text(
                    (text_area_center_x, current_y),
                    line,
                    font=best_main_font,
                    fill=text_color,
                    anchor="mt",
                    align="center",
                )
                current_y += main_title_line_heights[i]
                if i < len(best_main_lines) - 1:
                    current_y += line_spacing
            if subtitle_bottom_height > 0:
                current_y += subtitle_spacing
        except Exception as e:
            print(f"Error drawing title lines: {e}")

    if subtitle_bottom_height > 0 and subtitle_font:
        try:
            draw.text(
                (text_area_center_x, current_y),
                subtitle_bottom,
                font=subtitle_font,
                fill=subtitle_text_color,
                anchor="mt",
                align="center",
            )
        except Exception as e:
            print(f"Error drawing subtitle_bottom: {e}")

    return output_image, final_backdrop_bounds


# --- Smart Puzzle Layout --- NEW FUNCTION ---


# Updated LayoutItem to store more info
class LayoutItem:
    def __init__(self, image: Image.Image, contour_info: Dict[str, Any]):
        self.image = image  # The scaled PIL image (original or flipped)
        self.contour_info = contour_info
        # Use the axis-aligned bounding box of the minAreaRect for placement checks
        self.bounding_rect_local = contour_info[
            "bounding_rect"
        ]  # (x, y, w, h) relative to image
        self.area = contour_info["area"]  # Area from minAreaRect dims
        # Final placement info
        self.placed_pos_canvas: Optional[Tuple[int, int]] = (
            None  # Top-left paste position
        )
        self.bounding_rect_canvas: Optional[Tuple[int, int, int, int]] = (
            None  # Placement rect on canvas
        )


def _try_place_orientation(
    img_to_place: Image.Image,
    contour_info: Dict[str, Any],
    placed_items: List[LayoutItem],
    canvas_width: int,
    canvas_height: int,
    placement_step: int,
    overlap_threshold_ratio: float,  # Max allowed overlap ratio for THIS item
    avoid_center: bool,
    title_box_xywh: Optional[Tuple[int, int, int, int]],
    region_key: str,
    scan_bounds: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[Tuple[int, int]]:
    """
    Scans a region prioritizing outer edges.
    Overlap ratio is checked against the area of the item being placed.
    Returns the FIRST valid position found in the scan order.
    """
    bounding_rect_local = contour_info["bounding_rect"]
    item_area = contour_info["area"]  # Use area from minAreaRect for ratio calc
    bx_local, by_local, bw_local, bh_local = bounding_rect_local
    img_w, img_h = img_to_place.size

    # Determine scan range and order (same as before)
    min_scan_px = 0
    min_scan_py = 0
    max_place_px = canvas_width - img_w
    max_place_py = canvas_height - img_h
    if scan_bounds:
        min_scan_px = max(min_scan_px, scan_bounds[0])
        min_scan_py = max(min_scan_py, scan_bounds[1])
        max_place_px = min(max_place_px, scan_bounds[2] - img_w)
        max_place_py = min(max_place_py, scan_bounds[3] - img_h)
    max_place_px = max(min_scan_px, max_place_px)
    max_place_py = max(min_scan_py, max_place_py)
    py_range_fwd = range(min_scan_py, max_place_py + 1, placement_step)
    py_range_rev = range(max_place_py, min_scan_py - 1, -placement_step)
    px_range_fwd = range(min_scan_px, max_place_px + 1, placement_step)
    px_range_rev = range(max_place_px, min_scan_px - 1, -placement_step)
    outer_is_py: bool
    outer_range: range
    inner_range: range
    if region_key.startswith("top"):
        outer_is_py = True
        outer_range = py_range_fwd
        inner_range = px_range_rev if region_key.endswith("right") else px_range_fwd
    elif region_key.startswith("bottom"):
        outer_is_py = True
        outer_range = py_range_rev
        inner_range = px_range_rev if region_key.endswith("right") else px_range_fwd
    elif region_key.endswith("left"):
        outer_is_py = False
        outer_range = px_range_fwd
        inner_range = py_range_rev if region_key.startswith("bottom") else py_range_fwd
    elif region_key.endswith("right"):
        outer_is_py = False
        outer_range = px_range_rev
        inner_range = py_range_rev if region_key.startswith("bottom") else py_range_fwd
    else:
        outer_is_py = True
        outer_range = py_range_fwd
        inner_range = px_range_fwd

    # Scan
    for outer_val in outer_range:
        for inner_val in inner_range:
            px = inner_val if outer_is_py else outer_val
            py = outer_val if outer_is_py else inner_val

            candidate_paste_pos = (px, py)
            candidate_bounding_rect_canvas = (
                px + bx_local,
                py + by_local,
                bw_local,
                bh_local,
            )
            if (
                candidate_bounding_rect_canvas[0] < 0
                or candidate_bounding_rect_canvas[1] < 0
                or candidate_bounding_rect_canvas[0] + candidate_bounding_rect_canvas[2]
                > canvas_width
                or candidate_bounding_rect_canvas[1] + candidate_bounding_rect_canvas[3]
                > canvas_height
            ):
                continue

            is_valid_spot = True
            # A. Check overlap with placed items - REVISED RATIO CALC
            for placed_item in placed_items:
                if placed_item.bounding_rect_canvas is None:
                    continue
                overlaps, intersection = utils.check_overlap(
                    candidate_bounding_rect_canvas, placed_item.bounding_rect_canvas
                )
                if overlaps:
                    # Ratio relative to the CURRENT item's area
                    overlap_ratio = intersection / item_area if item_area > 0 else 1.0
                    if (
                        overlap_ratio > overlap_threshold_ratio
                    ):  # Check against passed threshold
                        is_valid_spot = False
                        break
            if not is_valid_spot:
                continue

            # B. Check title avoidance (remains the same)
            if avoid_center and title_box_xywh:
                rect_center_x = (
                    candidate_bounding_rect_canvas[0]
                    + candidate_bounding_rect_canvas[2] / 2
                )
                rect_center_y = (
                    candidate_bounding_rect_canvas[1]
                    + candidate_bounding_rect_canvas[3] / 2
                )
                tx, ty, tw, th = title_box_xywh
                center_in_title = (tx <= rect_center_x < tx + tw) and (
                    ty <= rect_center_y < ty + th
                )
                if center_in_title:
                    is_valid_spot = False
            if not is_valid_spot:
                continue

            # Found the FIRST valid spot according to the scan order and overlap rule
            # Nudging logic is removed for now to focus on overlap reduction first
            return candidate_paste_pos

    return None  # No spot found


def create_smart_puzzle_layout(
    image_paths: List[str],
    canvas: Image.Image,
    title_backdrop_bounds: Optional[Tuple[int, int, int, int]],
    # Sizing
    min_width_factor: float = config.PUZZLE_MIN_WIDTH_FACTOR,
    max_size_multiplier: float = config.PUZZLE_MAX_SIZE_MULTIPLIER,
    max_width_factor: float = config.PUZZLE_MAX_WIDTH_FACTOR,
    min_pixel_dim: int = config.OFFSET_GRID_MIN_PIXEL_DIM,
    # Placement
    placement_step: int = config.PUZZLE_PLACEMENT_STEP,
    max_overlap_ratio: float = config.PUZZLE_MAX_OVERLAP_AREA_RATIO,
    region_factor: float = config.PUZZLE_EDGE_REGION_FACTOR,
    avoid_center_box: bool = config.OFFSET_GRID_AVOID_CENTER_BOX,
    # Rescaling
    rescale_attempts: int = config.PUZZLE_RESCALE_ATTEMPTS,
    rescale_factor: float = config.PUZZLE_RESCALE_FACTOR,
    min_absolute_scale: float = config.PUZZLE_MIN_ABSOLUTE_SCALE,
    # Min Size Placement
    min_size_acceptable_overlap_ratio: float = config.PUZZLE_MIN_SIZE_ACCEPTABLE_OVERLAP_RATIO,
) -> Image.Image:
    """
    Arranges images prioritizing edges, uses stricter overlap, flip, rescale.
    Places at min size only if overlap is below an acceptable threshold.
    """
    print(
        f"Creating smart puzzle layout for {len(image_paths)} images (Stricter Overlap)..."
    )
    # (Setup messages...)
    if avoid_center_box and title_backdrop_bounds:
        print(f"  Will attempt to avoid title bounds: {title_backdrop_bounds}")
    elif avoid_center_box:
        print("  Warn: Avoidance requested, but no title bounds provided.")
        avoid_center_box = False
    else:
        print("  Center avoidance is OFF.")

    output_image = canvas.copy()  # This is the main image being built
    canvas_width, canvas_height = canvas.size

    if canvas_width <= 0 or canvas_height <= 0 or not image_paths:
        print("Warning: Invalid canvas/no images.")
        return output_image

    # --- 1. Load Images & Calculate Scales ---
    # ... (Loading and scale calculation logic remains the same) ...
    print("  Loading originals & calculating scales...")
    original_images = utils.load_images(image_paths)
    if not original_images:
        return output_image
    num_images = len(original_images)
    items_to_process: List[Dict[str, Any]] = []
    min_target_width_pixels = canvas_width * min_width_factor
    max_allowed_width_pixels = canvas_width * max_width_factor
    print(
        f"  Target min width: {min_target_width_pixels:.0f}px, Max allowed width: {max_allowed_width_pixels:.0f}px"
    )
    if min_target_width_pixels > max_allowed_width_pixels:
        print("  WARN: Min target width > Max allowed width.")
    for i, img in enumerate(original_images):
        if img.width <= 0 or img.height <= 0:
            continue
        scale_for_min_width = (
            min_target_width_pixels / img.width if img.width > 0 else 1.0
        )
        scale_for_min_width = max(scale_for_min_width, min_absolute_scale)
        if img.width > 0:
            scale_for_min_width = max(scale_for_min_width, min_pixel_dim / img.width)
        if img.height > 0:
            scale_for_min_width = max(scale_for_min_width, min_pixel_dim / img.height)
        initial_size_multiplier = random.uniform(1.0, max(1.0, max_size_multiplier))
        desired_initial_scale = scale_for_min_width * initial_size_multiplier
        scale_for_max_width = (
            max_allowed_width_pixels / img.width if img.width > 0 else float("inf")
        )
        final_initial_scale = min(desired_initial_scale, scale_for_max_width)
        final_initial_scale = max(final_initial_scale, scale_for_min_width)
        est_w = int(img.width * final_initial_scale)
        est_h = int(img.height * final_initial_scale)
        estimated_initial_area = est_w * est_h
        items_to_process.append(
            {
                "original_image": img,
                "initial_scale": final_initial_scale,
                "scale_for_min_width": scale_for_min_width,
                "estimated_area": estimated_initial_area,
                "id": i,
            }
        )
    items_to_process.sort(key=lambda item: item["estimated_area"], reverse=True)
    print(f"  Prepared {len(items_to_process)} items.")

    # --- 2. Define Placement Regions ---
    # ... (Region definition remains the same) ...
    print("  Defining placement regions...")
    region_w = int(canvas_width * region_factor)
    region_h = int(canvas_height * region_factor)
    regions = {
        "top_left": (0, 0, region_w, region_h),
        "top_right": (canvas_width - region_w, 0, canvas_width, region_h),
        "bottom_left": (0, canvas_height - region_h, region_w, canvas_height),
        "bottom_right": (
            canvas_width - region_w,
            canvas_height - region_h,
            canvas_width,
            canvas_height,
        ),
        "top_edge": (region_w, 0, canvas_width - region_w, region_h),
        "bottom_edge": (
            region_w,
            canvas_height - region_h,
            canvas_width - region_w,
            canvas_height,
        ),
        "left_edge": (0, region_h, region_w, canvas_height - region_h),
        "right_edge": (
            canvas_width - region_w,
            region_h,
            canvas_width,
            canvas_height - region_h,
        ),
        "full": (0, 0, canvas_width, canvas_height),
    }
    placement_order = [
        "top_left",
        "top_right",
        "bottom_right",
        "bottom_left",
        "top_edge",
        "bottom_edge",
        "left_edge",
        "right_edge",
        "full",
    ]
    min_overlap_placement_order = list(placement_order)

    # --- 3. Iterative Placement ---
    print("  Placing items (stricter overlap)...")
    placed_items: List[LayoutItem] = []
    items_placed_count = 0
    items_min_size_placed = 0
    items_skipped_final = 0
    title_box_xywh = None
    # ... (title_box_xywh setup remains the same) ...
    if avoid_center_box and title_backdrop_bounds:
        tx, ty = title_backdrop_bounds[0], title_backdrop_bounds[1]
        tw = max(1, title_backdrop_bounds[2] - tx)
        th = max(1, title_backdrop_bounds[3] - ty)
        title_box_xywh = (tx, ty, tw, th)

    for item_data in items_to_process:
        original_img = item_data["original_image"]
        initial_scale = item_data["initial_scale"]
        scale_min_allowed = item_data["scale_for_min_width"]
        item_id = item_data["id"]
        found_spot_for_this_item = False

        # --- A. Try placing normally ---
        for attempt in range(rescale_attempts + 1):
            current_scale = initial_scale * (rescale_factor**attempt)
            if current_scale < scale_min_allowed:
                print(
                    f"    Item {item_id}: Scale {current_scale:.3f} below minimum {scale_min_allowed:.3f}. Stopping normal attempts."
                )
                break
            current_scale = max(current_scale, min_absolute_scale)
            if original_img.width > 0:
                current_scale = max(current_scale, min_pixel_dim / original_img.width)
            if original_img.height > 0:
                current_scale = max(current_scale, min_pixel_dim / original_img.height)
            new_w = max(1, int(original_img.width * current_scale))
            new_h = max(1, int(original_img.height * current_scale))
            if new_w < 1 or new_h < 1:
                continue
            if attempt > 0 or current_scale != initial_scale:
                print(
                    f"    Attempt {attempt}: Trying item {item_id} at {new_w}x{new_h}"
                )
            try:
                img_scaled = original_img.resize(
                    (new_w, new_h), Image.Resampling.LANCZOS
                )
            except Exception as e:
                print(f"Warn: Resize failed item {item_id} attempt {attempt}: {e}")
                continue
            img_orientations = [(img_scaled, False)]
            try:
                img_orientations.append((ImageOps.mirror(img_scaled), True))
            except Exception as e:
                print(f"Warn: Failed to flip item {item_id}: {e}")
            placed_this_attempt = False
            for img_to_try, is_flipped in img_orientations:
                contour_info = utils.get_contour_info(img_to_try)
                if contour_info is None:
                    contour_info = {
                        "bounding_rect": (0, 0, img_to_try.width, img_to_try.height),
                        "area": float(img_to_try.width * img_to_try.height),
                        "contour": None,
                    }
                for region_key in placement_order:
                    scan_bounds = regions[region_key]
                    best_pos = _try_place_orientation(
                        img_to_try,
                        contour_info,
                        placed_items,
                        canvas_width,
                        canvas_height,
                        placement_step,
                        max_overlap_ratio,
                        avoid_center_box,
                        title_box_xywh,
                        region_key=region_key,
                        scan_bounds=scan_bounds,
                    )
                    if best_pos is not None:
                        px, py = best_pos
                        try:
                            output_image.paste(img_to_try, (px, py), img_to_try)
                            placed_item_info = LayoutItem(img_to_try, contour_info)
                            placed_item_info.placed_pos_canvas = (px, py)
                            bb_local = placed_item_info.bounding_rect_local
                            placed_item_info.bounding_rect_canvas = (
                                px + bb_local[0],
                                py + bb_local[1],
                                bb_local[2],
                                bb_local[3],
                            )
                            placed_items.append(placed_item_info)
                            items_placed_count += 1
                            found_spot_for_this_item = True
                            placed_this_attempt = True
                            orientation_str = (
                                "(Flipped)" if is_flipped else "(Original)"
                            )
                            print(
                                f"  Placed item {item_id} {orientation_str} (attempt {attempt}, size {img_to_try.size}) in region '{region_key}' at ({px},{py})"
                            )
                            break  # Exit region loop
                        except Exception as e:
                            print(
                                f"Warn: Paste failed item {item_id} at ({px},{py}): {e}"
                            )
                            found_spot_for_this_item = True
                            placed_this_attempt = True
                            break
                if placed_this_attempt:
                    break  # Exit orientation loop
            if placed_this_attempt:
                break  # Exit rescale loop

        # --- B. If Still Not Placed, Place at Minimum Size with ACCEPTABLE Overlap ---
        if not found_spot_for_this_item:
            print(
                f"    Item {item_id} not placed normally. Finding least overlap spot (below {min_size_acceptable_overlap_ratio*100:.0f}%) at minimum size..."
            )
            items_min_size_placed += 1
            min_scale = scale_min_allowed
            min_w = max(1, int(original_img.width * min_scale))
            min_h = max(1, int(original_img.height * min_scale))
            print(
                f"      Resizing item {item_id} to minimum size: {min_w}x{min_h} (scale: {min_scale:.3f})"
            )
            try:
                img_min_size = original_img.resize(
                    (min_w, min_h), Image.Resampling.LANCZOS
                )
            except Exception as e:
                print(
                    f"CRITICAL WARN: Resize failed for minimum size item {item_id}: {e}. Skipping item."
                )
                items_skipped_final += 1
                continue
            min_size_orientations = []
            contour_info_min = utils.get_contour_info(img_min_size)
            if contour_info_min is None:
                contour_info_min = {
                    "bounding_rect": (0, 0, min_w, min_h),
                    "area": float(min_w * min_h),
                    "contour": None,
                }
            min_size_orientations.append(
                {
                    "image": img_min_size,
                    "contour_info": contour_info_min,
                    "flipped": False,
                }
            )
            try:
                img_min_flipped = ImageOps.mirror(img_min_size)
                contour_info_min_flipped = utils.get_contour_info(img_min_flipped)
                if contour_info_min_flipped is None:
                    contour_info_min_flipped = {
                        "bounding_rect": (0, 0, min_w, min_h),
                        "area": float(min_w * min_h),
                        "contour": None,
                    }
                min_size_orientations.append(
                    {
                        "image": img_min_flipped,
                        "contour_info": contour_info_min_flipped,
                        "flipped": True,
                    }
                )
            except Exception as e:
                print(f"Warn: Failed to flip min size item {item_id}: {e}")
            best_acceptable_pos = None
            min_acceptable_overlap_found = float("inf")
            best_acceptable_orientation_data = None
            best_overall_pos = None
            min_overall_overlap_found = float("inf")
            best_overall_orientation_data = None
            for orientation_data in min_size_orientations:
                img_to_place = orientation_data["image"]
                c_info = orientation_data["contour_info"]
                is_flipped = orientation_data["flipped"]
                bounding_rect_local = c_info["bounding_rect"]
                bx_local, by_local, bw_local, bh_local = bounding_rect_local
                item_area = c_info["area"]
                for region_key in min_overlap_placement_order:
                    scan_bounds = regions[region_key]
                    min_scan_px_m = 0
                    min_scan_py_m = 0
                    max_place_px_m = canvas_width - img_to_place.width
                    max_place_py_m = canvas_height - img_to_place.height
                    if scan_bounds:
                        min_scan_px_m = max(min_scan_px_m, scan_bounds[0])
                        min_scan_py_m = max(min_scan_py_m, scan_bounds[1])
                        max_place_px_m = min(
                            max_place_px_m, scan_bounds[2] - img_to_place.width
                        )
                        max_place_py_m = min(
                            max_place_py_m, scan_bounds[3] - img_to_place.height
                        )
                    max_place_px_m = max(min_scan_px_m, max_place_px_m)
                    max_place_py_m = max(min_scan_py_m, max_place_py_m)
                    for py in range(min_scan_py_m, max_place_py_m + 1, placement_step):
                        for px in range(
                            min_scan_px_m, max_place_px_m + 1, placement_step
                        ):
                            candidate_paste_pos = (px, py)
                            candidate_bounding_rect_canvas = (
                                px + bx_local,
                                py + by_local,
                                bw_local,
                                bh_local,
                            )
                            if (
                                candidate_bounding_rect_canvas[0] < 0
                                or candidate_bounding_rect_canvas[1] < 0
                                or candidate_bounding_rect_canvas[0]
                                + candidate_bounding_rect_canvas[2]
                                > canvas_width
                                or candidate_bounding_rect_canvas[1]
                                + candidate_bounding_rect_canvas[3]
                                > canvas_height
                            ):
                                continue
                            if avoid_center_box and title_box_xywh:
                                rect_center_x = (
                                    candidate_bounding_rect_canvas[0]
                                    + candidate_bounding_rect_canvas[2] / 2
                                )
                                rect_center_y = (
                                    candidate_bounding_rect_canvas[1]
                                    + candidate_bounding_rect_canvas[3] / 2
                                )
                                tx, ty, tw, th = title_box_xywh
                                center_in_title = (tx <= rect_center_x < tx + tw) and (
                                    ty <= rect_center_y < ty + th
                                )
                                if center_in_title:
                                    continue
                            current_total_overlap = 0.0
                            max_individual_overlap_ratio = 0.0
                            for placed_item in placed_items:
                                if placed_item.bounding_rect_canvas is None:
                                    continue
                                overlaps, intersection = utils.check_overlap(
                                    candidate_bounding_rect_canvas,
                                    placed_item.bounding_rect_canvas,
                                )
                                if overlaps:
                                    current_total_overlap += intersection
                                    overlap_ratio = (
                                        intersection / item_area
                                        if item_area > 0
                                        else 1.0
                                    )  # Ratio based on current item
                                    max_individual_overlap_ratio = max(
                                        max_individual_overlap_ratio, overlap_ratio
                                    )
                            if current_total_overlap < min_overall_overlap_found:
                                min_overall_overlap_found = current_total_overlap
                                best_overall_pos = candidate_paste_pos
                                best_overall_orientation_data = orientation_data
                            if (
                                max_individual_overlap_ratio
                                <= min_size_acceptable_overlap_ratio
                            ):
                                if current_total_overlap < min_acceptable_overlap_found:
                                    min_acceptable_overlap_found = current_total_overlap
                                    best_acceptable_pos = candidate_paste_pos
                                    best_acceptable_orientation_data = orientation_data
            final_pos_to_use = None
            final_orientation_data = None
            placement_type = ""
            if best_acceptable_pos is not None:
                final_pos_to_use = best_acceptable_pos
                final_orientation_data = best_acceptable_orientation_data
                placement_type = f"MIN_ACCEPTABLE_OVERLAP (Ratio <= {min_size_acceptable_overlap_ratio*100:.0f}%)"
                print(
                    f"      Found acceptable spot for item {item_id} with overlap area {min_acceptable_overlap_found:.1f}"
                )
            elif best_overall_pos is not None:
                final_pos_to_use = best_overall_pos
                final_orientation_data = best_overall_orientation_data
                placement_type = "MIN_OVERALL_OVERLAP"
                print(
                    f"      No acceptable spot found. Using overall minimum overlap spot for item {item_id} (overlap area {min_overall_overlap_found:.1f})"
                )
            else:
                print(
                    f"WARN: Could not find any valid spot for item {item_id} placement at min size. Skipping item."
                )
                items_skipped_final += 1
                continue  # Skip if absolutely no spot found

            if final_pos_to_use is not None and final_orientation_data is not None:
                px, py = final_pos_to_use
                img_to_place = final_orientation_data["image"]
                c_info = final_orientation_data["contour_info"]
                is_flipped = final_orientation_data["flipped"]
                try:
                    output_image.paste(img_to_place, (px, py), img_to_place)
                    placed_item_info = LayoutItem(img_to_place, c_info)
                    placed_item_info.placed_pos_canvas = (px, py)
                    bb_local = placed_item_info.bounding_rect_local
                    placed_item_info.bounding_rect_canvas = (
                        px + bb_local[0],
                        py + bb_local[1],
                        bb_local[2],
                        bb_local[3],
                    )
                    placed_items.append(placed_item_info)
                    items_placed_count += 1
                    orientation_str = "(Flipped)" if is_flipped else "(Original)"
                    print(
                        f"  {placement_type} Placed item {item_id} {orientation_str} (MinSize {img_to_place.size}) at ({px},{py})"
                    )

                except Exception as e:
                    print(
                        f"Warn: {placement_type} Paste failed item {item_id} at ({px},{py}): {e}"
                    )
                    items_skipped_final += 1  # Count as skipped if paste fails

    # --- 4. Final Summary ---
    print(
        f"Finished smart layout: Placed {items_placed_count}/{num_images} items ({items_min_size_placed} attempted min size, {items_skipped_final} skipped final)."
    )

    return output_image
