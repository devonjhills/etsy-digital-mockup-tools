import os
import glob
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import numpy as np
from moviepy.editor import ImageSequenceClip


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


def apply_watermark(image, logo_path="logo.png", opacity=45, spacing_multiplier=3):
    """Apply a logo watermark in a grid pattern with adjustable opacity and spacing."""
    image = image.convert("RGBA")
    watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))

    # Load and resize the logo
    logo = Image.open(logo_path).convert("RGBA")
    logo_width = image.width // 12  # Even smaller logo for more repeats
    logo_height = int(logo_width * logo.height / logo.width)
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    
    # Adjust opacity
    logo = logo.copy()
    alpha = logo.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity / 100)
    logo.putalpha(alpha)

    # Tighter spacing for denser watermark grid
    spacing_x = logo_width * spacing_multiplier
    spacing_y = logo_height * spacing_multiplier

    # Add watermarks in a denser grid pattern with double-offset
    for y in range(-spacing_y * 2, image.height + spacing_y * 2, spacing_y):
        offset_x = (y // spacing_y % 2) * (spacing_x // 2)
        for x in range(-spacing_x * 2, image.width + spacing_x * 2, spacing_x):
            watermark_layer.paste(logo, (x, y), logo)

    return Image.alpha_composite(image, watermark_layer)


def grid_mockup(input_images, output_folder, title):
    """Create mockups with grid layouts and optional text overlays."""
    main_mockup, _, text_info = create_grid(
        input_images[:6], title, with_text_overlay=True
    )
    main_mockup, text_area_y_start, text_area_height = add_text_background(main_mockup)

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
        mockup = create_grid(input_images[i : i + 4], with_text_overlay=False)[0]
        mockup_with_watermark = apply_watermark(mockup)
        output_filename = os.path.join(output_folder, f"mockup_{i // 4 + 1}.png")
        mockup_with_watermark.save(output_filename, "PNG")
        output_filenames.append(output_filename)

    if input_images:
        trans_demo = create_transparency_demo(input_images[0])
        output_trans_demo = os.path.join(output_folder, "transparency_demo.png")
        trans_demo.save(output_trans_demo, "PNG")
        output_filenames.append(output_trans_demo)

    # Add video mockup
    if len(output_filenames) > 1:  # Only create video if we have multiple mockups
        video_path = os.path.join(output_folder, "mockup_video.mp4")
        create_video_mockup(output_filenames, video_path)
        output_filenames.append(video_path)

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
    grid_img = Image.new("RGBA", OUTPUT_SIZE, (255, 255, 255, 255))  # Changed to white

    for idx, img in enumerate(input_images[: cols * rows]):
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
        title_font = ImageFont.truetype("./fonts/Clattering.ttf", 150)  # Larger title
        details_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 80
        )
        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 65
        )
        return grid_img, None, (title_font, details_font, subtitle_font, title)

    return grid_img, None, None


