import os
import glob
import cv2
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import numpy as np

# Constants
OUTPUT_SIZE = (3000, 2250)
GRID_2x2_SIZE = (2000, 2000)
CELL_PADDING = 10


def load_images(image_paths):
    """Load images from paths."""
    return [Image.open(path).convert("RGBA") for path in image_paths]


def apply_watermark(image, logo_path="logo.png", opacity=45, spacing_multiplier=3):
    """Apply logo watermark in grid pattern."""
    image = image.convert("RGBA")
    watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))

    # Load and resize logo
    logo = Image.open(logo_path).convert("RGBA")
    logo_width = image.width // 12
    logo_height = int(logo_width * logo.height / logo.width)
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    # Set opacity
    logo = logo.copy()
    alpha = logo.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity / 100)
    logo.putalpha(alpha)

    # Create watermark grid
    spacing_x = logo_width * spacing_multiplier
    spacing_y = logo_height * spacing_multiplier

    for y in range(-spacing_y * 2, image.height + spacing_y * 2, spacing_y):
        offset_x = (y // spacing_y % 2) * (spacing_x // 2)
        for x in range(-spacing_x * 2, image.width + spacing_x * 2, spacing_x):
            watermark_layer.paste(logo, (x, y), logo)

    return Image.alpha_composite(image, watermark_layer)


def create_2x2_grid(input_images):
    """Create a 2x2 grid layout."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(GRID_2x2_SIZE, Image.LANCZOS)
    grid_img = canvas_bg.copy()

    if not input_images:
        return grid_img

    cell_width = (GRID_2x2_SIZE[0] // 2) - (CELL_PADDING * 2)
    cell_height = (GRID_2x2_SIZE[1] // 2) - (CELL_PADDING * 2)

    for idx, img_path in enumerate(input_images[:4]):
        row = idx // 2
        col = idx % 2

        x = (col * (cell_width + CELL_PADDING * 2)) + CELL_PADDING
        y = (row * (cell_height + CELL_PADDING * 2)) + CELL_PADDING

        # Load and resize image
        img = Image.open(img_path).convert("RGBA")
        img_aspect = img.width / img.height
        cell_aspect = cell_width / cell_height

        if img_aspect > cell_aspect:
            target_width = cell_width
            target_height = int(cell_width / img_aspect)
            y_offset = (cell_height - target_height) // 2
            x_offset = 0
        else:
            target_height = cell_height
            target_width = int(cell_height * img_aspect)
            x_offset = (cell_width - target_width) // 2
            y_offset = 0

        resized = img.resize((target_width, target_height), Image.LANCZOS)
        grid_img.paste(resized, (x + x_offset, y + y_offset), resized)

    return grid_img


def create_main_grid(images, canvas_size):
    """Create a grid layout based on image orientation."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(canvas_size, Image.LANCZOS)
    canvas = canvas_bg.copy()

    # Only use first 6 images
    images = images[:6]
    if not images:
        return canvas

    # Determine if images are primarily landscape or portrait
    aspect_ratios = [img.width / img.height for img in images]
    avg_aspect = sum(aspect_ratios) / len(aspect_ratios)

    # Set grid dimensions based on average aspect ratio
    if avg_aspect > 1:  # Landscape
        grid_cols = 2
        grid_rows = 3
    else:  # Portrait
        grid_cols = 3
        grid_rows = 2

    cell_width = canvas_size[0] // grid_cols
    cell_height = canvas_size[1] // grid_rows

    # Scale factor to allow slight overlap
    scale_factor = 1.1

    for idx, img in enumerate(images):
        row = idx // grid_cols
        col = idx % grid_cols

        # Center position for this cell
        center_x = col * cell_width + cell_width // 2
        center_y = row * cell_height + cell_height // 2

        # Calculate target dimensions with overlap
        target_width = int(cell_width * scale_factor)
        target_height = int(cell_height * scale_factor)

        # Maintain aspect ratio
        img_aspect = img.width / img.height
        if img_aspect > 1:  # Landscape image
            target_height = int(target_width / img_aspect)
        else:  # Portrait image
            target_width = int(target_height * img_aspect)

        # Resize image
        resized = img.resize((target_width, target_height), Image.LANCZOS)

        # Calculate position (centered in cell)
        x = center_x - target_width // 2
        y = center_y - target_height // 2

        canvas.paste(resized, (x, y), resized)

    return canvas


def add_overlay_and_title(image, title):
    """Add overlay and title text."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    overlay = Image.open(os.path.join(script_dir, "clip_overlay.png")).convert("RGBA")
    overlay = overlay.resize(image.size, Image.LANCZOS)
    image = Image.alpha_composite(image, overlay)

    # Prepare text
    draw = ImageDraw.Draw(image)
    max_width = 1000
    max_height = 550
    font_size = 125

    # Find appropriate font size and line breaks
    while font_size > 0:
        font = ImageFont.truetype("./fonts/Free Version Angelina.ttf", font_size)
        words = title.split()

        # Try single line
        if draw.textlength(title, font=font) <= max_width:
            lines = [title]
            break

        # Try two lines
        mid_point = len(words) // 2
        line1 = " ".join(words[:mid_point])
        line2 = " ".join(words[mid_point:])

        if (
            draw.textlength(line1, font=font) <= max_width
            and draw.textlength(line2, font=font) <= max_width
        ):
            lines = [line1, line2]
            break

        font_size -= 5

    if font_size <= 0:
        return image

    # Draw text
    text = "\n".join(lines)
    center_x = image.width // 2
    center_y = (image.height // 2) - 50
    line_spacing = 60
    y_offset = center_y - (font_size + line_spacing) // 2 * (len(lines) - 1)

    for line in lines:
        draw.text(
            (center_x, y_offset),
            line,
            font=font,
            fill=(0, 0, 0),
            anchor="mm",
            align="center",
        )
        y_offset += font_size + line_spacing

    return image


def create_transparency_demo(
    image_path, text="Transparent PNG for all your design needs"
):
    """Create transparency demo with checkerboard pattern."""
    canvas_size = (3000, 2250)
    demo = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(demo)

    # Draw checkerboard
    square_size = 80
    split_x = canvas_size[0] // 2

    for y in range(0, canvas_size[1], square_size):
        for x in range(0, canvas_size[0], square_size):
            if (x + y) // square_size % 2 == 0:
                fill_color = (
                    (100, 100, 100, 255) if x < split_x else (200, 200, 200, 255)
                )
                draw.rectangle(
                    [x, y, x + square_size, y + square_size], fill=fill_color
                )

    # Load and center image
    image = Image.open(image_path).convert("RGBA")
    aspect = image.width / image.height
    target_width, target_height = 1800, int(1800 / aspect)

    if target_height > canvas_size[1] - 400:
        target_height = canvas_size[1] - 400
        target_width = int(target_height * aspect)

    resized_img = image.resize((target_width, target_height), Image.LANCZOS)
    x_pos = (canvas_size[0] - target_width) // 2
    y_pos = (canvas_size[1] - target_height) // 2 + 100

    demo.paste(resized_img, (x_pos, y_pos), resized_img)

    # Add text and logo
    font = ImageFont.truetype("./fonts/DSMarkerFelt.ttf", 120)
    text_width = font.getlength(text)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo = Image.open(os.path.join(script_dir, "logo.png")).convert("RGBA")
    logo_height = 300
    logo_width = int(logo_height * logo.width / logo.height)
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    # Create text background
    text_bg = Image.new("RGBA", (int(text_width + 100), 190), (255, 255, 255, 255))
    text_bg_x = (canvas_size[0] - text_bg.width) // 2
    logo_x = text_bg_x - logo_width - 40

    demo.paste(text_bg, (text_bg_x, 80), text_bg)
    demo.paste(logo, (logo_x, 65), logo)

    draw.text(
        (text_bg_x + text_width // 2 + 50, 150),
        text,
        font=font,
        fill=(0, 0, 0, 255),
        anchor="mm",
    )

    return demo


def create_video_mockup(
    images, output_path, num_transition_frames=30, display_frames=60
):
    """Create video with transitions between images."""
    if not images:
        return

    TARGET_SIZE = (2000, 2000)

    # Resize and center images
    cv2_images = []
    for img in images:
        img_cv = cv2.imread(img)
        h, w = img_cv.shape[:2]
        aspect = w / h

        if aspect > 1:
            new_w = TARGET_SIZE[0]
            new_h = int(TARGET_SIZE[0] / aspect)
            pad_y = (TARGET_SIZE[1] - new_h) // 2
            pad_x = 0
        else:
            new_h = TARGET_SIZE[1]
            new_w = int(TARGET_SIZE[1] * aspect)
            pad_x = (TARGET_SIZE[0] - new_w) // 2
            pad_y = 0

        resized = cv2.resize(img_cv, (new_w, new_h))
        padded = cv2.copyMakeBorder(
            resized,
            pad_y,
            pad_y,
            pad_x,
            pad_x,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )
        cv2_images.append(padded)

    # Create video
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, 30, TARGET_SIZE)

    for i in range(len(cv2_images)):
        # Display current frame
        for _ in range(display_frames):
            out.write(cv2_images[i])

        # Transition to next frame
        if i < len(cv2_images) - 1:
            for j in range(num_transition_frames):
                alpha = j / num_transition_frames
                blended = cv2.addWeighted(
                    cv2_images[i], 1 - alpha, cv2_images[(i + 1)], alpha, 0
                )
                out.write(blended)

    # Display last frame
    for _ in range(display_frames):
        out.write(cv2_images[-1])

    out.release()


def grid_mockup(input_folder, title):
    """Main function to create mockups."""
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    # Load images
    input_images = sorted(glob.glob(os.path.join(input_folder, "*png")))
    loaded_images = load_images(input_images[:6])  # Only use 6 images for main mockup

    # Create main mockup with grid layout
    main_mockup = create_main_grid(loaded_images, OUTPUT_SIZE)

    # Add overlay and title
    if title:
        main_mockup = add_overlay_and_title(main_mockup, title)

    # Save main mockup
    output_main = os.path.join(output_folder, "main.png")
    main_mockup.save(output_main, "PNG")

    # Create 2x2 grid mockups
    mockup_no_text = create_2x2_grid(input_images[:4])
    mockup_no_text_with_watermark = apply_watermark(mockup_no_text)
    output_no_text = os.path.join(output_folder, "mockup_no_text.png")
    mockup_no_text_with_watermark.save(output_no_text, "PNG")

    output_filenames = [output_main, output_no_text]
    video_filenames = [output_no_text]

    # Create additional 2x2 grids
    for i in range(4, len(input_images), 4):
        mockup = create_2x2_grid(input_images[i : i + 4])
        mockup_with_watermark = apply_watermark(mockup)
        output_filename = os.path.join(output_folder, f"mockup_{i//4+1}.png")
        mockup_with_watermark.save(output_filename, "PNG")
        output_filenames.append(output_filename)
        video_filenames.append(output_filename)

    # Create transparency demo
    if input_images:
        trans_demo = create_transparency_demo(input_images[0])
        output_trans_demo = os.path.join(output_folder, "transparency_demo.png")
        trans_demo.save(output_trans_demo, "PNG")
        output_filenames.append(output_trans_demo)
        video_filenames.append(output_trans_demo)

    # Create video
    if len(video_filenames) > 1:
        video_path = os.path.join(output_folder, "mockup_video.mp4")
        create_video_mockup(video_filenames, video_path)
        output_filenames.append(video_path)

    return output_filenames


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "input")

    # Delete .Identifier files
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".Identifier"):
                os.remove(os.path.join(root, file))

    # Process each subfolder
    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder
            print(f"Processing: {subfolder_path} with title: {title}")
            grid_mockup(subfolder_path, title)

    print("Processing complete!")
