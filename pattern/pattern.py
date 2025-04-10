import os
import glob
import math
import sys  # Good practice

# NOTE: Import Image directly for access to constants like LANCZOS if needed
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# --- Define Base Paths Relative to Script Location ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
INPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "input")


# --- Helper Function to get Asset Paths ---
def get_asset_path(asset_name):
    """Returns the absolute path to an asset (font or image)."""
    # Adjusted to look in assets/fonts or directly in assets
    if asset_name.lower().endswith((".ttf", ".otf")):
        path = os.path.join(ASSETS_DIR, "fonts", asset_name)
    else:
        path = os.path.join(ASSETS_DIR, asset_name)

    if not os.path.exists(path):
        # Use print instead of log for direct user feedback if asset missing
        print(f"Warning: Asset not found at expected location: {path}")
        # Return None or raise error based on how critical the asset is
        return None  # Allow graceful handling if asset is optional
    return path


# --- Handle Pillow Resampling Filter Compatibility ---
try:
    # Newer Pillow versions (>= 9.1.0) use Resampling enum
    DEFAULT_RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    # Fallback for older Pillow versions
    DEFAULT_RESAMPLE_FILTER = Image.LANCZOS


# ==============================================================================
# ORIGINAL Mockup Functions (Restored Logic, Fixed Paths)
# ==============================================================================
def create_main_mockup(input_folder, title):
    """Creates the main 2x6 grid mockup. (Original Logic & Positioning)"""
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    GRID_ROWS, GRID_COLS = 2, 6
    print(f"  Creating main mockup for '{title}'...")

    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not images:
        print(f"    No images found in {input_folder} for main mockup.")
        return

    grid_width = 3000
    grid_height = 2250

    background_color = (222, 215, 211, 255)
    grid_canvas = Image.new("RGBA", (grid_width, grid_height), background_color)

    # --- Original Calculations ---
    # Fixed cell height
    cell_height = grid_height // GRID_ROWS
    # Fixed *average* cell width for spacing calculation
    avg_cell_width = grid_width // GRID_COLS

    # Spacing based on *average* cell width
    total_spacing_x = grid_width - (avg_cell_width * GRID_COLS)
    spacing_between_x = total_spacing_x / (GRID_COLS + 1) if GRID_COLS > 0 else 0
    # --- End Original Calculations ---

    # Load shadow
    shadow_path = get_asset_path("shadow.png")
    shadow = None
    shadow_new_width = 0
    if shadow_path:
        try:
            shadow_img = Image.open(shadow_path).convert("RGBA")
            scale_factor = (
                cell_height / shadow_img.height if shadow_img.height > 0 else 1
            )
            shadow_new_width = int(shadow_img.width * scale_factor)
            if shadow_new_width > 0 and cell_height > 0:
                shadow = shadow_img.resize(
                    (shadow_new_width, cell_height), DEFAULT_RESAMPLE_FILTER
                )
        except Exception as e:
            print(f"    Error loading or resizing shadow: {e}. Skipping shadow.")

    # First pass: Draw images using original placement
    image_positions_for_shadow = []  # Store the ACTUAL paste position for shadows
    images_to_place = images[: GRID_ROWS * GRID_COLS]

    for i, img_path in enumerate(images_to_place):
        try:
            img = Image.open(img_path).convert("RGBA")
            # Resize based on height, maintain aspect ratio -> variable width
            img_aspect = img.width / img.height if img.height > 0 else 1
            img_new_width = int(cell_height * img_aspect)
            img_new_height = cell_height  # Should equal cell_height
            if img_new_width <= 0 or img_new_height <= 0:
                continue  # Skip invalid size

            img_resized = img.resize(
                (img_new_width, img_new_height), DEFAULT_RESAMPLE_FILTER
            )

            row_index = i // GRID_COLS
            col_index = i % GRID_COLS

            # --- Original Positioning Calculation ---
            # Calculate top-left corner based on grid column index, average width, and spacing
            x_pos = int(
                (col_index + 1) * spacing_between_x + col_index * avg_cell_width
            )
            y_pos = int(row_index * cell_height)  # Simple row positioning
            # --- End Original Positioning Calculation ---

            # Store the calculated (x_pos, y_pos) for shadow placement relative to this point
            image_positions_for_shadow.append((x_pos, y_pos))

            # --- Direct Paste at Calculated Position ---
            # Paste the image (variable width) directly at the calculated x_pos, y_pos
            grid_canvas.paste(img_resized, (x_pos, y_pos), img_resized)  # Use mask

        except Exception as e:
            print(f"    Error processing image {img_path}: {e}")

    # Second pass: Add shadows relative to the calculated image start positions
    if shadow:
        for x_pos, y_pos in image_positions_for_shadow:
            # Original shadow placement logic (relative to the calculated x_pos)
            shadow_x = x_pos - shadow_new_width + 5  # Original offset
            shadow_y = y_pos
            try:
                # Basic bounds check before pasting
                if (
                    shadow_x < grid_width
                    and shadow_y < grid_height
                    and shadow_x + shadow.width > 0
                    and shadow_y + shadow.height > 0
                ):
                    grid_canvas.paste(shadow, (shadow_x, shadow_y), shadow)  # Use mask
            except Exception as e:
                print(f"    Error pasting shadow at ({shadow_x},{shadow_y}): {e}")

    # Add overlay
    final_image = grid_canvas
    overlay_path = get_asset_path("overlay.png")
    if overlay_path:
        try:
            overlay = Image.open(overlay_path).convert("RGBA")
            overlay = overlay.resize((grid_width, grid_height), DEFAULT_RESAMPLE_FILTER)
            final_image = Image.alpha_composite(grid_canvas, overlay)
        except Exception as e:
            print(
                f"    Error loading or applying overlay: {e}. Using image without overlay."
            )

    final_image = final_image.convert("RGB")  # Convert before adding text/saving

    # Add title text (Original font/size/color/placement)
    try:
        draw = ImageDraw.Draw(final_image)
        font_path = get_asset_path("Clattering.ttf")
        if not font_path:
            raise FileNotFoundError("Clattering.ttf not found")
        initial_font_size, max_width = 200, 1380

        def get_font_and_size(f_path, size, text_to_draw):
            font = ImageFont.truetype(f_path, size)
            try:
                bbox = draw.textbbox((0, 0), text_to_draw, font=font)
                return font, bbox[2] - bbox[0], bbox[3] - bbox[1]
            except AttributeError:
                text_width, text_height = draw.textsize(text_to_draw, font=font)
                return font, text_width, text_height

        font_size = initial_font_size
        font, text_width, text_height = get_font_and_size(font_path, font_size, title)
        while text_width > max_width and font_size > 50:
            font_size -= 5
            font, text_width, text_height = get_font_and_size(
                font_path, font_size, title
            )

        text_x = (grid_width - text_width) // 2
        text_y = (grid_height - text_height) // 2  # Original had vertical_offset = 0

        draw.text(
            (text_x, text_y), title, font=font, fill=(238, 186, 43), anchor="lt"
        )  # Original color/anchor

    except (FileNotFoundError, Exception) as e:
        print(f"    Error adding title: {e}")

    # Save final image (Original name/format)
    try:
        grid_filename = "main.png"  # Original filename
        save_path = os.path.join(output_folder, grid_filename)
        final_image.save(save_path, "PNG")
        print(f"    Main mockup saved: {save_path}")
    except Exception as e:
        print(f"    Error saving main mockup: {e}")


