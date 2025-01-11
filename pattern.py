import os
import cv2
import numpy as np
import glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_main_mockup(input_folder, title):
    global INPUT_FOLDER, OUTPUT_FOLDER

    INPUT_FOLDER = input_folder
    output_folder = os.path.join(input_folder, "mocks")
    OUTPUT_FOLDER = output_folder

    GRID_ROWS, GRID_COLS = 2, 6
    TEXT_PADDING = 30  # Padding around text in center rectangle

    print(f"  Creating main mockup for '{title}'...")

    images = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*.[jp][pn][g]")))

    grid_width = 3000
    grid_height = 2250

    background_color = (222, 215, 211, 255)

    grid_canvas = Image.new("RGBA", (grid_width, grid_height), background_color)

    cell_width = grid_width // GRID_COLS
    cell_height = grid_height // GRID_ROWS

    text_color = (44, 46, 58)
    border_color = (0, 0, 0, 255)  # Fully opaque black
    border_width = 1  # Thinner border width

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
        img = img.resize((int(img.width * cell_height / img.height), cell_height), Image.LANCZOS)

        row_index = i // GRID_COLS
        col_index = i % GRID_COLS

        x_pos = int((col_index + 1) * spacing_between + col_index * cell_width)
        y_pos = int(row_index * cell_height)

        # Add left border to image (now thin and opaque)
        img_with_border = Image.new("RGBA", (img.width + 2, img.height), border_color)
        img_with_border.paste(img, (2, 0), img)
        
        # Store position for shadow placement
        image_positions.append((x_pos, y_pos))
        
        # Paste the actual image
        grid_canvas.paste(img_with_border, (x_pos, y_pos), img_with_border)

    # Second pass: Add shadows on top of all images
    for x_pos, y_pos in image_positions:
        shadow_x = x_pos - shadow_new_width + 5  # Changed from 20 to 5 to move shadow more to the left
        grid_canvas.paste(shadow, (shadow_x, y_pos), shadow)

    draw = ImageDraw.Draw(grid_canvas)
    title_font = ImageFont.truetype("./fonts/Clattering.ttf", 195)
    info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 80)

    pattern_text = "12 Seamless Patterns"
    title_text = f"{title}"
    info_text = "12x12 in.  |  300 DPI  |  JPG"

    # Get text bounding box for layout calculations
    text_bbox_pattern = draw.textbbox((0, 0), pattern_text, font=info_font)
    text_bbox_title = draw.textbbox((0, 0), title_text, font=title_font)
    text_bbox_info = draw.textbbox((0, 0), info_text, font=info_font)

    # Calculate total height and positions
    total_height = (text_bbox_pattern[3] - text_bbox_pattern[1] +
                   text_bbox_title[3] - text_bbox_title[1] +
                   text_bbox_info[3] - text_bbox_info[1])
    
    text_width = max(text_bbox_pattern[2] - text_bbox_pattern[0],
                    text_bbox_title[2] - text_bbox_title[0],
                    text_bbox_info[2] - text_bbox_info[0])

    center_width = text_width + TEXT_PADDING * 1.5
    center_height = total_height + TEXT_PADDING * 1.1 + 100  # Added extra spacing between lines
    side_rect_height = center_height * 0.25

    center_x_start = (grid_width - center_width) // 2
    center_x_end = center_x_start + center_width

    draw.rectangle(
        [(0, grid_height // 2 - side_rect_height // 2),
         (center_x_start, grid_height // 2 + side_rect_height // 2)],
        fill=background_color,
        outline=border_color,
        width=border_width,
    )

    radius = 40

    # Define custom width for the center rectangle
    center_width = 1500  # Adjust this value to change the width
    center_x_start = (grid_width - center_width) // 2
    center_x_end = center_x_start + center_width

    draw.rounded_rectangle(
        [(center_x_start, grid_height // 2 - center_height // 2),
         (center_x_end, grid_height // 2 + center_height // 2)],
        radius=radius,
        fill=background_color,
        outline=border_color,
        width=border_width,
    )

    draw.rectangle(
        [(center_x_end, grid_height // 2 - side_rect_height // 2),
         (grid_width, grid_height // 2 + side_rect_height // 2)],
        fill=background_color,
        outline=border_color,
        width=border_width,
    )

    # Calculate positions for text elements
    text_y_start = grid_height / 2 - center_height / 2
    text_y_end = grid_height / 2 + center_height / 2
    
    # Position pattern text near top of rectangle
    pattern_y = text_y_start + TEXT_PADDING/2
    
    # Position title text slightly above center
    title_offset = 40  # Pixels to move up from center
    title_y = grid_height / 2 - title_offset
    
    info_y = text_y_end - TEXT_PADDING/2

    # Draw each text element separately
    draw.text((grid_width / 2, pattern_y), pattern_text,
              anchor="mt", fill=text_color, font=info_font)
    draw.text((grid_width / 2, title_y), title_text,
              anchor="mm", fill=text_color, font=title_font)
    draw.text((grid_width / 2, info_y), info_text,
              anchor="mb", fill=text_color, font=info_font)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    grid_filename = "main.png"
    grid_canvas.save(os.path.join(OUTPUT_FOLDER, grid_filename), "PNG")

def create_large_grid(input_folder):
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))

    GRID_ROWS = 2
    GRID_COLS = 2
    GRID_SIZE = 2025

    print("   Creating large grids...")

    output_folder = os.path.join(input_folder, "mocks")

    num_images = len(images)
    if num_images < GRID_ROWS * GRID_COLS * 3:
        raise ValueError(f"At least {GRID_ROWS * GRID_COLS * 3} images required, but only {num_images} found.")

    for grid_set in range(num_images // (GRID_ROWS * GRID_COLS)):
        grid_width = GRID_SIZE
        grid_height = GRID_SIZE
        grid_canvas = Image.new("RGBA", (grid_width, grid_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(grid_canvas)

        for i in range(GRID_ROWS * GRID_COLS):
            img_path = images.pop(0)
            img = Image.open(img_path).convert("RGBA")

            col_index = i % GRID_COLS
            row_index = i // GRID_COLS

            square_width = grid_width // GRID_COLS
            square_height = grid_height // GRID_ROWS

            x_pos = col_index * square_width
            y_pos = row_index * square_height

            img.thumbnail((square_width, square_height), Image.LANCZOS)
            img_x = x_pos + (square_width - img.width) // 2
            img_y = y_pos + (square_height - img.height) // 2

            grid_canvas.paste(img, (img_x, img_y), img)

        border_thickness = 5
        for j in range(1, GRID_COLS):
            border_x = j * square_width
            draw.line([(border_x, 0), (border_x, grid_height)], fill="black", width=border_thickness)

        for k in range(1, GRID_ROWS):
            border_y = k * square_height
            draw.line([(0, border_y), (grid_width, border_y)], fill="black", width=border_thickness)

        txt = Image.new("RGBA", grid_canvas.size, (255, 255, 255, 0))
        font = ImageFont.truetype("./fonts/Clattering.ttf", 260)

        text = "Digital Veil"
        text_position = (grid_width // 2, grid_height // 2)

        txtLayer = ImageDraw.Draw(txt)
        txtLayer.text(
            text_position,
            text,
            font=font,
            fill=(0, 0, 0, 128),
            anchor="mm",
            align="center",
        )

        combined = Image.alpha_composite(grid_canvas, txt)

        os.makedirs(output_folder, exist_ok=True)
        grid_filename = f"large_grid_set_{grid_set + 1}.png"
        combined.save(os.path.join(output_folder, grid_filename), "PNG")

def create_pattern(input_folder):
    IMAGE_SIZE = 2048
    GRID_SIZE = 2

    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))[:3]
    output_folder = os.path.join(input_folder, "mocks")

    print("   Creating 2x2 image grids...")

    for index, image_path in enumerate(images):
        output_image = Image.new("RGBA", (IMAGE_SIZE, IMAGE_SIZE))
        source_image = Image.open(image_path).convert("RGBA")

        square_size = IMAGE_SIZE // GRID_SIZE
        source_image = source_image.resize((square_size, square_size), Image.LANCZOS)

        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                output_image.paste(source_image, (i * square_size, j * square_size))

        txt = Image.new("RGBA", output_image.size, (255, 255, 255, 0))
        font = ImageFont.truetype("./fonts/Clattering.ttf", 185)

        text = "Seamless Patterns"
        text_position = (IMAGE_SIZE // 2, IMAGE_SIZE // 2)

        txtLayer = ImageDraw.Draw(txt)
        txtLayer.text(
            text_position,
            text,
            font=font,
            fill=(0, 0, 0, 192),
            anchor="mm",
            align="center",
        )

        combined = Image.alpha_composite(output_image, txt)

        os.makedirs(output_folder, exist_ok=True)
        filename = f"seamless_{index + 1}.png"
        combined.save(os.path.join(output_folder, filename), "PNG")

    videoSource = "seamless_1.png"
    img = cv2.imread(os.path.join(output_folder, videoSource))
    height, width, _ = img.shape

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(os.path.join(output_folder, "zoom_out.mp4"), fourcc, 30.0, (width, height))

    for zoom in np.linspace(0.5, 1.0, 180):
        start_row = int((1 - zoom) * height / 2)
        start_col = int((1 - zoom) * width / 2)
        end_row = start_row + int(zoom * height)
        end_col = start_col + int(zoom * width)

        frame = img[start_row:end_row, start_col:end_col]
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)
        video.write(frame)

    video.release()

if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_directory, "input")

    print("Deleting all .Identifier files...")
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".Identifier"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder

            create_main_mockup(subfolder_path, title)
            create_pattern(subfolder_path)
            create_large_grid(subfolder_path)

