import os
import cv2
import numpy as np
import math
import glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


def create_main_mockup(input_folder, title):
    global INPUT_FOLDER, OUTPUT_FOLDER

    INPUT_FOLDER = input_folder
    output_folder = os.path.join(input_folder, "mocks")
    OUTPUT_FOLDER = output_folder

    GRID_ROWS, GRID_COLS = 2, 6
    print(f"  Creating main mockup for '{title}'...")

    images = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*.[jp][pn][g]")))

    grid_width = 3000
    grid_height = 2250

    background_color = (222, 215, 211, 255)
    grid_canvas = Image.new("RGBA", (grid_width, grid_height), background_color)

    cell_width = grid_width // GRID_COLS
    cell_height = grid_height // GRID_ROWS

    # Spacing between images
    total_spacing = grid_width - (cell_width * GRID_COLS)
    spacing_between = total_spacing / (GRID_COLS + 1)

    # Load and prepare shadow with proper aspect ratio
    script_dir = os.path.dirname(os.path.abspath(__file__))
    shadow_path = os.path.join(script_dir, "shadow.png")
    shadow = Image.open(shadow_path).convert("RGBA")

    # Calculate scale factor based on height while maintaining aspect ratio
    scale_factor = cell_height / shadow.height
    shadow_new_width = int(shadow.width * scale_factor)
    shadow = shadow.resize((shadow_new_width, cell_height), Image.LANCZOS)

    # First pass: Draw all images
    image_positions = []  # Store positions for shadow placement
    for i, img_path in enumerate(images[: GRID_ROWS * GRID_COLS]):
        img = Image.open(img_path).convert("RGBA")
        img = img.resize(
            (int(img.width * cell_height / img.height), cell_height), Image.LANCZOS
        )

        row_index = i // GRID_COLS
        col_index = i % GRID_COLS

        x_pos = int((col_index + 1) * spacing_between + col_index * cell_width)
        y_pos = int(row_index * cell_height)

        image_positions.append((x_pos, y_pos))
        grid_canvas.paste(img, (x_pos, y_pos), img)

    # Second pass: Add shadows on top of all images
    for x_pos, y_pos in image_positions:
        shadow_x = x_pos - shadow_new_width + 5
        grid_canvas.paste(shadow, (shadow_x, y_pos), shadow)

    # Add overlay image and create final composition
    overlay_path = os.path.join(script_dir, "overlay.png")
    overlay = Image.open(overlay_path).convert("RGBA")
    overlay = overlay.resize((grid_width, grid_height), Image.LANCZOS)
    final_image = Image.alpha_composite(grid_canvas, overlay)

    # Add centered title text with dynamic font sizing
    draw = ImageDraw.Draw(final_image)
    initial_font_size = 200  # Start with larger size
    max_width = 1380  # Maximum allowed width

    # Function to get font and text size
    def get_font_and_size(size):
        font = ImageFont.truetype("./fonts/Clattering.ttf", size)
        bbox = draw.textbbox((0, 0), title, font=font)
        return font, bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Find appropriate font size
    font_size = initial_font_size
    font, text_width, text_height = get_font_and_size(font_size)
    while text_width > max_width and font_size > 50:  # Don't go smaller than 50
        font_size -= 5
        font, text_width, text_height = get_font_and_size(font_size)

    # Calculate center position with vertical offset
    text_x = (grid_width - text_width) // 2
    vertical_offset = 0
    text_y = (grid_height - text_height) // 2 - vertical_offset

    # Draw the text
    draw.text((text_x, text_y), title, font=font, fill=(238, 186, 43), anchor="lt")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    grid_filename = "main.png"
    final_image.save(os.path.join(OUTPUT_FOLDER, grid_filename), "PNG")