def create_large_grid(input_folder):
    """Creates layered/rotated mockups. (Original Logic)"""
    print("  Creating layered composite outputs...")
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    images = sorted(
        glob.glob(os.path.join(input_folder, "*.jpg"))
    )  # Original: JPG only

    num_images = len(images)
    if num_images < 3:  # Original check
        print(
            f"    Skipping layered composite: At least 3 JPG images required, found {num_images}."
        )
        return

    # --- Original Settings ---
    CANVAS_WIDTH = 2800
    CANVAS_HEIGHT = 2250
    center_target_size = (2400, 2400)  # Original size
    bottom_left_target_size = (1800, 1800)  # Original size
    center_rotation = -25  # Original angle
    bottom_left_rotation = -15  # Original angle
    shadow_offset = 25  # Original offset
    shadow_blur = 15  # Original blur
    shadow_opacity = 120  # Original opacity

    # Original logic for determining number of sets (up to 4)
    max_sets = min(4, num_images // 3)
    print(f"    Generating {max_sets} layered set(s)...")

    for set_index in range(max_sets):
        print(f"      Processing set {set_index + 1}...")
        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")

        # --- Backdrop Image ---
        backdrop_img_index = set_index * 3
        try:
            backdrop_img = Image.open(images[backdrop_img_index]).convert("RGB")
            # Original fit logic
            backdrop_img_resized = ImageOps.fit(
                backdrop_img,
                (CANVAS_WIDTH, CANVAS_HEIGHT),
                method=DEFAULT_RESAMPLE_FILTER,
            )
            offset_x = (CANVAS_WIDTH - backdrop_img_resized.width) // 2
            offset_y = (CANVAS_HEIGHT - backdrop_img_resized.height) // 2
            canvas.paste(backdrop_img_resized, (offset_x, offset_y))
        except Exception as e:
            print(
                f"      Error processing backdrop image {images[backdrop_img_index]}: {e}"
            )
            continue

        # --- Center Image (Original Logic) ---
        center_img_index = set_index * 3 + 1
        if center_img_index < num_images:
            try:
                center_img = Image.open(images[center_img_index]).convert("RGBA")
                center_img = ImageOps.fit(
                    center_img, center_target_size, method=DEFAULT_RESAMPLE_FILTER
                )
                center_img_rotated = center_img.rotate(
                    center_rotation, expand=True, resample=Image.BICUBIC
                )

                # Original offsets
                center_offset_x_base = (CANVAS_WIDTH - center_target_size[0]) // 2 - 800
                center_offset_y_base = (
                    CANVAS_HEIGHT - center_target_size[1]
                ) // 2 + 100
                # Original rotation adjustment
                center_offset_x = (
                    center_offset_x_base
                    - (center_img_rotated.width - center_target_size[0]) // 2
                )
                center_offset_y = (
                    center_offset_y_base
                    - (center_img_rotated.height - center_target_size[1]) // 2
                )

                # Original shadow creation and placement (two shadows)
                center_shadow = Image.new("RGBA", center_img_rotated.size, (0, 0, 0, 0))
                try:
                    center_alpha = center_img_rotated.split()[3]
                    center_shadow.paste((0, 0, 0, shadow_opacity), mask=center_alpha)
                    center_shadow_blurred = center_shadow.filter(
                        ImageFilter.GaussianBlur(shadow_blur)
                    )
                    # Shadow 1 (top-right offset)
                    canvas.paste(
                        center_shadow_blurred,
                        (
                            center_offset_x + shadow_offset,
                            center_offset_y + shadow_offset,
                        ),
                        center_shadow_blurred,
                    )
                    # Shadow 2 (top-left offset - check original carefully, was it top-left or bottom-left?)
                    # *Assuming original meant bottom-left based on visual offset directions*
                    # No, original code shows (-offset, -offset) which is top-left
                    canvas.paste(
                        center_shadow_blurred,
                        (
                            center_offset_x - shadow_offset,
                            center_offset_y - shadow_offset,
                        ),
                        center_shadow_blurred,
                    )
                except IndexError:
                    print(
                        f"       Warning: Center Image {images[center_img_index]} has no alpha channel for shadow."
                    )
                except Exception as e:
                    print(
                        f"       Error creating/pasting center shadow for {images[center_img_index]}: {e}"
                    )

                canvas.paste(
                    center_img_rotated,
                    (center_offset_x, center_offset_y),
                    center_img_rotated,
                )
            except Exception as e:
                print(
                    f"      Error processing center image {images[center_img_index]}: {e}"
                )

        # --- Bottom-Left Image (Original Logic) ---
        bottom_left_img_index = set_index * 3 + 2
        if bottom_left_img_index < num_images:
            try:
                bottom_left_img = Image.open(images[bottom_left_img_index]).convert(
                    "RGBA"
                )
                bottom_left_img = ImageOps.fit(
                    bottom_left_img,
                    bottom_left_target_size,
                    method=DEFAULT_RESAMPLE_FILTER,
                )
                bottom_left_img_rotated = bottom_left_img.rotate(
                    bottom_left_rotation, expand=True, resample=Image.BICUBIC
                )

                # Original offsets
                bottom_left_offset_x_base = -400
                bottom_left_offset_y_base = (
                    CANVAS_HEIGHT - bottom_left_target_size[1] + 300
                )
                # Original rotation adjustment
                bottom_left_offset_x = (
                    bottom_left_offset_x_base
                    - (bottom_left_img_rotated.width - bottom_left_target_size[0]) // 2
                )
                bottom_left_offset_y = (
                    bottom_left_offset_y_base
                    - (bottom_left_img_rotated.height - bottom_left_target_size[1]) // 2
                )

                # Original shadow creation and placement (two shadows)
                bottom_left_shadow = Image.new(
                    "RGBA", bottom_left_img_rotated.size, (0, 0, 0, 0)
                )
                try:
                    bottom_left_alpha = bottom_left_img_rotated.split()[3]
                    bottom_left_shadow.paste(
                        (0, 0, 0, shadow_opacity), mask=bottom_left_alpha
                    )
                    bottom_left_shadow_blurred = bottom_left_shadow.filter(
                        ImageFilter.GaussianBlur(shadow_blur)
                    )
                    # Shadow 1 (bottom-right offset)
                    canvas.paste(
                        bottom_left_shadow_blurred,
                        (
                            bottom_left_offset_x + shadow_offset,
                            bottom_left_offset_y + shadow_offset,
                        ),
                        bottom_left_shadow_blurred,
                    )
                    # Shadow 2 (top-left offset)
                    canvas.paste(
                        bottom_left_shadow_blurred,
                        (
                            bottom_left_offset_x - shadow_offset,
                            bottom_left_offset_y - shadow_offset,
                        ),
                        bottom_left_shadow_blurred,
                    )
                except IndexError:
                    print(
                        f"       Warning: Bottom-Left Image {images[bottom_left_img_index]} has no alpha channel for shadow."
                    )
                except Exception as e:
                    print(
                        f"       Error creating/pasting bottom-left shadow for {images[bottom_left_img_index]}: {e}"
                    )

                canvas.paste(
                    bottom_left_img_rotated,
                    (bottom_left_offset_x, bottom_left_offset_y),
                    bottom_left_img_rotated,
                )
            except Exception as e:
                print(
                    f"      Error processing bottom-left image {images[bottom_left_img_index]}: {e}"
                )

        # --- Save the Result (Original Logic) ---
        try:
            output_filename = f"layered_mockup_{set_index + 1}.jpg"  # Original name
            save_path = os.path.join(output_folder, output_filename)
            canvas.save(
                save_path, "JPEG", quality=95, optimize=True
            )  # Original settings
            print(f"      Layered mockup saved: {save_path}")
        except Exception as e:
            print(f"      Error saving layered mockup {set_index + 1}: {e}")


def create_pattern(input_folder):
    """Creates a simple 2x2 tiled seamless pattern image. (Original Logic)"""
    print("  Creating seamless pattern image...")  # Original message adjusted slightly
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    # Original logic took only first image (any type, but later code implies jpg)
    # Reverting to original glob, assumes pattern_resize made them jpg.
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))[
        :1
    ]  # Original logic + jpg assumption
    if not images:
        print("    No JPG images found for seamless pattern.")
        return

    image_path = images[0]
    IMAGE_SIZE = 2048  # Original size
    GRID_SIZE = 2  # Original grid

    try:
        output_image = Image.new("RGBA", (IMAGE_SIZE, IMAGE_SIZE))
        source_image = Image.open(image_path).convert("RGBA")

        cell_size = IMAGE_SIZE // GRID_SIZE
        source_image = source_image.resize(
            (cell_size, cell_size), DEFAULT_RESAMPLE_FILTER
        )

        # Create 2x2 grid
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                output_image.paste(
                    source_image, (col * cell_size, row * cell_size), source_image
                )  # Use mask

        # Original text overlay logic
        txt_layer = Image.new("RGBA", output_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)  # Renamed from txtLayer
        try:
            # Use corrected path helper
            font_path = get_asset_path("Clattering.ttf")
            if not font_path:
                raise FileNotFoundError("Clattering.ttf not found")
            font = ImageFont.truetype(font_path, 185)  # Original size
        except (FileNotFoundError, Exception) as e:
            print(f"    Warning: Clattering font not found ({e}). Using default font.")
            try:
                font = ImageFont.load_default(size=185)
            except AttributeError:
                font = ImageFont.load_default().font_variant(size=185)

        text = "Seamless Patterns"  # Original text
        text_position = (IMAGE_SIZE // 2, IMAGE_SIZE // 2)  # Original position

        # Original outline drawing logic
        offsets = [(x, y) for x in (-3, 3) for y in (-3, 3)]  # Original offsets
        for offset_x, offset_y in offsets:
            draw.text(
                (text_position[0] + offset_x, text_position[1] + offset_y),
                text,
                font=font,
                fill=(255, 255, 255, 192),  # Original white border color
                anchor="mm",
                align="center",
            )
        # Draw main black text on top
        draw.text(
            text_position,
            text,
            font=font,
            fill=(0, 0, 0, 192),  # Original black text color
            anchor="mm",
            align="center",
        )

        combined = Image.alpha_composite(output_image, txt_layer)

        # Save (Original Logic)
        # Original name included index, but loop only ran once. Let's match name exactly.
        index = 0  # Simulate original loop index for filename
        filename = f"seamless_{index + 1}.jpg"
        save_path = os.path.join(output_folder, filename)
        combined.convert("RGB").save(
            save_path,
            "JPEG",
            quality=85,
            optimize=True,
            subsampling="4:2:0",  # Original settings
        )
        print(f"    Seamless pattern saved: {save_path}")
        return save_path  # Return path for video function

    except Exception as e:
        print(f"    Error creating seamless pattern for {image_path}: {e}")
        return None


def create_seamless_zoom_video(input_folder, seamless_image_path):
    """Creates a zoom-out video from the seamless pattern image. (Original Logic)"""
    print("  Creating seamless zoom video...")  # Adjusted message slightly
    # Input path is now passed directly
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)  # Ensure output folder exists

    # Original logic checked for seamless_1.jpg *before* function call implicitly
    # Now check passed path
    if not seamless_image_path or not os.path.exists(seamless_image_path):
        print(
            f"    Seamless pattern image '{seamless_image_path or 'None'}' not found. Skipping zoom video."
        )
        return

    try:
        import cv2
    except ImportError:
        print("    OpenCV (cv2) is not installed. Skipping video creation.")
        print("    Install using: pip install opencv-python")
        return

    try:
        img = cv2.imread(seamless_image_path)
        if img is None:
            print(f"    Error: OpenCV could not read image: {seamless_image_path}")
            return

        height, width = img.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Original codec
        video_path = os.path.join(output_folder, "video_seamless.mp4")  # Original name
        video = cv2.VideoWriter(
            video_path, fourcc, 30.0, (width, height)
        )  # Original FPS/size
        total_frames = 90  # Original frames
        initial_zoom = 1.5  # Original zoom

        for i in range(total_frames):
            # Original zoom interpolation logic
            t = i / (total_frames - 1) if total_frames > 1 else 0
            zoom_factor = initial_zoom - (initial_zoom - 1) * t
            if zoom_factor <= 0:
                continue  # Avoid division by zero

            new_w = int(width / zoom_factor)
            new_h = int(height / zoom_factor)
            x1 = max(0, (width - new_w) // 2)
            y1 = max(0, (height - new_h) // 2)
            # Clamp dimensions to prevent exceeding original boundaries
            new_w = min(new_w, width - x1)
            new_h = min(new_h, height - y1)

            if new_w <= 0 or new_h <= 0:
                continue  # Skip if calculated size is invalid

            crop = img[y1 : y1 + new_h, x1 : x1 + new_w]

            if crop is not None and crop.size > 0:
                frame = cv2.resize(
                    crop, (width, height), interpolation=cv2.INTER_LINEAR
                )
                video.write(frame)
            # else: # Original didn't warn on bad crop? Add if needed.
            #      print(f"    Warning: Invalid crop result at frame {i}. Skipping frame.")

        video.release()
        print(f"    Seamless zoom video saved: {video_path}")

    except Exception as e:
        print(f"    Error creating seamless zoom video: {e}")


def create_grid_mockup_with_borders(
    input_folder, border_width=15, watermark_text="© digital veil"
):
    """Creates a 4x3 grid mockup with white borders and watermark. (Original Logic)"""
    print("  Creating grid mockup with borders...")  # Adjusted message
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    images = sorted(
        glob.glob(os.path.join(input_folder, "*.[jp][pn][g]"))
    )  # Original glob
    if not images:
        print("    No images found for grid mockup.")  # Adjusted message
        return

    images_to_place = images[:12]  # Original limit
    # Original didn't warn about fewer than 12 images, so removed warning

    grid_rows, grid_cols = 3, 4  # Original grid size

    # Original size calculation logic
    avg_aspect = 1.0
    try:
        img_samples = [Image.open(img) for img in images_to_place[:3]]
        if img_samples:
            valid_aspects = [
                img.width / img.height for img in img_samples if img.height > 0
            ]
            if valid_aspects:
                avg_aspect = sum(valid_aspects) / len(valid_aspects)
    except Exception as e:
        print(f"    Warning: Could not determine average aspect ratio: {e}")

    grid_width = 3000  # Original width
    cell_width = (grid_width - (grid_cols + 1) * border_width) // grid_cols
    cell_height = int(cell_width / avg_aspect) if avg_aspect > 0 else cell_width
    grid_height = (cell_height * grid_rows) + ((grid_rows + 1) * border_width)

    if cell_width <= 0 or cell_height <= 0:
        print(
            f"    Error: Calculated cell dimensions invalid ({cell_width}x{cell_height})."
        )
        return

    grid_canvas = Image.new(
        "RGB", (grid_width, grid_height), (255, 255, 255)
    )  # Original bg

    # Place images (Original Logic)
    for i, img_path in enumerate(images_to_place):
        try:
            img = Image.open(img_path).convert("RGB")
            img = img.resize((cell_width, cell_height), DEFAULT_RESAMPLE_FILTER)
            row_index = i // grid_cols
            col_index = i % grid_cols
            x_pos = border_width + col_index * (cell_width + border_width)
            y_pos = border_width + row_index * (cell_height + border_width)
            grid_canvas.paste(img, (x_pos, y_pos))
        except Exception as e:
            print(f"    Error processing or pasting image {img_path}: {e}")

    # Add staggered watermarks (Original Logic)
    try:
        # Original font finding logic
        try:
            font_path = get_asset_path("DSMarkerFelt.ttf")
            if not font_path:
                raise FileNotFoundError("DSMarkerFelt.ttf not found")
            font = ImageFont.truetype(font_path, 80)  # Original size
        except (FileNotFoundError, IOError) as e:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 80)  # Original size
            except IOError:
                font = ImageFont.load_default().font_variant(
                    size=80
                )  # Original fallback

        txt_layer = Image.new("RGBA", grid_canvas.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)  # Renamed from d

        # Use textbbox if possible, fallback to textsize
        try:
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            watermark_width, watermark_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            watermark_width, watermark_height = draw.textsize(watermark_text, font=font)

        if watermark_width <= 0 or watermark_height <= 0:
            raise ValueError("Watermark zero size.")

        # Original placement calculation logic
        num_watermarks_x = 5  # Original count
        num_watermarks_y = 7  # Original count

        for i in range(num_watermarks_y):
            for j in range(num_watermarks_x):
                offset = (watermark_width / 2) if i % 2 else 0  # Original stagger
                # Original position calculation
                x = (
                    (j * grid_width // (num_watermarks_x - 1))
                    - watermark_width // 2
                    + offset
                )
                y = (i * grid_height // (num_watermarks_y - 1)) - watermark_height // 2
                # Original drawing logic (shadow + text)
                draw.text(
                    (x + 2, y + 2), watermark_text, fill=(0, 0, 0, 30), font=font
                )  # Original shadow
                draw.text(
                    (x, y), watermark_text, fill=(255, 255, 255, 128), font=font
                )  # Original text

        # Original rotation logic
        angle = -30  # Original angle
        txt_layer_rotated = txt_layer.rotate(
            angle, resample=Image.BICUBIC, expand=False
        )

        # Original compositing logic
        grid_canvas_rgba = grid_canvas.convert("RGBA")
        final_image = Image.alpha_composite(grid_canvas_rgba, txt_layer_rotated)
        final_image = final_image.convert("RGB")

    except (FileNotFoundError, Exception) as e:  # Added FileNotFoundError
        print(f"    Error adding watermark: {e}")
        final_image = grid_canvas  # Use canvas without watermark if error

    # Save the result (Original Logic)
    try:
        output_path = os.path.join(
            output_folder, "grid_mockup_with_borders.jpg"
        )  # Original name
        final_image.save(output_path, "JPEG", quality=95)  # Original quality
        print(f"    Grid mockup with borders saved: {output_path}")  # Adjusted message
    except Exception as e:
        print(f"    Error saving grid mockup with borders: {e}")


# ==============================================================================
# SEAMLESS MOCKUP Function (Keep Previously Restored Version)
# ==============================================================================
def create_seamless_mockup(input_folder):
    """Creates a mockup showing a single tile next to a 2x2 seamless representation using canvas2.png."""
    print("  Creating original seamless comparison mockup...")
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    input_files = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if not input_files:
        print("    No image files found in input folder for seamless mockup.")
        return
    input_image_path = input_files[0]

    try:
        input_img = Image.open(input_image_path)
        if input_img.mode != "RGBA":
            input_img = input_img.convert("RGBA")
        cell_max_size = (550, 550)
        scaled_img = input_img.copy()
        scaled_img.thumbnail(cell_max_size, DEFAULT_RESAMPLE_FILTER)
        cell_width, cell_height = scaled_img.size

        try:
            canvas_path = get_asset_path("canvas2.png")
            if not canvas_path:
                raise FileNotFoundError("canvas2.png asset not found")
            canvas = Image.open(canvas_path).convert("RGBA")
            canvas_target_size = (2000, 2000)
            canvas = canvas.resize(canvas_target_size, DEFAULT_RESAMPLE_FILTER)
        except (FileNotFoundError, Exception) as e:
            print(
                f"    Warning: Canvas background 'canvas2.png' not found or failed ({e}). Using white."
            )
            canvas_target_size = (2000, 2000)
            canvas = Image.new("RGBA", canvas_target_size, (255, 255, 255, 255))

        canvas_width, canvas_height = canvas.size
        margin, arrow_gap = 100, 100
        left_x, left_y = margin, (canvas_height - cell_height) // 2
        canvas.paste(scaled_img, (left_x, left_y), scaled_img)
        grid_x = left_x + cell_width + arrow_gap
        grid_y = (canvas_height - (2 * cell_height)) // 2
        for i in range(2):
            for j in range(2):
                pos = (grid_x + j * cell_width, grid_y + i * cell_height)
                canvas.paste(scaled_img, pos, scaled_img)

        output_image_path = os.path.join(output_folder, "output_mockup.png")
        canvas.save(output_image_path, "PNG")
        print(f"    Original seamless comparison mockup saved: {output_image_path}")
    except Exception as e:
        print(
            f"    Error creating original seamless comparison mockup for {input_image_path}: {e}"
        )


# ==============================================================================
# Main Execution Logic (Using Corrected Paths and Restored Function Logic)
# ==============================================================================
if __name__ == "__main__":
    print("Starting mockup generation process...")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Input Base Dir: {INPUT_BASE_DIR}")
    print(f"Assets Dir: {ASSETS_DIR}")

    if not os.path.isdir(INPUT_BASE_DIR):
        print(f"Error: Base input directory not found at '{INPUT_BASE_DIR}'")
        sys.exit(1)

    folders_to_ignore = {"mocks", "zipped"}

    subfolders_found = [
        d
        for d in os.listdir(INPUT_BASE_DIR)
        if os.path.isdir(os.path.join(INPUT_BASE_DIR, d)) and d not in folders_to_ignore
    ]

    if not subfolders_found:
        print("No valid subfolders found in the input directory to process.")
    else:
        print(f"Found subfolders to process: {', '.join(subfolders_found)}")

    for subfolder_name in subfolders_found:
        subfolder_path = os.path.join(INPUT_BASE_DIR, subfolder_name)
        print(f"\nProcessing subfolder: '{subfolder_name}'")
        title = subfolder_name.replace("_", " ").replace("-", " ").title()

        # Original order of operations
        seamless_pattern_file = create_pattern(
            subfolder_path
        )  # Expects jpg input, creates seamless_1.jpg
        create_seamless_zoom_video(
            subfolder_path, seamless_pattern_file
        )  # Needs output from create_pattern
        create_seamless_mockup(
            subfolder_path
        )  # Uses first image found, creates output_mockup.png
        create_main_mockup(subfolder_path, title)  # Uses all images, creates main.png
        create_grid_mockup_with_borders(
            subfolder_path
        )  # Uses all images, creates grid_mockup_with_borders.jpg
        create_large_grid(
            subfolder_path
        )  # Expects jpg input, creates layered_mockup_X.jpg

        print(f"Finished processing for subfolder: '{subfolder_name}'")

    print("\nAll subfolders processed.")
