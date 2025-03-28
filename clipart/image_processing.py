# image_processing.py
import os
import traceback
import textwrap
import random
from typing import Tuple, Optional, List
from PIL import Image, ImageDraw, ImageEnhance
import numpy as np
import math

# Import configuration and utilities using relative imports
from . import config
from . import utils


# --- Watermarking ---
def apply_watermark(
    image: Image.Image,
    opacity: int = config.WATERMARK_DEFAULT_OPACITY,
    # Text specific parameters pulled from config by default
    text: str = config.WATERMARK_TEXT,
    text_font_name: str = config.WATERMARK_TEXT_FONT_NAME,
    text_font_size: int = config.WATERMARK_TEXT_FONT_SIZE,
    text_color: Tuple[int, int, int] = config.WATERMARK_TEXT_COLOR,
    text_angle: float = config.WATERMARK_TEXT_ANGLE,
) -> Image.Image:
    """
    Applies a tiled, diagonal text watermark to an image.
    """
    if not isinstance(image, Image.Image):
        print("Error: Invalid input image for watermark.")
        return image
    if opacity <= 0:
        print("Info: Watermark opacity is zero, skipping.")
        return image
    if not text:
        print("Info: Watermark text is empty, skipping.")
        return image

    base_image = image.copy().convert("RGBA")
    watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    final_alpha_value = int(max(0, min(255, opacity)))
    print(f"  Watermark: Text='{text}', Opacity={opacity} -> Alpha={final_alpha_value}")
    if final_alpha_value < 10:
        print(f"  Warning: Watermark alpha value ({final_alpha_value}) is very low.")

    font = utils.get_font(text_font_name, text_font_size)
    if not font:
        print("Error: Cannot load watermark font. Skipping watermark.")
        return base_image

    # Measure text size
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        text_width, text_height = temp_draw.textsize(text, font=font)

    if text_width <= 0 or text_height <= 0:
        print("Error: Watermark text has zero dimensions. Skipping.")
        return base_image
    print(f"  Watermark text measured: {text_width}x{text_height}")

    margin = int(math.sqrt(text_width**2 + text_height**2) / 2) + 5
    tile_width = text_width + 2 * margin
    tile_height = text_height + 2 * margin
    text_tile = Image.new("RGBA", (tile_width, tile_height), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(text_tile)

    text_rgba_color = text_color + (final_alpha_value,)
    try:
        tile_draw.text(
            (tile_width / 2, tile_height / 2),
            text,
            font=font,
            fill=text_rgba_color,
            anchor="mm",
        )
    except Exception:
        tile_draw.text((margin, margin), text, font=font, fill=text_rgba_color)

    try:
        rotated_tile = text_tile.rotate(
            text_angle, expand=True, resample=Image.Resampling.BICUBIC
        )
    except Exception as e:
        print(f"Error rotating watermark text tile: {e}. Skipping watermark.")
        return base_image

    rot_w, rot_h = rotated_tile.size
    if rot_w <= 0 or rot_h <= 0:
        print(
            f"Error: Rotated watermark tile has zero dimensions ({rot_w}x{rot_h}). Skipping."
        )
        return base_image
    print(f"  Rotated tile size: {rot_w}x{rot_h}")

    # NEW: Calculate spacing based on canvas size
    canvas_w, canvas_h = base_image.size
    tiles_x = max(2, int(canvas_w / (canvas_w * 0.2)))  # ~20% width per tile
    tiles_y = max(2, int(canvas_h / (canvas_h * 0.2)))  # ~20% height per tile
    spc_x = max(1, int(canvas_w / tiles_x))
    spc_y = max(1, int(canvas_h / tiles_y))

    start_offset_x = int(rot_w * 1.5)
    start_offset_y = int(rot_h * 1.5)
    y_s, y_e = -start_offset_y, base_image.height + start_offset_y
    x_s, x_e = -start_offset_x, base_image.width + start_offset_x

    print(f"  Tiling rotated text ({rot_w}x{rot_h}) with spacing ({spc_x},{spc_y})...")
    paste_count = 0
    for y in range(y_s, y_e, spc_y):
        off_x = (y // spc_y % 2) * (spc_x // 4)  # Slight stagger for diagonals
        for x in range(x_s + off_x, x_e + off_x, spc_x):
            try:
                watermark_layer.paste(rotated_tile, (x, y), rotated_tile)
                paste_count += 1
            except Exception:
                pass
    print(f"  Pasted {paste_count} watermark instances.")
    if paste_count == 0:
        print(
            "  Warning: Zero watermark instances were pasted. Check spacing and bounds."
        )

    try:
        return Image.alpha_composite(base_image, watermark_layer)
    except ValueError as e:
        print(f"Error compositing watermark: {e}. Returning original image.")
        return base_image


# --- Grid Mockups ---
# ... (keep create_2x2_grid function as is) ...
def create_2x2_grid(
    input_image_paths: List[str],
    canvas_bg_image: Image.Image,
    grid_size: Tuple[int, int] = config.GRID_2x2_SIZE,
    padding: int = config.CELL_PADDING,
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
            img_copy.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
            t_w, t_h = img_copy.size
            off_x = (cell_w - t_w) // 2
            off_y = (cell_h - t_h) // 2
            px, py = x_start + off_x, y_start + off_y
            grid_img.paste(img_copy, (px, py), img_copy)
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
    canvas_path: str = "assets/transparency_mock.png",
    scale: float = config.TRANSPARENCY_DEMO_SCALE,
) -> Optional[Image.Image]:
    """Creates a mockup by pasting an image onto the left side of a predefined canvas."""
    # Load the predefined canvas
    canvas = utils.safe_load_image(canvas_path, "RGBA")
    if not canvas:
        print(f"Error: Failed to load canvas image from {canvas_path}")
        return None

    img = utils.safe_load_image(image_path, "RGBA")
    if not img:
        print(f"Warn: Could not load image {image_path} for transparency demo.")
        return canvas

    canvas_w, canvas_h = canvas.size
    max_w = int(canvas_w * scale * 0.5)  # scale relative to half the canvas width
    max_h = int(canvas_h * scale)
    if max_w <= 0 or max_h <= 0:
        print(f"Warn: Invalid scale/canvas size for transparency demo.")
        return canvas

    try:
        img_copy = img.copy()
        img_copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        img_w, img_h = img_copy.size

        # Paste image on the left side, centered vertically
        px = (canvas_w // 4) - (img_w // 2)
        py = (canvas_h - img_h) // 2
        canvas.paste(img_copy, (px, py), img_copy)
    except Exception as e:
        print(f"Error creating transparency demo for {image_path}: {e}")
        traceback.print_exc()
        return canvas

    return canvas


# --- Title Bar and Text --- (with Neobrutalist Shadow - Text Placement Fixed)
def add_title_bar_and_text(
    image: Image.Image,
    title: str,
    subtitle_top: str,
    subtitle_bottom: str,
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
    max_font_size: int = config.TITLE_MAX_FONT_SIZE,
    min_font_size: int = config.TITLE_MIN_FONT_SIZE,
    line_spacing: int = config.TITLE_LINE_SPACING,
    font_step: int = config.TITLE_FONT_STEP,
    max_lines: int = config.TITLE_MAX_LINES,
    backdrop_padding_x: int = config.TITLE_BACKDROP_PADDING_X,
    backdrop_padding_y: int = config.TITLE_BACKDROP_PADDING_Y,
    backdrop_corner_radius: int = config.TITLE_BACKDROP_CORNER_RADIUS,
    shadow_enable: bool = config.TITLE_BACKDROP_SHADOW_ENABLE,
    shadow_offset: Tuple[int, int] = config.TITLE_BACKDROP_SHADOW_OFFSET,
    shadow_color: Tuple[int, int, int, int] = config.TITLE_BACKDROP_SHADOW_COLOR,
    shadow_opacity: int = config.TITLE_BACKDROP_SHADOW_OPACITY,
) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    if not isinstance(image, Image.Image):
        print("Error: Invalid image input to add_title_bar_and_text.")
        return None, None

    output_image = image.copy().convert("RGBA")
    temp_img_for_measure = Image.new("RGBA", (1, 1))
    temp_draw_for_measure = ImageDraw.Draw(temp_img_for_measure)

    canvas_width, canvas_height = output_image.size
    if canvas_width <= 0 or canvas_height <= 0:
        print("Error: Input image has zero dimensions.")
        return output_image, None

    # --- Helper to apply opacity ---
    def apply_opacity(color_tuple: Tuple, opacity_level: int) -> Tuple:
        if not (0 <= opacity_level <= 255):
            opacity_level = 255
        alpha_multiplier = opacity_level / 255.0
        # Ensure input tuple has alpha, default to 255 if not
        base_color = color_tuple[:3]
        base_alpha = color_tuple[3] if len(color_tuple) == 4 else 255
        final_alpha = int(min(base_alpha, 255) * alpha_multiplier)
        return base_color + (final_alpha,)

    # --- Calculate Text Sizes and Overall Backdrop Dimensions ---
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
            test_str = "abc...XYZ012..."
            try:
                test_len = font.getlength(test_str)
            except AttributeError:
                # Fallback for older Pillow versions
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
            avg_char_width = 10  # Default average width
            try:
                if hasattr(font, "getlength"):
                    avg_char_width = max(1, font.getlength("a"))
                else:
                    bbox = temp_draw_for_measure.textbbox((0, 0), "a", font=font)
                    avg_char_width = max(1, bbox[2] - bbox[0])
            except Exception:
                pass  # Use default if calculation fails

            approx_chars_per_line = max(
                1, int(text_area_width_initial / avg_char_width)
            )
            best_main_lines = textwrap.wrap(
                title, width=approx_chars_per_line, max_lines=max_lines
            )
            if not best_main_lines:
                best_main_lines = []  # Ensure it's an empty list if wrapping fails
        else:
            best_main_lines = []  # Ensure it's an empty list if font fails

    max_text_content_width, main_title_height = 0, 0
    main_title_line_heights = []
    if best_main_lines and best_main_font:
        try:
            for line in best_main_lines:
                bbox = temp_draw_for_measure.textbbox((0, 0), line, font=best_main_font)
                line_height = bbox[3] - bbox[1]
                # Add a minimum height in case bbox calculation returns zero
                main_title_line_heights.append(max(1, line_height))
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
            subtitle_top_height = max(1, bbox[3] - bbox[1])  # Ensure min height
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
            subtitle_bottom_height = max(1, bbox[3] - bbox[1])  # Ensure min height
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

    # Calculate main backdrop dimensions and position
    backdrop_width = max(1, int(max_text_content_width + 2 * backdrop_padding_x))
    backdrop_height = max(1, int(total_content_height + 2 * backdrop_padding_y))
    backdrop_x_start = (canvas_width - backdrop_width) // 2
    backdrop_y_start = (canvas_height - backdrop_height) // 2
    # These are the bounds of the TOP backdrop
    final_backdrop_bounds = (
        backdrop_x_start,
        backdrop_y_start,
        backdrop_x_start + backdrop_width,
        backdrop_y_start + backdrop_height,
    )

    # --- Prepare Colors ---
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

    # Prepare shadow color
    transparent_shadow_color = apply_opacity(shadow_color, shadow_opacity)

    # --- Draw Backdrops ---
    # Create a layer for *both* backdrops
    backdrop_layer = Image.new("RGBA", output_image.size, (0, 0, 0, 0))
    backdrop_draw = ImageDraw.Draw(backdrop_layer)

    try:
        # 1. Draw Shadow Backdrop (if enabled)
        if (
            shadow_enable
            and shadow_offset != (0, 0)
            and transparent_shadow_color[3] > 0
        ):
            shadow_x1 = final_backdrop_bounds[0] + shadow_offset[0]
            shadow_y1 = final_backdrop_bounds[1] + shadow_offset[1]
            shadow_x2 = final_backdrop_bounds[2] + shadow_offset[0]
            shadow_y2 = final_backdrop_bounds[3] + shadow_offset[1]
            shadow_bounds = (shadow_x1, shadow_y1, shadow_x2, shadow_y2)

            # Ensure shadow stays within canvas bounds (optional, but good practice)
            shadow_bounds = (
                max(0, shadow_bounds[0]),
                max(0, shadow_bounds[1]),
                min(canvas_width, shadow_bounds[2]),
                min(canvas_height, shadow_bounds[3]),
            )

            if (
                shadow_bounds[0] < shadow_bounds[2]
                and shadow_bounds[1] < shadow_bounds[3]
            ):  # Check if valid rect
                backdrop_draw.rounded_rectangle(
                    shadow_bounds,
                    fill=transparent_shadow_color,
                    radius=backdrop_corner_radius,  # Use same radius
                )
            else:
                print(
                    "Warn: Shadow bounds resulted in invalid rectangle, skipping shadow."
                )

        # 2. Draw Main Backdrop (on top of shadow)
        if transparent_gradient:
            # Generate gradient for the main backdrop size
            gradient_fill = utils.generate_gradient_background(
                (backdrop_width, backdrop_height),
                transparent_gradient[0],
                transparent_gradient[1],
            )
            # Create mask for rounded corners
            mask = Image.new("L", (backdrop_width, backdrop_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle(
                (0, 0, backdrop_width, backdrop_height),
                fill=255,
                radius=backdrop_corner_radius,
            )
            # Paste gradient using the mask at the main backdrop position
            backdrop_layer.paste(
                gradient_fill, (backdrop_x_start, backdrop_y_start), mask
            )
        elif transparent_bar_color[3] > 0:  # Only draw if not fully transparent
            # Draw solid color main backdrop
            backdrop_draw.rounded_rectangle(
                final_backdrop_bounds,
                fill=transparent_bar_color,
                radius=backdrop_corner_radius,
            )

        # 3. Composite backdrop layer onto the output image
        output_image = Image.alpha_composite(output_image, backdrop_layer)

    except Exception as e:
        print(f"Error drawing backdrop(s): {e}.")
        traceback.print_exc()

    # --- Draw Text (on top of combined backdrops) ---
    draw = ImageDraw.Draw(output_image, "RGBA")
    # Calculate starting Y position for the first text block inside the backdrop padding
    current_y = backdrop_y_start + backdrop_padding_y
    text_area_center_x = canvas_width // 2

    # Draw Subtitle Top
    if subtitle_top_height > 0 and subtitle_font:
        try:
            # Simply use current_y and anchor="mt"
            draw.text(
                (text_area_center_x, current_y),
                subtitle_top,
                font=subtitle_font,
                fill=subtitle_text_color,
                anchor="mt",
                align="center",
            )
            # Advance current_y by the height of this block plus spacing
            current_y += subtitle_top_height
            if (
                main_title_height > 0 or subtitle_bottom_height > 0
            ):  # Add spacing only if more blocks follow
                current_y += subtitle_spacing
        except Exception as e:
            print(f"Error drawing subtitle_top: {e}")

    # Draw Main Title Lines
    if main_title_height > 0 and best_main_lines and best_main_font:
        if final_main_font_size > 0:
            print(
                f"-> Title '{title}': Font '{font_name}' at {final_main_font_size}pt."
            )
        try:
            # Keep track of the y position for the current line
            line_y_start = current_y
            for i, line in enumerate(best_main_lines):
                # Simply use line_y_start and anchor="mt" for each line
                draw.text(
                    (text_area_center_x, line_y_start),
                    line,
                    font=best_main_font,
                    fill=text_color,
                    anchor="mt",
                    align="center",
                )
                # Advance the y position for the next line
                line_y_start += main_title_line_heights[i]
                if i < len(best_main_lines) - 1:
                    line_y_start += line_spacing  # Add inter-line spacing

            # Update current_y to be after the last drawn title line
            current_y = line_y_start

            # Add spacing before bottom subtitle only if title exists and bottom subtitle exists
            if subtitle_bottom_height > 0:
                current_y += subtitle_spacing
        except Exception as e:
            print(f"Error drawing title lines: {e}")

    # Draw Subtitle Bottom
    if subtitle_bottom_height > 0 and subtitle_font:
        try:
            # Simply use current_y and anchor="mt"
            draw.text(
                (text_area_center_x, current_y),
                subtitle_bottom,
                font=subtitle_font,
                fill=subtitle_text_color,
                anchor="mt",
                align="center",
            )
            # No need to advance current_y further unless more elements were added below
        except Exception as e:
            print(f"Error drawing subtitle_bottom: {e}")

    # Return the modified image and the bounds of the *main* (top) backdrop
    return output_image, final_backdrop_bounds


# --- Collage Layout --- CENTERPIECE VERSION ---
def create_collage_layout(
    image_paths: List[str],
    canvas: Image.Image,
    title_backdrop_bounds: Optional[Tuple[int, int, int, int]],  # (x1, y1, x2, y2)
    # Use config names
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
    alpha_threshold: int = 10,  # Threshold to consider a pixel as 'content'
) -> Image.Image:
    print(f"Creating centerpiece collage layout for {len(image_paths)} images...")
    if not image_paths:
        print("  No images provided.")
        return canvas

    placement_canvas = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    canvas_width, canvas_height = canvas.size
    min_pixel_dim = 20

    if canvas_width <= 0 or canvas_height <= 0:
        print("  Error: Invalid canvas dimensions.")
        return canvas

    # --- Load ALL Images and Calculate 'Fit' Score ---
    all_items_loaded = []
    print("  Loading images and calculating centerpiece suitability...")
    for i, path in enumerate(image_paths):
        original_img = utils.safe_load_image(path, mode="RGBA")
        if not original_img or original_img.width <= 0 or original_img.height <= 0:
            print(f"  Warn: Failed to load or invalid image '{path}', skipping.")
            continue

        fit_score = float("inf")  # Default to worst score
        bbox_area = 0
        try:
            # Get bounding box of actual content
            bbox = original_img.getbbox()
            if bbox:
                bbox_width = bbox[2] - bbox[0]
                bbox_height = bbox[3] - bbox[1]

                if bbox_width > 0 and bbox_height > 0:
                    bbox_area = bbox_width * bbox_height

                    # 1. Squareness Score (lower is better)
                    aspect_ratio = bbox_width / bbox_height
                    squareness_score = abs(aspect_ratio - 1.0)

                    # 2. Fill Ratio Score (lower is better, based on 1.0 - fill_ratio)
                    # Ensure cropping is within image bounds if bbox is tight
                    crop_box = (
                        max(0, bbox[0]),
                        max(0, bbox[1]),
                        min(original_img.width, bbox[2]),
                        min(original_img.height, bbox[3]),
                    )
                    if crop_box[0] < crop_box[2] and crop_box[1] < crop_box[3]:
                        alpha_channel = np.array(
                            original_img.split()[-1].crop(crop_box)
                        )
                        content_pixels = np.sum(alpha_channel > alpha_threshold)
                        fill_ratio = content_pixels / bbox_area if bbox_area > 0 else 0
                        fill_score = (
                            1.0 - fill_ratio
                        )  # Lower score for higher fill ratio
                    else:
                        fill_score = 1.0  # Penalize if crop box is invalid

                    # 3. Combined Score (lower is better) - Equal weight for now
                    fit_score = squareness_score + fill_score
                else:
                    print(f"    Warn: Zero dimension bbox for {os.path.basename(path)}")
            else:
                print(f"    Warn: Could not get bbox for {os.path.basename(path)}")

        except Exception as e:
            print(f"    Error calculating fit score for {os.path.basename(path)}: {e}")

        all_items_loaded.append(
            {
                "id": i,
                "path": path,
                "original_img": original_img,
                "fit_score": fit_score,  # Lower score is better
                "estimated_area": bbox_area,  # Use bbox area for sorting secondary if needed
            }
        )

    if not all_items_loaded:
        print("  No images successfully loaded.")
        return canvas  # Return original canvas

    # --- Select Centerpiece (Lowest fit_score) ---
    # Sort primarily by fit_score (ascending), secondarily by area (descending) as tie-breaker
    all_items_loaded.sort(key=lambda item: (item["fit_score"], -item["estimated_area"]))

    if not all_items_loaded or all_items_loaded[0]["fit_score"] == float("inf"):
        print(
            "  Warn: No images had a valid fit score. Falling back to largest area for centerpiece."
        )
        # Resort by area if no valid scores or list became empty somehow
        all_items_loaded.sort(key=lambda item: -item.get("estimated_area", 0))
        if not all_items_loaded:
            print("  Error: No items left after attempting centerpiece selection.")
            return canvas

    centerpiece_data = all_items_loaded.pop(
        0
    )  # Take the first (best fit score or largest area)
    surrounding_items_data = all_items_loaded  # The rest are surrounding
    print(
        f"  Centerpiece (Score: {centerpiece_data.get('fit_score', 'N/A'):.3f}): {os.path.basename(centerpiece_data['path'])}"
    )
    print(f"  Surrounding items: {len(surrounding_items_data)}")

    placed_item_bounds_xywh = []  # Store (x, y, w, h) of placed content

    # --- Define Title Avoidance Zone ---
    avoid_rect_title_x1y1x2y2 = None  # (x1, y1, x2, y2) for point-in-rect check
    if title_backdrop_bounds:
        tx1, ty1, tx2, ty2 = title_backdrop_bounds
        avoid_x1 = max(0, tx1 - title_avoid_padding)
        avoid_y1 = max(0, ty1 - title_avoid_padding)
        avoid_x2 = min(canvas_width, tx2 + title_avoid_padding)
        avoid_y2 = min(canvas_height, ty2 + title_avoid_padding)
        if avoid_x1 < avoid_x2 and avoid_y1 < avoid_y2:
            avoid_rect_title_x1y1x2y2 = (avoid_x1, avoid_y1, avoid_x2, avoid_y2)
            print(f"  Avoidance Rect (Title): {avoid_rect_title_x1y1x2y2}")

    # --- Place Centerpiece ---
    print("  Placing centerpiece...")
    centerpiece_img_orig = centerpiece_data["original_img"]
    avoid_rect_centerpiece_xywh = None  # Initialize
    try:
        # Scale based on the smaller canvas dimension to fit better
        target_dim = min(canvas_width, canvas_height) * centerpiece_scale_factor
        scale_c = target_dim / max(
            1, centerpiece_img_orig.width, centerpiece_img_orig.height
        )  # Avoid div by zero

        cp_w = max(min_pixel_dim, int(centerpiece_img_orig.width * scale_c))
        cp_h = max(min_pixel_dim, int(centerpiece_img_orig.height * scale_c))
        centerpiece_scaled = centerpiece_img_orig.resize(
            (cp_w, cp_h), Image.Resampling.LANCZOS
        )

        # Center placement
        px_c = (canvas_width - cp_w) // 2
        py_c = (canvas_height - cp_h) // 2

        placement_canvas.paste(centerpiece_scaled, (px_c, py_c), centerpiece_scaled)

        # Record bounds and define centerpiece avoidance zone
        cp_content_box = centerpiece_scaled.getbbox()
        if not cp_content_box:
            cp_content_box = (0, 0, cp_w, cp_h)
        cp_cb_x = cp_content_box[0]
        cp_cb_y = cp_content_box[1]
        cp_cb_w = max(1, cp_content_box[2] - cp_cb_x)
        cp_cb_h = max(1, cp_content_box[3] - cp_cb_y)
        centerpiece_bounds_xywh = (px_c + cp_cb_x, py_c + cp_cb_y, cp_cb_w, cp_cb_h)
        placed_item_bounds_xywh.append(centerpiece_bounds_xywh)

        # Avoidance rect around centerpiece content box (x, y, w, h)
        avoid_cp_x = max(0, centerpiece_bounds_xywh[0] - centerpiece_avoid_padding)
        avoid_cp_y = max(0, centerpiece_bounds_xywh[1] - centerpiece_avoid_padding)
        avoid_cp_x2 = min(
            canvas_width,
            centerpiece_bounds_xywh[0]
            + centerpiece_bounds_xywh[2]
            + centerpiece_avoid_padding,
        )
        avoid_cp_y2 = min(
            canvas_height,
            centerpiece_bounds_xywh[1]
            + centerpiece_bounds_xywh[3]
            + centerpiece_avoid_padding,
        )
        # Ensure width/height are positive
        avoid_cp_w = max(0, avoid_cp_x2 - avoid_cp_x)
        avoid_cp_h = max(0, avoid_cp_y2 - avoid_cp_y)
        if avoid_cp_w > 0 and avoid_cp_h > 0:
            avoid_rect_centerpiece_xywh = (
                avoid_cp_x,
                avoid_cp_y,
                avoid_cp_w,
                avoid_cp_h,
            )
            print(f"  Avoidance Rect (Centerpiece): {avoid_rect_centerpiece_xywh}")
        else:
            print(f"  Warn: Centerpiece avoidance rect has zero dimension.")
            avoid_rect_centerpiece_xywh = None

    except Exception as e:
        print(f"  Error placing centerpiece: {e}")
        traceback.print_exc()
        avoid_rect_centerpiece_xywh = (
            None  # No centerpiece avoidance if placement failed
        )

    # --- Prepare Surrounding Images (Initial Sizes) ---
    surrounding_items_prepared = []
    print("  Calculating initial sizes for surrounding items...")
    for item_data in surrounding_items_data:
        original_img = item_data["original_img"]
        try:
            # Random scale based on width factors
            min_target_w = canvas_width * surround_min_width_factor
            max_target_w = canvas_width * surround_max_width_factor
            target_w = random.uniform(min_target_w, max_target_w)

            initial_scale = target_w / max(1, original_img.width)  # Avoid div by zero
            initial_scale = max(
                initial_scale, min_absolute_scale
            )  # Ensure not below absolute min

            # Resize
            new_w = max(min_pixel_dim, int(original_img.width * initial_scale))
            new_h = max(min_pixel_dim, int(original_img.height * initial_scale))
            # Maintain aspect ratio roughly
            if original_img.width > 0 and original_img.height > 0:
                if original_img.width > original_img.height:
                    new_h = max(
                        min_pixel_dim,
                        int(new_w * original_img.height / original_img.width),
                    )
                else:
                    new_w = max(
                        min_pixel_dim,
                        int(new_h * original_img.width / original_img.height),
                    )

            initial_scaled_img = original_img.resize(
                (new_w, new_h), Image.Resampling.LANCZOS
            )

            item_data["initial_scaled_img"] = initial_scaled_img
            item_data["initial_scale"] = initial_scale
            item_data["initial_area"] = new_w * new_h
            surrounding_items_prepared.append(item_data)

        except Exception as e:
            print(
                f"  Warn: Failed to prepare surrounding image '{item_data['path']}': {e}"
            )

    # Sort surrounding items by initial area (largest first)
    surrounding_items_prepared.sort(key=lambda item: item["initial_area"], reverse=True)

    # --- Helper function to find best spot for SURROUNDING items ---
    def find_best_spot_surrounding(
        image_to_place: Image.Image,
    ) -> Tuple[Optional[Tuple[int, int]], float]:
        img_w, img_h = image_to_place.size
        min_overlap = float("inf")
        best_p = None

        content_box_x1y1x2y2 = image_to_place.getbbox()
        if not content_box_x1y1x2y2:
            content_box_x1y1x2y2 = (0, 0, img_w, img_h)
        cb_x_local = content_box_x1y1x2y2[0]
        cb_y_local = content_box_x1y1x2y2[1]
        cb_w_local = max(1, content_box_x1y1x2y2[2] - cb_x_local)
        cb_h_local = max(1, content_box_x1y1x2y2[3] - cb_y_local)

        for py in range(0, canvas_height - img_h + 1, placement_step):
            for px in range(0, canvas_width - img_w + 1, placement_step):
                current_bounds_xywh = (
                    px + cb_x_local,
                    py + cb_y_local,
                    cb_w_local,
                    cb_h_local,
                )
                content_center_x = current_bounds_xywh[0] + current_bounds_xywh[2] / 2
                content_center_y = current_bounds_xywh[1] + current_bounds_xywh[3] / 2

                # Check Avoidance Zones (Title AND Centerpiece)
                # Check Title (using x1y1x2y2 format)
                title_avoided = False
                if (
                    avoid_rect_title_x1y1x2y2
                    and (
                        avoid_rect_title_x1y1x2y2[0]
                        <= content_center_x
                        < avoid_rect_title_x1y1x2y2[2]
                    )
                    and (
                        avoid_rect_title_x1y1x2y2[1]
                        <= content_center_y
                        < avoid_rect_title_x1y1x2y2[3]
                    )
                ):
                    title_avoided = True

                # Check Centerpiece (using x,y,w,h format)
                centerpiece_avoided = False
                if not title_avoided and avoid_rect_centerpiece_xywh:
                    cp_ax, cp_ay, cp_aw, cp_ah = avoid_rect_centerpiece_xywh
                    if (cp_ax <= content_center_x < cp_ax + cp_aw) and (
                        cp_ay <= content_center_y < cp_ay + cp_ah
                    ):
                        centerpiece_avoided = True

                if title_avoided or centerpiece_avoided:
                    continue  # Skip this position if center is in either avoidance zone

                # Calculate Overlap
                current_total_overlap = 0.0
                # Check against ALL previously placed items (including centerpiece)
                for placed_bounds_xywh in placed_item_bounds_xywh:
                    overlaps, intersection = utils.check_overlap(
                        current_bounds_xywh, placed_bounds_xywh
                    )
                    if overlaps:
                        current_total_overlap += intersection

                # Update Best Spot
                if current_total_overlap < min_overlap:
                    min_overlap = current_total_overlap
                    best_p = (px, py)
                    if min_overlap == 0:
                        break  # Optimization: stop if perfect spot found
            if min_overlap == 0 and best_p is not None:
                break  # Optimization
        return best_p, min_overlap

    # --- Place Surrounding Items ---
    print("  Placing surrounding items...")
    for item_data in surrounding_items_prepared:
        item_id = item_data["id"]
        item_path = item_data["path"]
        original_img = item_data["original_img"]
        current_scaled_img = item_data["initial_scaled_img"]
        current_scale = item_data["initial_scale"]
        log_prefix = f"Item {item_id}"

        # Find best spot for initial size
        best_pos, min_overlap_area = find_best_spot_surrounding(current_scaled_img)

        # Check if rescaling is needed based on overlap ratio
        needs_rescale = False
        if (
            best_pos is not None and min_overlap_area > 0
        ):  # Only check if there's overlap
            content_box = current_scaled_img.getbbox()
            content_area = 1.0
            if content_box:
                content_w = content_box[2] - content_box[0]
                content_h = content_box[3] - content_box[1]
                content_area = max(1.0, float(content_w * content_h))
            else:
                img_w_curr, img_h_curr = current_scaled_img.size
                content_area = max(1.0, float(img_w_curr * img_h_curr))

            overlap_ratio = min_overlap_area / content_area
            if overlap_ratio > max_overlap_ratio_trigger:
                needs_rescale = True
                print(
                    f"    {log_prefix}: Initial overlap ratio {overlap_ratio:.2f} > {max_overlap_ratio_trigger:.2f}. Attempting rescale."
                )

        # Rescaling Logic
        if needs_rescale:
            best_pos_after_rescale = best_pos  # Start with the initial best pos
            min_overlap_after_rescale = min_overlap_area  # Start with initial overlap
            final_image_to_place = current_scaled_img  # Start with initial image

            for attempt in range(rescale_attempts):
                new_scale = current_scale * (rescale_factor ** (attempt + 1))
                if new_scale < min_absolute_scale:
                    print(
                        f"      Rescale attempt {attempt+1}: Scale {new_scale:.3f} below minimum {min_absolute_scale:.3f}. Stopping."
                    )
                    break
                try:
                    # Resize from ORIGINAL image
                    new_w = max(min_pixel_dim, int(original_img.width * new_scale))
                    new_h = max(min_pixel_dim, int(original_img.height * new_scale))
                    if original_img.width > 0 and original_img.height > 0:
                        if original_img.width > original_img.height:
                            new_h = max(
                                min_pixel_dim,
                                int(new_w * original_img.height / original_img.width),
                            )
                        else:
                            new_w = max(
                                min_pixel_dim,
                                int(new_h * original_img.width / original_img.height),
                            )
                    rescaled_img = original_img.resize(
                        (new_w, new_h), Image.Resampling.LANCZOS
                    )
                except Exception as e:
                    print(
                        f"      Rescale attempt {attempt+1}: Resize failed: {e}. Stopping."
                    )
                    break

                # Find best spot for the RESCALED image
                pos_rescaled, overlap_rescaled = find_best_spot_surrounding(
                    rescaled_img
                )

                if pos_rescaled is not None:
                    # Update the overall best position found if this attempt yielded lower overlap
                    if overlap_rescaled < min_overlap_after_rescale:
                        min_overlap_after_rescale = overlap_rescaled
                        best_pos_after_rescale = pos_rescaled
                        final_image_to_place = (
                            rescaled_img  # Store this image as potentially the best
                        )
                        print(
                            f"      Rescale attempt {attempt+1}: New best overlap {overlap_rescaled:.1f} at {pos_rescaled} size {rescaled_img.size}"
                        )

                    # Check if overlap ratio is now acceptable for THIS rescaled size
                    content_box_r = rescaled_img.getbbox()
                    area_r = 1.0
                    if content_box_r:
                        w_r = content_box_r[2] - content_box_r[0]
                        h_r = content_box_r[3] - content_box_r[1]
                        area_r = max(1.0, float(w_r * h_r))
                    else:
                        w_r, h_r = rescaled_img.size
                        area_r = max(1.0, float(w_r * h_r))

                    current_overlap_ratio = overlap_rescaled / area_r

                    if current_overlap_ratio <= max_overlap_ratio_trigger:
                        print(
                            f"      Rescale attempt {attempt+1}: Overlap ratio {current_overlap_ratio:.2f} acceptable."
                        )
                        best_pos = best_pos_after_rescale  # Use the position found for this acceptable size
                        current_scaled_img = (
                            final_image_to_place  # Use the image that achieved this
                        )
                        min_overlap_area = min_overlap_after_rescale
                        break  # Exit rescale loop, we found an acceptable size/pos
                    else:
                        print(
                            f"      Rescale attempt {attempt+1}: Overlap ratio {current_overlap_ratio:.2f} still too high."
                        )
                else:
                    print(
                        f"      Rescale attempt {attempt+1}: Could not find position for smaller size {rescaled_img.size}."
                    )

            else:  # Loop finished without break (acceptable overlap not found)
                print(
                    f"    {log_prefix}: Rescaling finished. Using best position found during attempts (overlap {min_overlap_after_rescale:.1f})."
                )
                best_pos = best_pos_after_rescale  # Use the best position found overall
                current_scaled_img = final_image_to_place  # Use the image corresponding to that best position
                min_overlap_area = min_overlap_after_rescale  # Use the overlap corresponding to that best position

        # Final Placement for surrounding item
        if best_pos is not None:
            px, py = best_pos
            try:
                placement_canvas.paste(current_scaled_img, (px, py), current_scaled_img)
                # Store the bounds of the placed content in (x, y, w, h) format
                final_cb_x1y1x2y2 = current_scaled_img.getbbox()
                if not final_cb_x1y1x2y2:
                    final_cb_x1y1x2y2 = (
                        0,
                        0,
                        current_scaled_img.width,
                        current_scaled_img.height,
                    )
                final_cb_x = final_cb_x1y1x2y2[0]
                final_cb_y = final_cb_x1y1x2y2[1]
                final_cb_w = max(1, final_cb_x1y1x2y2[2] - final_cb_x)
                final_cb_h = max(1, final_cb_x1y1x2y2[3] - final_cb_y)
                final_content_bounds_xywh = (
                    px + final_cb_x,
                    py + final_cb_y,
                    final_cb_w,
                    final_cb_h,
                )
                placed_item_bounds_xywh.append(final_content_bounds_xywh)
                size_info = f"(Initial Size {item_data.get('initial_scaled_img', Image.new('RGBA',(0,0))).size})"
                if (
                    "initial_scaled_img" in item_data
                    and current_scaled_img.size != item_data["initial_scaled_img"].size
                ):
                    size_info = f"(Rescaled to {current_scaled_img.size})"
                print(
                    f"    Placed {log_prefix} ({os.path.basename(item_path)}) at ({px},{py}) {size_info} overlap {min_overlap_area:.1f}"
                )
            except Exception as e:
                print(f"    Error pasting {log_prefix} at ({px},{py}): {e}")
        else:
            print(
                f"  Warn: Could not find any position for {log_prefix} ({os.path.basename(item_path)}). Skipping."
            )

    # --- Composite placement canvas onto original background ---
    final_image = Image.alpha_composite(canvas.copy().convert("RGBA"), placement_canvas)

    print("Finished centerpiece collage layout.")
    return final_image