def create_large_grid(input_folder):
    # Get list of input images (any size now)
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # ------------------- Canvas Settings -------------------
    CANVAS_WIDTH = 2800
    CANVAS_HEIGHT = 2250

    print("Creating layered composite outputs...")

    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    num_images = len(images)
    if num_images < 3:
        raise ValueError(f"At least 3 images required, but only {num_images} found.")

    # ------------------- Image Settings -------------------
    center_target_size = (2400, 2400)  # Example: 2/3 of the canvas
    bottom_left_target_size = (1800, 1800)  # Example: 1/2 of the canvas

    # Define rotation angles and offsets
    center_rotation = -25  # Angle for the centered image
    bottom_left_rotation = -15  # Angle for the bottom-left image

    # Shadow settings
    shadow_offset = 25
    shadow_blur = 15
    shadow_opacity = 120

    # ------------------- Generate Composite Outputs -------------------
    for set_index in range(min(4, num_images // 3)):  # Loop to create up to 4 mockups
        # ------------------- Background Image (Full Backdrop) -------------------
        backdrop_img_index = set_index * 3  # Index of the backdrop image for this set
        if backdrop_img_index >= num_images:
            break  # Stop if we run out of images

        # Create a blank canvas of the desired size
        canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")

        backdrop_img = Image.open(images[backdrop_img_index]).convert("RGB")
        # Resize the backdrop to fit the canvas, preserving aspect ratio
        backdrop_img = ImageOps.fit(
            backdrop_img, (CANVAS_WIDTH, CANVAS_HEIGHT), method=Image.LANCZOS
        )

        # Calculate the offset to center the backdrop on the canvas
        backdrop_offset_x = (CANVAS_WIDTH - backdrop_img.width) // 2
        backdrop_offset_y = (CANVAS_HEIGHT - backdrop_img.height) // 2

        canvas.paste(backdrop_img, (backdrop_offset_x, backdrop_offset_y))

        # --- Center Image ---
        center_img_index = set_index * 3 + 1  # Index of the center image
        if center_img_index < num_images:  # Only process if image exists
            center_img = Image.open(images[center_img_index]).convert("RGBA")
            center_img = ImageOps.fit(
                center_img, center_target_size, method=Image.LANCZOS
            )
            center_img = center_img.rotate(
                center_rotation, expand=True, resample=Image.BICUBIC
            )

            # Offsets are now *relative* to the canvas size.  More precise control.
            center_offset_x = (
                CANVAS_WIDTH - center_target_size[0]
            ) // 2 - 800  # Center horizontally
            center_offset_y = (
                CANVAS_HEIGHT - center_target_size[1]
            ) // 2 + 100  # Center vertically (shifted)

            # Adjust center offset for rotation
            center_offset_x -= (center_img.width - center_target_size[0]) // 2
            center_offset_y -= (center_img.height - center_target_size[1]) // 2

            # Create and paste center shadow (top and right)
            center_shadow = Image.new("RGBA", center_img.size, (0, 0, 0, 0))
            center_alpha = center_img.split()[3]
            center_shadow.paste((0, 0, 0, shadow_opacity), mask=center_alpha)
            center_shadow = center_shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
            canvas.paste(
                center_shadow,
                (center_offset_x + shadow_offset, center_offset_y + shadow_offset),
                center_shadow,
            )
            # Create and paste center shadow (top and left)
            canvas.paste(
                center_shadow,
                (center_offset_x - shadow_offset, center_offset_y - shadow_offset),
                center_shadow,
            )
            canvas.paste(center_img, (center_offset_x, center_offset_y), center_img)

        # --- Bottom-Left Image ---
        bottom_left_img_index = set_index * 3 + 2  # Index of the bottom-left image
        if bottom_left_img_index < num_images:  # Only process if image exists
            bottom_left_img = Image.open(images[bottom_left_img_index]).convert("RGBA")
            bottom_left_img = ImageOps.fit(
                bottom_left_img, bottom_left_target_size, method=Image.LANCZOS
            )
            bottom_left_img = bottom_left_img.rotate(
                bottom_left_rotation, expand=True, resample=Image.BICUBIC
            )

            bottom_left_offset_x = -400  # Shifted slightly *outside* the left edge
            bottom_left_offset_y = (
                CANVAS_HEIGHT - bottom_left_target_size[1] + 300
            )  # Shifted *up* from the bottom

            # Adjust bottom-left offset for rotation
            bottom_left_offset_x -= (
                bottom_left_img.width - bottom_left_target_size[0]
            ) // 2
            bottom_left_offset_y -= (
                bottom_left_img.height - bottom_left_target_size[1]
            ) // 2

            # Create and paste bottom-left shadow (bottom and right)
            bottom_left_shadow = Image.new("RGBA", bottom_left_img.size, (0, 0, 0, 0))
            bottom_left_alpha = bottom_left_img.split()[3]
            bottom_left_shadow.paste((0, 0, 0, shadow_opacity), mask=bottom_left_alpha)
            bottom_left_shadow = bottom_left_shadow.filter(
                ImageFilter.GaussianBlur(shadow_blur)
            )
            canvas.paste(
                bottom_left_shadow,
                (
                    bottom_left_offset_x + shadow_offset,
                    bottom_left_offset_y + shadow_offset,
                ),
                bottom_left_shadow,
            )

            # Create and paste bottom-left shadow (top and left)

            canvas.paste(
                bottom_left_shadow,
                (
                    bottom_left_offset_x - shadow_offset,
                    bottom_left_offset_y - shadow_offset,
                ),
                bottom_left_shadow,
            )
            canvas.paste(
                bottom_left_img,
                (bottom_left_offset_x, bottom_left_offset_y),
                bottom_left_img,
            )

        # --- Save the Result ---
        output_filename = f"layered_mockup_{set_index + 1}.jpg"  # Numbered output files
        canvas.save(
            os.path.join(output_folder, output_filename),
            "JPEG",
            quality=95,
            optimize=True,
        )


def create_pattern(input_folder):
    IMAGE_SIZE = 2048
    GRID_SIZE = 2

    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))[
        :1
    ]  # Only take first image
    output_folder = os.path.join(input_folder, "mocks")

    print("   Creating seamless mockup...")

    for index, image_path in enumerate(images):
        output_image = Image.new("RGBA", (IMAGE_SIZE, IMAGE_SIZE))
        source_image = Image.open(image_path).convert("RGBA")

        # Resize source image to half the canvas size since we'll use it in 2x2 grid
        cell_size = IMAGE_SIZE // GRID_SIZE
        source_image = source_image.resize((cell_size, cell_size), Image.LANCZOS)

        # Create 2x2 grid using the same image for seamless pattern
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                output_image.paste(source_image, (col * cell_size, row * cell_size))

        # Create text layer for white border
        txt = Image.new("RGBA", output_image.size, (255, 255, 255, 0))
        font = ImageFont.truetype("./fonts/Clattering.ttf", 185)

        text = "Seamless Patterns"
        text_position = (IMAGE_SIZE // 2, IMAGE_SIZE // 2)

        txtLayer = ImageDraw.Draw(txt)
        # Draw white border by rendering text multiple times with offset
        offsets = [(x, y) for x in (-3, 3) for y in (-3, 3)]
        for offset_x, offset_y in offsets:
            txtLayer.text(
                (text_position[0] + offset_x, text_position[1] + offset_y),
                text,
                font=font,
                fill=(255, 255, 255, 192),
                anchor="mm",
                align="center",
            )
        # Draw main black text on top
        txtLayer.text(
            text_position,
            text,
            font=font,
            fill=(0, 0, 0, 192),
            anchor="mm",
            align="center",
        )

        combined = Image.alpha_composite(output_image, txt)

        # Save with optimized JPEG settings
        os.makedirs(output_folder, exist_ok=True)
        filename = f"seamless_{index + 1}.jpg"
        combined.convert("RGB").save(
            os.path.join(output_folder, filename),
            "JPEG",
            quality=85,
            optimize=True,
            subsampling="4:2:0",
        )


def create_seamless_zoom_video(input_folder):
    import cv2  # ensure cv2 is imported

    output_folder = os.path.join(input_folder, "mocks")
    img_path = os.path.join(output_folder, "seamless_1.jpg")
    if not os.path.exists(img_path):
        print("seamless_1.jpg not found, skipping zoom video creation")
        return
    img = cv2.imread(img_path)
    height, width = img.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_path = os.path.join(output_folder, "video_seamless.mp4")
    video = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

    total_frames = 90
    initial_zoom = 1.5  # start zoomed in (crop factor)
    for i in range(total_frames):
        t = i / (total_frames - 1)
        zoom_factor = (
            initial_zoom - (initial_zoom - 1) * t
        )  # interpolate zoom factor to 1.0
        new_w = int(width / zoom_factor)
        new_h = int(height / zoom_factor)
        x1 = (width - new_w) // 2
        y1 = (height - new_h) // 2
        crop = img[y1 : y1 + new_h, x1 : x1 + new_w]
        frame = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)
        video.write(frame)
    video.release()