def add_text_background(image, text_block_width=1550, text_area_height=500):
    """Adds a colored rectangular background with exact dimensions."""
    text_area_y_start = (OUTPUT_SIZE[1] - text_area_height) // 2
    text_area_x_start = (OUTPUT_SIZE[0] - text_block_width) // 2
    overlay = Image.new("RGBA", (text_block_width, text_area_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        [0, 0, text_block_width - 1, text_area_height - 1],
        radius=40,
        fill=(225, 213, 213, 255),  # Changed to pink/beige
        width=2,
    )
    image.paste(overlay, (text_area_x_start, text_area_y_start), overlay)
    return image, text_area_y_start, text_area_height


def draw_text(image, text_info):
    """Draw title and additional text on the image."""
    if not text_info:
        return
    title_font, details_font, subtitle_font, title = text_info
    draw = ImageDraw.Draw(image)
    
    # Get text background area
    _, text_top, text_height = add_text_background(image)  # Get actual dimensions
    text_bottom = text_top + text_height
    center_x = OUTPUT_SIZE[0] // 2
    center_y = text_top + (text_height // 2)

    # Draw texts at specific positions
    draw.text(
        (center_x, text_top + 60),
        "12 Clipart Graphics",
        font=subtitle_font,
        fill=(0, 0, 0, 255),
        anchor="mm",
    )
    draw.text(
        (center_x, center_y),
        title,
        font=title_font,
        fill=(0, 0, 0, 255),
        anchor="mm",
    )
    draw.text(
        (center_x, text_bottom - 70),
        "Transparent PNG  |  300 DPI",
        font=subtitle_font,
        fill=(0, 0, 0, 255),
        anchor="mm",
    )


def create_transparency_demo(image, text="Transparent PNG for all your design needs"):
    """Creates a mockup showing transparency with split dark/light checkerboard pattern."""
    canvas_size = (3000, 2250)
    demo = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(demo)

    # Split checkerboard pattern
    square_size = 40
    split_x = canvas_size[0] // 2
    
    # Draw checkerboard patterns
    for y in range(0, canvas_size[1], square_size):
        for x in range(0, canvas_size[0], square_size):
            if (x + y) // square_size % 2 == 0:
                # Darker squares on left side
                if x < split_x:
                    fill_color = (100, 100, 100, 255)
                # Lighter squares on right side
                else:
                    fill_color = (200, 200, 200, 255)
                draw.rectangle(
                    [x, y, x + square_size, y + square_size],
                    fill=fill_color
                )

    # Center the image vertically and horizontally
    aspect = image.width / image.height
    target_width, target_height = 1800, int(1800 / aspect)  # Made image larger
    if target_height > canvas_size[1] - 400:  # Ensure it fits with padding
        target_height = canvas_size[1] - 400
        target_width = int(target_height * aspect)

    resized_img = image.resize((target_width, target_height), Image.LANCZOS)

    # Calculate center position
    x_pos = (canvas_size[0] - target_width) // 2
    y_pos = (
        canvas_size[1] - target_height
    ) // 2 + 100  # Slight offset to account for text

    demo.paste(resized_img, (x_pos, y_pos), resized_img)

    # Create text background with more opacity
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 120)
    text_width = font.getlength(text)
    text_height = 150
    
    # Fully opaque white background for text
    text_bg = Image.new("RGBA", (int(text_width + 100), text_height + 40), (255, 255, 255, 255))
    demo.paste(text_bg, ((canvas_size[0] - text_bg.width) // 2, 80), text_bg)
    
    # Draw text
    draw.text(
        (canvas_size[0] // 2, 150),
        text,
        font=font,
        fill=(0, 0, 0, 255),
        anchor="mm"
    )

    return demo


def create_video_mockup(image_files, output_path, size=(1200, 1200)):
    """Creates a video transitioning through mockup images."""
    frames = []
    
    for img_path in image_files:
        if "main.png" in img_path:  # Skip main mockup
            continue
            
        # Open and resize image to square format
        with Image.open(img_path) as img:
            # Convert to RGB (required for video)
            img = img.convert('RGB')
            
            # Calculate sizing to maintain aspect ratio within square
            aspect = img.width / img.height
            if aspect > 1:
                new_width = size[0]
                new_height = int(size[0] / aspect)
            else:
                new_height = size[1]
                new_width = int(size[1] * aspect)
                
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Create white background
            bg = Image.new('RGB', size, (255, 255, 255))
            
            # Paste image in center
            x = (size[0] - new_width) // 2
            y = (size[1] - new_height) // 2
            bg.paste(img, (x, y))
            
            # Convert to numpy array for moviepy
            frames.append(np.array(bg))

    # Create video with 2-second transitions
    clip = ImageSequenceClip(frames, fps=1/2)  # 2 seconds per frame
    clip.write_videofile(output_path, fps=30)


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
