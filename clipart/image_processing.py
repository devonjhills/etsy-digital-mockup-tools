# image_processing.py
import os
import traceback
import textwrap
import random
from typing import Tuple, Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import numpy as np
import math

# Optional import for dynamic color selection using scikit-learn
try:
    from sklearn.cluster import KMeans
    from sklearn.exceptions import ConvergenceWarning
    import warnings

    # Suppress ConvergenceWarning during K-Means clustering
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not found. Dynamic color selection will be disabled.")
    print("Install it using: pip install scikit-learn")

# Relative imports for configuration and utilities
from . import config
from . import utils


# --- Helper Functions ---


def _calculate_fit_score(image: Image.Image, alpha_threshold: int) -> Tuple[float, int]:
    """
    Calculates a fit score for an image based on its content bounding box and alpha channel.
    Returns a tuple (fit_score, content_bbox_area).
    """
    try:
        bbox = image.getbbox()
        if bbox:
            bbox_width = bbox[2] - bbox[0]
            bbox_height = bbox[3] - bbox[1]
            if bbox_width > 0 and bbox_height > 0:
                content_area = bbox_width * bbox_height
                try:
                    aspect_ratio = bbox_width / bbox_height
                    squareness_score = (
                        abs(math.log(aspect_ratio))
                        if aspect_ratio > 0
                        else float("inf")
                    )
                except Exception:
                    squareness_score = float("inf")
                try:
                    cropped = image.crop(bbox)
                    if "A" in cropped.getbands():
                        alpha = np.array(cropped.split()[-1])
                        content_pixels = np.sum(alpha > alpha_threshold)
                        fill_ratio = (
                            content_pixels / content_area if content_area > 0 else 0
                        )
                        fill_score = 1.0 - fill_ratio
                    else:
                        fill_score = 0.0  # Fully opaque image
                except Exception:
                    fill_score = 0.5  # Fallback value on error
                fit_score = 0.6 * squareness_score + 0.4 * fill_score
                return fit_score, content_area
    except Exception:
        pass
    return float("inf"), 0


# --- Color Contrast Utilities ---


def compute_colorfulness(image: Image.Image) -> float:
    """
    Computes a colorfulness metric for an image.
    Uses a method inspired by Hasler & Süsstrunk:
      colorfulness = sqrt(std(rg)^2 + std(yb)^2) + 0.3 * sqrt(mean(rg)^2 + mean(yb)^2)
    """
    # Ensure image is in RGB mode
    image_rgb = image.convert("RGB")
    arr = np.array(image_rgb).astype("float")
    R = arr[:, :, 0]
    G = arr[:, :, 1]
    B = arr[:, :, 2]
    rg = R - G
    yb = 0.5 * (R + G) - B
    std_root = np.sqrt(np.std(rg) ** 2 + np.std(yb) ** 2)
    mean_root = np.sqrt(np.mean(rg) ** 2 + np.mean(yb) ** 2)
    return std_root + 0.3 * mean_root


def select_centerpiece_image(
    image_paths: List[str],
    alpha_threshold: int = 10,
) -> Optional[Image.Image]:
    """
    Loads images from paths and selects the most suitable clipart for dynamic color analysis.
    The selection is based on both the content (fit score) and a measure of colorfulness.
    The image with the highest combined score (colorfulness divided by fit score+1) is returned.
    """
    print("Selecting clipart image for color analysis (best colorful combination)...")
    if not image_paths:
        print("  Warn: No image paths provided for selection.")
        return None

    items = []
    for path in image_paths:
        original_img = utils.safe_load_image(path)
        if not original_img or original_img.width <= 0 or original_img.height <= 0:
            print(f"  Warn: Skipping invalid image: {os.path.basename(path)}")
            continue

        fit_score, content_area = _calculate_fit_score(original_img, alpha_threshold)
        colorfulness = compute_colorfulness(original_img)
        # Lower fit_score is better; higher colorfulness is better.
        combined_score = colorfulness / (fit_score + 1)
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
        print("  Error: No images successfully loaded for selection.")
        return None

    # Sort descending by the combined score.
    items.sort(key=lambda item: item["combined_score"], reverse=True)

    best_item = items[0]
    print(
        f"  Selected clipart (Combined Score: {best_item['combined_score']:.3f}, "
        f"Colorfulness: {best_item['colorfulness']:.1f}, Fit Score: {best_item['fit_score']:.3f}): "
        f"{os.path.basename(best_item['path'])}"
    )
    return best_item["original_img"]