def create_grid_mockup_with_borders(
    input_folder, output_folder=None, border_width=15, watermark_text="© digital veil"
):
    """
    Creates a grid mockup of all images in the input folder with white borders and a watermark.

    Args:
        input_folder: Folder containing the input images
        output_folder: Folder to save the output (defaults to input_folder/mocks)
        border_width: Width of the white borders between images
        watermark_text: Text to use as watermark
    """
    import os
    import glob
    import math
    from PIL import Image, ImageDraw, ImageFont

    # Set up output folder
    if output_folder is None:
        output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    # Get all images
    images = sorted(glob.glob(os.path.join(input_folder, "*.[jp][pn][g]")))
    if len(images) == 0:
        print(f"No images found in {input_folder}")
        return

    # Limit to 12 images
    images = images[:12]

    # Determine grid configuration (4x3 grid)
    grid_rows, grid_cols = 3, 4

    # Calculate sizes
    img_samples = [Image.open(img) for img in images[:3]]
    avg_aspect = sum(img.width / img.height for img in img_samples) / len(img_samples)

    grid_width = 3000  # Base width
    cell_width = (grid_width - (grid_cols + 1) * border_width) // grid_cols
    cell_height = int(cell_width / avg_aspect)
    grid_height = (cell_height * grid_rows) + ((grid_rows + 1) * border_width)

    # Create white canvas
    grid_canvas = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))

    # Place images
    for i, img_path in enumerate(images):
        if i >= grid_rows * grid_cols:
            break

        img = Image.open(img_path).convert("RGB")
        img = img.resize((cell_width, cell_height), Image.LANCZOS)

        row_index = i // grid_cols
        col_index = i % grid_cols

        x_pos = border_width + col_index * (cell_width + border_width)
        y_pos = border_width + row_index * (cell_height + border_width)

        grid_canvas.paste(img, (x_pos, y_pos))

    # Add staggered watermarks
    draw = ImageDraw.Draw(grid_canvas)

    # Try to use a standard font that should be available
    try:
        font = ImageFont.truetype("Arial.ttf", 80)
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 80)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default().font_variant(size=80)

    # Create a transparent layer for watermarks
    txt = Image.new("RGBA", grid_canvas.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(txt)

    # Get watermark dimensions
    watermark_width, watermark_height = draw.textbbox(
        (0, 0), watermark_text, font=font
    )[2:4]

    # Calculate spacing for staggered pattern
    num_watermarks_x = 5
    num_watermarks_y = 7

    # Create staggered pattern of watermarks
    for i in range(num_watermarks_y):
        for j in range(num_watermarks_x):
            # Stagger every other row
            offset = (watermark_width / 2) if i % 2 else 0

            # Calculate positions
            x = (
                (j * grid_width // (num_watermarks_x - 1))
                - watermark_width // 2
                + offset
            )
            y = (i * grid_height // (num_watermarks_y - 1)) - watermark_height // 2

            # Draw watermark with shadow for better visibility
            d.text(
                (x + 2, y + 2), watermark_text, fill=(0, 0, 0, 30), font=font
            )  # Shadow
            d.text(
                (x, y), watermark_text, fill=(255, 255, 255, 60), font=font
            )  # Main text

    # Rotate the text layer for diagonal effect
    angle = -30
    txt = txt.rotate(angle, resample=Image.BICUBIC, expand=False)

    # Composite the watermark with the grid
    grid_canvas = Image.alpha_composite(grid_canvas.convert("RGBA"), txt).convert("RGB")

    # Save the result
    output_path = os.path.join(output_folder, "grid_mockup_with_borders.jpg")
    grid_canvas.save(output_path, "JPEG", quality=95)
    print(f"Grid mockup created: {output_path}")
    return output_path


def create_seamless_mockup(input_folder):
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    # Get the first image in the input folder
    input_files = [
        f
        for f in os.listdir(input_folder)
        if f.lower().endswith(("png", "jpg", "jpeg"))
    ]
    if not input_files:
        print("No image files found in input folder.")
        return

    input_image_path = os.path.join(input_folder, input_files[0])
    input_img = Image.open(input_image_path)

    # Define the maximum size for the tile so it fits within the canvas margins
    cell_max_size = (550, 550)
    scaled_img = input_img.copy()
    # Use Lanczos filtering for a high-quality downscaling
    scaled_img.thumbnail(cell_max_size, Image.LANCZOS)
    cell_width, cell_height = scaled_img.size

    # Load the canvas background from canvas.png in the script directory and resize it to 2000x2000
    canvas_path = os.path.join(os.path.dirname(__file__), "canvas2.png")
    canvas = Image.open(canvas_path)
    canvas = canvas.resize((2000, 2000))
    canvas_width, canvas_height = canvas.size

    # Define margins and gap
    margin = 100
    arrow_gap = 100

    # Position the single input image on the left (spaced from the edge)
    left_x = margin
    left_y = (canvas_height - cell_height) // 2
    canvas.paste(scaled_img, (left_x, left_y))

    # Position the 2x2 grid on the right (also spaced from the edges)
    grid_x = left_x + cell_width + arrow_gap
    grid_y = (canvas_height - (2 * cell_height)) // 2

    for i in range(2):  # rows
        for j in range(2):  # columns
            pos = (grid_x + j * cell_width, grid_y + i * cell_height)
            canvas.paste(scaled_img, pos)

    # Save the output image
    output_image_path = os.path.join(output_folder, "output_mockup.png")
    canvas.save(output_image_path)
    print(f"Mockup saved to {output_image_path}")


if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_directory, "input")

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder
            # First, create seamless patterns (needed for zoom video)
            create_pattern(subfolder_path)

            create_seamless_zoom_video(subfolder_path)
            create_seamless_mockup(subfolder_path)

            # Continue processing other mockups
            create_main_mockup(subfolder_path, title)
            create_grid_mockup_with_borders(subfolder_path)
            create_large_grid(subfolder_path)
