import os
import glob
from PIL import Image, ImageFont, ImageDraw
import numpy as np


# Set up constants for size and padding
OUTPUT_SIZE = (3000, 2250)
GRID_COLS = 2
GRID_ROWS = 2


def load_images(image_paths):
    """Load all images from given paths."""
    loaded_imgs = []
    for path in image_paths:
        img = Image.open(path).convert("RGBA")
        loaded_imgs.append(img)
    return loaded_imgs


def apply_watermark(image, logo_path="./logo.png", opacity=40, spacing_multiplier=8):
    """Apply logo watermark in a grid pattern with adjustable opacity and spacing."""
    image = image.convert("RGBA")  # Ensure image is RGBA
    watermark = Image.new("RGBA", image.size, (0, 0, 0, 0))  # Create watermark canvas

    # Load and resize the logo
    logo = Image.open(logo_path).convert("RGBA")
    logo_width = image.width // 8
    logo_height = int(logo_width * logo.height / logo.width)
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    # Adjust logo opacity
    logo_array = np.array(logo)
    logo_array[:, :, 3] = (logo_array[:, :, 3] * opacity // 100).astype(np.uint8)
    logo = Image.fromarray(logo_array)

    # Calculate spacing for watermark grid
    spacing_x = logo_width * spacing_multiplier
    spacing_y = logo_height * spacing_multiplier

    # Add watermarks in a grid pattern
    for y in range(0, image.height, spacing_y):
        for x in range(0, image.width, spacing_x):
            watermark.paste(logo, (x, y), logo)

    # Composite the watermark with the original image
    return Image.alpha_composite(image, watermark)


def grid_mockup(input_images, output_folder, title):
    """Create mockups with grid layouts and optional text overlays."""
    main_mockup, _, text_info = create_grid(input_images[:6], title, with_text_overlay=True)
    main_mockup = add_text_background(main_mockup)

    if text_info:
        draw_text(main_mockup, text_info)

    output_main = os.path.join(output_folder, "main.png")
    main_mockup.save(output_main, "PNG")

    mockup_no_text = create_grid(input_images[:4], with_text_overlay=False)[0]
    mockup_no_text_with_watermark = apply_watermark(mockup_no_text)
    output_no_text = os.path.join(output_folder, "mockup_no_text.png")
    mockup_no_text_with_watermark.save(output_no_text, "PNG")

    output_filenames = [output_main, output_no_text]
    for i in range(4, len(input_images), 4):
        mockup = create_grid(input_images[i:i + 4], with_text_overlay=False)[0]
        mockup_with_watermark = apply_watermark(mockup)
        output_filename = os.path.join(output_folder, f"mockup_{i // 4 + 1}.png")
        mockup_with_watermark.save(output_filename, "PNG")
        output_filenames.append(output_filename)

    if input_images:
        trans_demo = create_transparency_demo(input_images[0])
        output_trans_demo = os.path.join(output_folder, "transparency_demo.png")
        trans_demo.save(output_trans_demo, "PNG")
        output_filenames.append(output_trans_demo)

    return output_filenames


def create_grid(input_images, title=None, with_text_overlay=True):
    """Create a grid with optional text overlay."""
    cols = 3 if with_text_overlay else GRID_COLS
    rows = 2 if with_text_overlay else GRID_ROWS
    padding = 50 if with_text_overlay else 10

    total_h_padding = padding * (cols + 1)
    total_v_padding = padding * (rows + 1)
    cell_width = (OUTPUT_SIZE[0] - total_h_padding) // cols
    cell_height = (OUTPUT_SIZE[1] - total_v_padding) // rows
    grid_img = Image.new("RGBA", OUTPUT_SIZE, (225, 213, 213, 255))

    for idx, img in enumerate(input_images[:cols * rows]):
        row, col = divmod(idx, cols)
        x = padding + col * (cell_width + padding)
        y = padding + row * (cell_height + padding)
        aspect = img.width / img.height

        target_width, target_height = cell_width, int(cell_width / aspect)
        if target_height > cell_height:
            target_height = cell_height
            target_width = int(target_height * aspect)

        img = img.resize((target_width, target_height), Image.LANCZOS)
        x_center = x + (cell_width - target_width) // 2
        y_center = y + (cell_height - target_height) // 2
        grid_img.paste(img, (x_center, y_center), img)

    if with_text_overlay and title:
        title_font = ImageFont.truetype("./fonts/Quando.TTF", 100)
        details_font = ImageFont.truetype("./fonts/Quando.TTF", 60)
        return grid_img, None, (title_font, details_font, title)

    return grid_img, None, None


def add_text_background(image, text_block_width=1650, text_area_height=375):
    """Adds a white rectangular background with a border and rounded corners."""
    text_area_y_start = (OUTPUT_SIZE[1] - text_area_height) // 2
    text_area_x_start = (OUTPUT_SIZE[0] - text_block_width) // 2
    overlay = Image.new("RGBA", (text_block_width, text_area_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        [0, 0, text_block_width - 1, text_area_height - 1],
        radius=40,
        fill=(255, 255, 255, 255),
        width=2,
    )
    image.paste(overlay, (text_area_x_start, text_area_y_start), overlay)
    return image


def draw_text(image, text_info):
    """Draw title text on the image."""
    if not text_info:
        return
    title_font, details_font, title = text_info
    draw = ImageDraw.Draw(image)
    text_x = OUTPUT_SIZE[0] // 2
    text_y = OUTPUT_SIZE[1] // 2
    draw.text((text_x, text_y), title, font=title_font, fill=(0, 0, 0, 255), anchor="mm")

def create_transparency_demo(image, text="Transparent PNG for all your design needs"):
    """Creates a mockup showing transparency with an offset checkerboard pattern."""
    canvas_size = (3000, 2250)
    demo = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(demo)

    # Checkerboard pattern
    square_size = 40
    start_x, start_y = 600, 1250
    for y in range(start_y, start_y + 1400, square_size):
        for x in range(start_x, start_x + 1800, square_size):
            if (x + y) // square_size % 2 == 0:
                draw.rectangle([x, y, x + square_size, y + square_size], fill=(200, 200, 200, 255))

    aspect = image.width / image.height
    target_width, target_height = 1500, int(1500 / aspect)
    resized_img = image.resize((target_width, target_height), Image.LANCZOS)
    demo.paste(resized_img, ((canvas_size[0] - target_width) // 2, start_y), resized_img)

    font = ImageFont.truetype("./fonts/Quando.TTF", 110)
    draw.text((300, 200), text, font=font, fill=(0, 0, 0, 255), anchor="lm")
    return demo


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "input")

    print("Deleting all .Identifier files...")
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".Identifier"):
                file_path = os.path.join(root, file)
                os.remove(file_path)

    for subdir, _, files in os.walk(input_folder):
        images = sorted(glob.glob(os.path.join(subdir, "*.png")))
        if not images:
            continue
        title = os.path.basename(subdir)
        input_images = load_images(images)
        output_folder = os.path.join(subdir, "mocks")
        os.makedirs(output_folder, exist_ok=True)

        print(f"Processing folder: {subdir} with title: {title}")
        grid_mockup(input_images, output_folder, title)

    print("Processing complete!")