def get_relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Calculates relative luminance for an sRGB color (WCAG formula)."""
    r, g, b = [x / 255.0 for x in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(lum1: float, lum2: float) -> float:
    """Calculates contrast ratio between two relative luminance values."""
    l1, l2 = max(lum1, lum2), min(lum1, lum2)
    return (l1 + 0.05) / (l2 + 0.05)


# --- Dynamic Colors ---


def find_dynamic_colors(
    image: Image.Image,
    n_colors: int = 5,
    min_contrast: float = 4.5,
    resize_dim: int = 100,
    min_opaque_pixels: int = 50,
    alpha_threshold: int = 50,
) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
    """
    Finds a dominant color pair (background, text) from the opaque pixels of the provided image.
    Returns a tuple (background_rgb, text_rgb) if a pair meeting the contrast is found.
    """
    if not SKLEARN_AVAILABLE:
        print("  Dynamic Colors: scikit-learn not available.")
        return None
    if not image:
        print("  Dynamic Colors: No image provided for analysis.")
        return None

    try:
        img_rgba = image.copy().convert("RGBA")
        img_rgba.thumbnail((resize_dim, resize_dim))
        pixels = np.array(img_rgba)
        alpha_channel = pixels[:, :, 3]
        opaque_mask = alpha_channel > alpha_threshold
        opaque_pixels = pixels[opaque_mask][:, :3]
        num_opaque = opaque_pixels.shape[0]
        if num_opaque < min_opaque_pixels:
            print(
                f"  Dynamic Colors: Not enough opaque pixels ({num_opaque} < {min_opaque_pixels})."
            )
            return None
        if num_opaque < n_colors:
            n_colors = max(1, num_opaque)
            print(
                f"  Dynamic Colors: Reduced clusters to {n_colors} due to low opaque pixel count."
            )

        kmeans = KMeans(
            n_clusters=n_colors, random_state=42, n_init="auto", max_iter=100
        )
        kmeans.fit(opaque_pixels)
        dominant_colors = [
            tuple(int(c) for c in color) for color in kmeans.cluster_centers_
        ]
        print(f"  Dynamic Colors: Dominant opaque colors found: {dominant_colors}")

        white, black = (255, 255, 255), (0, 0, 0)
        lum_white, lum_black = get_relative_luminance(white), get_relative_luminance(
            black
        )
        best_pair, highest_contrast = None, 0.0

        for bg_color in dominant_colors:
            if (
                bg_color in (black, white)
                and len(dominant_colors) > 1
                and highest_contrast >= min_contrast
            ):
                continue
            lum_bg = get_relative_luminance(bg_color)
            contrast_white = calculate_contrast_ratio(lum_bg, lum_white)
            if contrast_white >= min_contrast and contrast_white > highest_contrast:
                highest_contrast = contrast_white
                best_pair = (bg_color, white)
            contrast_black = calculate_contrast_ratio(lum_bg, lum_black)
            if contrast_black >= min_contrast and contrast_black > highest_contrast:
                highest_contrast = contrast_black
                best_pair = (bg_color, black)

        if best_pair:
            print(
                f"  Dynamic Colors: Selected pair {best_pair} with contrast {highest_contrast:.2f}:1"
            )
            return best_pair
        else:
            print(
                f"  Dynamic Colors: No dominant color pair with >= {min_contrast}:1 contrast found."
            )
            return None
    except Exception as e:
        print(f"Error during dynamic color extraction: {e}")
        return None


# --- Watermarking ---


def apply_watermark(
    image: Image.Image,
    opacity: int = config.WATERMARK_DEFAULT_OPACITY,
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
    if opacity <= 0 or not text:
        print("Info: Watermark skipped due to opacity/text settings.")
        return image

    base_image = image.copy().convert("RGBA")
    canvas_w, canvas_h = base_image.size
    final_alpha = max(0, min(255, opacity))
    print(f"  Watermark: Text='{text}', Opacity={opacity} -> Alpha={final_alpha}")
    if final_alpha < 10:
        print(f"  Warning: Watermark alpha value ({final_alpha}) is very low.")

    font = utils.get_font(text_font_name, text_font_size)
    if not font:
        print("Error: Cannot load watermark font. Skipping watermark.")
        return base_image

    temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    try:
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = temp_draw.textsize(text, font=font)

    if text_width <= 0 or text_height <= 0:
        print(f"Error: Watermark text '{text}' has zero dimensions. Skipping.")
        return base_image
    print(f"  Watermark text size: {text_width}x{text_height}")

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
        print(f"Error drawing text on tile: {e}. Using fallback.")
        tile_draw.text((margin, margin), text, font=font, fill=text_rgba)

    try:
        rotated_tile = text_tile.rotate(
            text_angle, expand=True, resample=Image.Resampling.BICUBIC
        )
    except Exception as e:
        print(f"Error rotating watermark tile: {e}. Skipping watermark.")
        return base_image

    rot_w, rot_h = rotated_tile.size
    if rot_w <= 0 or rot_h <= 0:
        print(
            f"Error: Rotated watermark tile has zero dimensions ({rot_w}x{rot_h}). Skipping."
        )
        return base_image
    print(f"  Rotated tile size: {rot_w}x{rot_h}")

    target_tiles_across = 5
    spc_x = max(rot_w // 2, canvas_w // target_tiles_across, 1)
    spc_y = max(rot_h // 2, canvas_h // target_tiles_across, 1)
    watermark_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    start_offset_x, start_offset_y = rot_w, rot_h
    x_start, x_end = -start_offset_x, canvas_w + start_offset_x
    y_start, y_end = -start_offset_y, canvas_h + start_offset_y

    print(f"  Tiling watermark with spacing ({spc_x}, {spc_y})...")
    paste_count = 0
    for y in range(y_start, y_end, spc_y):
        row_offset_x = (y // spc_y % 2) * (spc_x // 3)
        for x in range(x_start + row_offset_x, x_end + row_offset_x, spc_x):
            try:
                watermark_layer.paste(rotated_tile, (x, y), rotated_tile)
                paste_count += 1
            except Exception:
                pass
    print(f"  Pasted {paste_count} watermark instances.")
    if paste_count == 0:
        print("  Warning: No watermark instances pasted.")

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
) -> Image.Image:
    """
    Creates a 2x2 grid mockup from the first 4 images onto a canvas.
    """
    grid_img = canvas_bg_image.copy().convert("RGBA")
    if not input_image_paths:
        print("Warn: No input images for 2x2 grid.")
        return grid_img

    cols, rows = 2, 2
    total_pad_w, total_pad_h = padding * (cols + 1), padding * (rows + 1)
    available_w, available_h = grid_size[0] - total_pad_w, grid_size[1] - total_pad_h
    cell_w, cell_h = max(1, available_w // cols), max(1, available_h // rows)
    if cell_w <= 1 or cell_h <= 1:
        print(f"Warn: Grid cell size ({cell_w}x{cell_h}) is too small.")

    images = utils.load_images(input_image_paths[:4])
    for idx, img in enumerate(images):
        if not img:
            img_path = (
                input_image_paths[idx]
                if idx < len(input_image_paths)
                else f"image {idx+1}"
            )
            print(f"Warn: Skipping invalid image {img_path} in 2x2 grid.")
            continue
        row, col = divmod(idx, cols)
        cell_x = padding + col * (cell_w + padding)
        cell_y = padding + row * (cell_h + padding)
        try:
            img_copy = img.copy()
            img_copy.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
            thumb_w, thumb_h = img_copy.size
            offset_x, offset_y = (cell_w - thumb_w) // 2, (cell_h - thumb_h) // 2
            grid_img.paste(img_copy, (cell_x + offset_x, cell_y + offset_y), img_copy)
        except Exception as e:
            img_path = (
                input_image_paths[idx]
                if idx < len(input_image_paths)
                else f"image {idx+1}"
            )
            print(f"Warn: Pasting failed for {img_path} in 2x2 grid: {e}")
    return grid_img


# --- Transparency Demo ---


def create_transparency_demo(
    image_path: str,
    canvas_path: str = "assets/transparency_mock.png",
    scale: float = config.TRANSPARENCY_DEMO_SCALE,
) -> Optional[Image.Image]:
    """
    Creates a mockup by pasting an image onto a predefined canvas.
    """
    canvas = utils.safe_load_image(canvas_path, "RGBA")
    if not canvas:
        print(f"Error: Failed to load canvas from {canvas_path}")
        return None
    img = utils.safe_load_image(image_path, "RGBA")
    if not img:
        print(f"Warn: Could not load image {image_path} for transparency demo.")
        return canvas

    canvas_w, canvas_h = canvas.size
    max_w, max_h = int(canvas_w * 0.5 * scale), int(canvas_h * scale)
    if max_w <= 0 or max_h <= 0:
        print("Warn: Invalid scale/canvas size for transparency demo.")
        return canvas

    try:
        img_copy = img.copy()
        img_copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        img_w, img_h = img_copy.size
        paste_x = max(0, (canvas_w // 4) - (img_w // 2))
        paste_y = max(0, (canvas_h - img_h) // 2)
        canvas.paste(img_copy, (paste_x, paste_y), img_copy)
    except Exception as e:
        print(f"Error creating transparency demo for {image_path}: {e}")
        return canvas
    return canvas


# --- Title Bar and Text ---


def add_title_bar_and_text(
    image: Image.Image,
    title: str,
    subtitle_top: str,
    subtitle_bottom: str,
    image_for_color_analysis: Optional[Image.Image] = None,
    use_dynamic_colors: bool = True,
    dynamic_contrast_threshold: float = 4.5,
    dynamic_color_clusters: int = 5,
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
    """
    Adds a centered text block (title, subtitles) with a rounded backdrop and optional shadow.
    If dynamic colors are enabled and an analysis image is provided, the backdrop and text colors are selected dynamically.
    """
    if not isinstance(image, Image.Image):
        print("Error: Invalid image input to add_title_bar_and_text.")
        return None, None

    output_image = image.copy().convert("RGBA")
    canvas_w, canvas_h = output_image.size
    if canvas_w <= 0 or canvas_h <= 0:
        print("Error: Input image has zero dimensions.")
        return output_image, None

    current_bar_color, current_text_color = bar_color, text_color
    current_subtitle_color = subtitle_text_color
    current_gradient = bar_gradient

    if use_dynamic_colors and SKLEARN_AVAILABLE and image_for_color_analysis:
        print("Attempting dynamic color selection...")
        dynamic_pair = find_dynamic_colors(
            image_for_color_analysis,
            n_colors=dynamic_color_clusters,
            min_contrast=dynamic_contrast_threshold,
        )
        if dynamic_pair:
            dynamic_bg, dynamic_text = dynamic_pair
            current_bar_color = dynamic_bg
            current_text_color = dynamic_text
            current_subtitle_color = dynamic_text
            current_gradient = None
            print(
                f"  Using dynamic colors: BG={current_bar_color}, Text={current_text_color}"
            )
        else:
            print("  Dynamic color selection failed. Using default colors.")
    elif use_dynamic_colors and not SKLEARN_AVAILABLE:
        print(
            "  Dynamic colors requested but scikit-learn not available. Using default colors."
        )
    elif use_dynamic_colors:
        print(
            "  Dynamic colors requested but no analysis image provided. Using default colors."
        )

    def apply_opacity(color_tuple: Tuple, opacity_level: int) -> Tuple:
        opacity_level = max(0, min(255, opacity_level))
        base_color = color_tuple[:3]
        base_alpha = color_tuple[3] if len(color_tuple) == 4 else 255
        final_alpha = int(base_alpha * (opacity_level / 255.0))
        return base_color + (final_alpha,)

    temp_img = Image.new("RGBA", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    subtitle_font = utils.get_font(subtitle_font_name, subtitle_font_size)
    if not subtitle_font:
        print(f"Warn: Could not load subtitle font '{subtitle_font_name}'.")
        subtitle_top = subtitle_bottom = ""

    text_area_width = max(1, canvas_w - 2 * padding_x)
    best_main_font = None
    best_main_lines = []
    final_main_font_size = 0
    found_fitting_size = False

    for size in range(max_font_size, min_font_size - 1, -font_step):
        font = utils.get_font(font_name, size)
        if not font:
            continue
        try:
            test_str = "abc"
            try:
                test_len = font.getlength(test_str)
            except AttributeError:
                bbox = temp_draw.textbbox((0, 0), test_str, font=font)
                test_len = bbox[2] - bbox[0]
            avg_char_width = test_len / len(test_str) if test_len > 0 else 10
            approx_chars = max(1, int(text_area_width / avg_char_width))
            wrapped_lines = textwrap.wrap(
                title, width=approx_chars, max_lines=max_lines, placeholder="..."
            )
            if not wrapped_lines:
                continue
            max_line_width = 0
            lines_fit = True
            for line in wrapped_lines:
                bbox = temp_draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
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
                found_fitting_size = True
                break
        except Exception as e:
            print(f"Warn: Error during font size calculation at size {size}: {e}")

    if not found_fitting_size:
        print(f"Warn: Could not fit title. Using min size {min_font_size}pt.")
        font = utils.get_font(font_name, min_font_size)
        if font:
            best_main_font, final_main_font_size = font, min_font_size
            try:
                avg_char_width = (
                    font.getlength("a")
                    if hasattr(font, "getlength")
                    else (
                        temp_draw.textbbox((0, 0), "a", font=font)[2]
                        - temp_draw.textbbox((0, 0), "a", font=font)[0]
                    )
                )
            except Exception:
                avg_char_width = 10
            approx_chars = max(1, int(text_area_width / avg_char_width))
            best_main_lines = textwrap.wrap(
                title, width=approx_chars, max_lines=max_lines, placeholder="..."
            )
            if not best_main_lines and title:
                best_main_lines = [
                    title[:approx_chars] + "..." if approx_chars > 3 else ""
                ]
        else:
            print(
                f"Error: Failed to load min title font '{font_name}' size {min_font_size}pt."
            )
            best_main_lines = []

    max_text_width, main_title_height = 0, 0
    main_line_heights = []
    if best_main_lines and best_main_font:
        for line in best_main_lines:
            bbox = temp_draw.textbbox((0, 0), line, font=best_main_font)
            line_width = bbox[2] - bbox[0]
            line_height = max(1, bbox[3] - bbox[1])
            main_line_heights.append(line_height)
            max_text_width = max(max_text_width, line_width)
        main_title_height = (
            sum(main_line_heights) + (len(best_main_lines) - 1) * line_spacing
        )

    subtitle_top_height, subtitle_top_width = 0, 0
    if subtitle_top and subtitle_font:
        bbox = temp_draw.textbbox((0, 0), subtitle_top, font=subtitle_font)
        subtitle_top_width, subtitle_top_height = bbox[2] - bbox[0], max(
            1, bbox[3] - bbox[1]
        )
        max_text_width = max(max_text_width, subtitle_top_width)

    subtitle_bottom_height, subtitle_bottom_width = 0, 0
    if subtitle_bottom and subtitle_font:
        bbox = temp_draw.textbbox((0, 0), subtitle_bottom, font=subtitle_font)
        subtitle_bottom_width, subtitle_bottom_height = bbox[2] - bbox[0], max(
            1, bbox[3] - bbox[1]
        )
        max_text_width = max(max_text_width, subtitle_bottom_width)

    content_heights = [
        h
        for h in [subtitle_top_height, main_title_height, subtitle_bottom_height]
        if h > 0
    ]
    total_content_height = (
        sum(content_heights) + (len(content_heights) - 1) * subtitle_spacing
    )

    if max_text_width <= 0 or total_content_height <= 0:
        print("Warn: No text content to render. Skipping backdrop and text.")
        return output_image, None

    backdrop_width = max(1, int(max_text_width + 2 * backdrop_padding_x))
    backdrop_height = max(1, int(total_content_height + 2 * backdrop_padding_y))
    backdrop_x = (canvas_w - backdrop_width) // 2
    backdrop_y = (canvas_h - backdrop_height) // 2
    backdrop_bounds = (
        backdrop_x,
        backdrop_y,
        backdrop_x + backdrop_width,
        backdrop_y + backdrop_height,
    )

    transparent_bar = apply_opacity(current_bar_color, bar_opacity)
    transparent_gradient = None
    if current_gradient and len(current_gradient) == 2:
        try:
            transparent_gradient = (
                apply_opacity(current_gradient[0], bar_opacity),
                apply_opacity(current_gradient[1], bar_opacity),
            )
        except Exception as e:
            print(f"Warn: Could not process gradient colors: {e}.")
    transparent_shadow = apply_opacity(shadow_color, shadow_opacity)
    final_text_color = current_text_color[:3]
    final_subtitle_color = current_subtitle_color[:3]

    backdrop_layer = Image.new("RGBA", output_image.size, (0, 0, 0, 0))
    backdrop_draw = ImageDraw.Draw(backdrop_layer)
    try:
        if shadow_enable and shadow_offset != (0, 0) and transparent_shadow[3] > 0:
            shadow_bounds = (
                max(0, backdrop_bounds[0] + shadow_offset[0]),
                max(0, backdrop_bounds[1] + shadow_offset[1]),
                min(canvas_w, backdrop_bounds[2] + shadow_offset[0]),
                min(canvas_h, backdrop_bounds[3] + shadow_offset[1]),
            )
            if (
                shadow_bounds[0] < shadow_bounds[2]
                and shadow_bounds[1] < shadow_bounds[3]
            ):
                backdrop_draw.rounded_rectangle(
                    shadow_bounds,
                    fill=transparent_shadow,
                    radius=backdrop_corner_radius,
                )
            else:
                print("Warn: Shadow bounds invalid.")
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
            backdrop_layer.paste(gradient_fill, (backdrop_x, backdrop_y), mask)
        elif transparent_bar[3] > 0:
            backdrop_draw.rounded_rectangle(
                backdrop_bounds, fill=transparent_bar, radius=backdrop_corner_radius
            )
        output_image = Image.alpha_composite(output_image, backdrop_layer)
    except Exception as e:
        print(f"Error drawing backdrop: {e}")
        traceback.print_exc()

    draw = ImageDraw.Draw(output_image)
    current_y = backdrop_y + backdrop_padding_y
    text_center_x = backdrop_x + backdrop_width / 2

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
            current_y += (
                subtitle_top_height
                + (
                    subtitle_top_height
                    and (main_title_height > 0 or subtitle_bottom_height > 0)
                )
                * subtitle_spacing
            )
        except Exception as e:
            print(f"Error drawing subtitle_top: {e}")

    if main_title_height > 0 and best_main_lines and best_main_font:
        print(
            f"-> Drawing Title '{title[:30]}...' using '{font_name}' at {final_main_font_size}pt."
        )
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
                current_y += (
                    main_line_heights[i] + (i < len(best_main_lines) - 1) * line_spacing
                )
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

    return output_image, backdrop_bounds


# --- Collage Layout ---


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
    """
    Creates a collage by placing a central image and surrounding others, avoiding a title area.
    """
    print(f"Creating centerpiece collage layout for {len(image_paths)} images...")
    if not image_paths:
        print("  No images provided.")
        return canvas.copy().convert("RGBA")

    base_canvas = canvas.copy().convert("RGBA")
    placement_canvas = Image.new("RGBA", base_canvas.size, (0, 0, 0, 0))
    canvas_w, canvas_h = base_canvas.size
    min_pixel_dim = 20

    if canvas_w <= 0 or canvas_h <= 0:
        print("  Error: Invalid canvas dimensions.")
        return base_canvas

    items = []
    print("  Loading images and calculating centerpiece suitability...")
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
        print("  Warn: No valid fit score. Falling back to largest area.")
        items.sort(key=lambda item: -item.get("content_bbox_area", 0))
        if items[0]["content_bbox_area"] == 0:
            print("  Error: No items with positive content area.")
            return base_canvas

    centerpiece_data = items.pop(0)
    surrounding_items = items
    print(
        f"  Centerpiece (Score: {centerpiece_data.get('fit_score', 'N/A'):.3f}): {os.path.basename(centerpiece_data['path'])}"
    )
    print(f"  Surrounding items: {len(surrounding_items)}")

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
        print(f"  Avoidance Rect (Title): {avoid_rect_title}")

    print("  Placing centerpiece...")
    centerpiece_img = centerpiece_data["original_img"]
    avoid_rect_centerpiece = None
    try:
        target_dim = min(canvas_w, canvas_h) * centerpiece_scale_factor
        scale_factor = target_dim / max(centerpiece_img.width, centerpiece_img.height)
        cp_w = max(min_pixel_dim, int(centerpiece_img.width * scale_factor))
        cp_h = max(min_pixel_dim, int(centerpiece_img.height * scale_factor))
        centerpiece_scaled = centerpiece_img.resize(
            (cp_w, cp_h), Image.Resampling.LANCZOS
        )
        cp_x, cp_y = (canvas_w - cp_w) // 2, (canvas_h - cp_h) // 2
        placement_canvas.paste(centerpiece_scaled, (cp_x, cp_y), centerpiece_scaled)
        cp_bbox = centerpiece_scaled.getbbox()
        if cp_bbox:
            cp_x_local, cp_y_local, cp_x2_local, cp_y2_local = cp_bbox
            cp_w_local = max(1, cp_x2_local - cp_x_local)
            cp_h_local = max(1, cp_y2_local - cp_y_local)
            cp_content_bounds = (
                cp_x + cp_x_local,
                cp_y + cp_y_local,
                cp_w_local,
                cp_h_local,
            )
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
            if avoid_cp[2] - avoid_cp[0] > 0 and avoid_cp[3] - avoid_cp[1] > 0:
                avoid_rect_centerpiece = avoid_cp
                print(
                    f"  Avoidance Rect (Centerpiece Content): {avoid_rect_centerpiece}"
                )
            else:
                print("  Warn: Centerpiece avoidance rect has zero dimension.")
        else:
            print("  Warn: Centerpiece has no content bbox.")
    except Exception as e:
        print(f"  Error placing centerpiece: {e}")
        traceback.print_exc()

    surrounding_prepared = []
    print("  Preparing surrounding items...")
    for item in surrounding_items:
        try:
            min_target_w = canvas_w * surround_min_width_factor
            max_target_w = canvas_w * surround_max_width_factor
            target_w = random.uniform(min_target_w, max_target_w)
            scale = max(
                target_w / max(item["original_img"].width, 1), min_absolute_scale
            )
            new_w = max(min_pixel_dim, int(item["original_img"].width * scale))
            new_h = max(min_pixel_dim, int(item["original_img"].height * scale))
            scaled_img = item["original_img"].resize(
                (new_w, new_h), Image.Resampling.LANCZOS
            )
            item["initial_scaled_img"] = scaled_img
            item["initial_scale"] = scale
            bbox = scaled_img.getbbox()
            item["initial_content_area"] = max(
                1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if bbox else new_w * new_h
            )
            surrounding_prepared.append(item)
        except Exception as e:
            print(
                f"  Warn: Failed to prepare surrounding image '{os.path.basename(item['path'])}': {e}"
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
        cb = image_to_place.getbbox() or (0, 0, img_w, img_h)
        cb_x, cb_y = cb[0], cb[1]
        cb_w, cb_h = max(1, cb[2] - cb[0]), max(1, cb[3] - cb[1])
        for py in range(0, canvas_h - img_h + 1, placement_step):
            for px in range(0, canvas_w - img_w + 1, placement_step):
                current_bounds = (px + cb_x, py + cb_y, cb_w, cb_h)
                center_x, center_y = (
                    current_bounds[0] + cb_w / 2,
                    current_bounds[1] + cb_h / 2,
                )
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
                    if overlaps:
                        overlap_total += area
                if overlap_total < min_overlap:
                    min_overlap = overlap_total
                    best_pos = (px, py)
                    if min_overlap == 0:
                        return best_pos, min_overlap
        return best_pos, min_overlap

    print("  Placing surrounding items...")
    for item in surrounding_prepared:
        log_prefix = f"Item {item['id']} ({os.path.basename(item['path'])})"
        current_img = item["initial_scaled_img"]
        best_pos, overlap_area = find_best_spot(current_img)
        needs_rescale = False
        cb = current_img.getbbox()
        if cb:
            w, h = cb[2] - cb[0], cb[3] - cb[1]
            current_area = max(1.0, float(w * h))
        else:
            current_area = float(current_img.size[0] * current_img.size[1])
        if (
            best_pos is not None
            and (overlap_area / current_area) > max_overlap_ratio_trigger
        ):
            needs_rescale = True
            print(
                f"    {log_prefix}: Overlap ratio {(overlap_area / current_area):.2f} exceeds threshold. Rescaling."
            )
        if needs_rescale:
            best_pos_rescaled, best_overlap_rescaled = best_pos, overlap_area
            final_img = current_img
            for attempt in range(rescale_attempts):
                new_scale = item["initial_scale"] * (rescale_factor ** (attempt + 1))
                if new_scale < min_absolute_scale:
                    print(
                        f"      Rescale {attempt+1}: Scale {new_scale:.3f} below minimum. Stopping."
                    )
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
                    print(f"      Rescale {attempt+1}: Resize failed: {e}. Stopping.")
                    break
                pos, overlap_rescaled = find_best_spot(rescaled_img)
                if pos is not None and overlap_rescaled < best_overlap_rescaled:
                    best_overlap_rescaled = overlap_rescaled
                    best_pos_rescaled = pos
                    final_img = rescaled_img
                    cb_rescaled = rescaled_img.getbbox() or (0, 0, new_w, new_h)
                    area_r = max(
                        1.0,
                        float(
                            (cb_rescaled[2] - cb_rescaled[0])
                            * (cb_rescaled[3] - cb_rescaled[1])
                        ),
                    )
                    if (overlap_rescaled / area_r) <= max_overlap_ratio_trigger:
                        print(
                            f"      Rescale {attempt+1}: Acceptable overlap ratio achieved."
                        )
                        best_pos, current_img, overlap_area = (
                            best_pos_rescaled,
                            final_img,
                            best_overlap_rescaled,
                        )
                        break
                else:
                    print(
                        f"      Rescale {attempt+1}: No better position found. Stopping."
                    )
                    break
            else:
                print(
                    f"    {log_prefix}: Rescaling finished. Using best found overlap {best_overlap_rescaled:.1f}."
                )
                best_pos, current_img, overlap_area = (
                    best_pos_rescaled,
                    final_img,
                    best_overlap_rescaled,
                )

        if best_pos is not None:
            px, py = best_pos
            try:
                placement_canvas.paste(current_img, (px, py), current_img)
                final_bbox = current_img.getbbox() or (
                    0,
                    0,
                    current_img.size[0],
                    current_img.size[1],
                )
                placed_bounds.append(
                    (
                        px + final_bbox[0],
                        py + final_bbox[1],
                        max(1, final_bbox[2] - final_bbox[0]),
                        max(1, final_bbox[3] - final_bbox[1]),
                    )
                )
                size_info = f"(Size {current_img.size})"
                if current_img.size != item["initial_scaled_img"].size:
                    size_info = f"(Rescaled to {current_img.size})"
                print(
                    f"    Placed {log_prefix} at ({px},{py}) {size_info} with overlap {overlap_area:.1f}"
                )
            except Exception as e:
                print(f"    Error pasting {log_prefix} at ({px},{py}): {e}")
        else:
            print(f"  Warn: Could not find position for {log_prefix}. Skipping.")

    final_image = Image.alpha_composite(base_canvas, placement_canvas)
    print("Finished centerpiece collage layout.")
    return final_image
