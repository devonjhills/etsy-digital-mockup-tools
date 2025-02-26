import os
import cv2
import numpy as np
import glob
from PIL import Image, ImageDraw, ImageFont


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
    initial_font_size = 160  # Start with larger size
    max_width = 1380  # Maximum allowed width
    
    # Function to get font and text size
    def get_font_and_size(size):
        font = ImageFont.truetype("./fonts/Free Version Angelina.ttf", size)
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
    vertical_offset = 50  # Move up by 200 pixels
    text_y = (grid_height - text_height) // 2 - vertical_offset
    
    # Draw the text
    draw.text((text_x, text_y), title, font=font, fill=(0, 0, 0), anchor="lt")

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    grid_filename = "main.png"
    final_image.save(os.path.join(OUTPUT_FOLDER, grid_filename), "PNG")


def create_large_grid(input_folder):
    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))
    script_dir = os.path.dirname(os.path.abspath(__file__)) 
    
    GRID_ROWS = 2
    GRID_COLS = 2
    GRID_SIZE = 2025

    print("   Creating large grids...")

    output_folder = os.path.join(input_folder, "mocks")

    num_images = len(images)
    if num_images < GRID_ROWS * GRID_COLS * 3:
        raise ValueError(
            f"At least {GRID_ROWS * GRID_COLS * 3} images required, but only {num_images} found."
        )

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

        border_thickness = 15  # Increased from 10 to 15
        for j in range(1, GRID_COLS):
            border_x = j * square_width
            draw.line(
                [(border_x, 0), (border_x, grid_height)],
                fill="white",  # Changed from black to white
                width=border_thickness,
            )

        for k in range(1, GRID_ROWS):
            border_y = k * square_height
            draw.line(
                [(0, border_y), (grid_width, border_y)],
                fill="white",  # Changed from black to white
                width=border_thickness,
            )

        # Replace text watermark with semi-transparent logo
        logo_path = os.path.join(script_dir, "logo.png")
        logo = Image.open(logo_path).convert("RGBA")
        
        # Calculate logo size (e.g. 50% of grid width)
        logo_width = int(grid_width * 0.50)
        logo_height = int(logo_width * logo.size[1] / logo.size[0])
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

        # Make logo semi-transparent by adjusting alpha channel
        logo_data = logo.getdata()
        new_data = []
        for item in logo_data:
            # Preserve original RGB but reduce alpha to 70%
            new_data.append((item[0], item[1], item[2], int(item[3] * 0.7)))
        logo.putdata(new_data)

        # Calculate center position
        logo_x = (grid_width - logo_width) // 2
        logo_y = (grid_height - logo_height) // 2

        # Create new transparent layer and paste logo
        overlay = Image.new("RGBA", grid_canvas.size, (255, 255, 255, 0))
        overlay.paste(logo, (logo_x, logo_y), logo)

        combined = Image.alpha_composite(grid_canvas, overlay)

        # Save with optimized JPEG settings
        os.makedirs(output_folder, exist_ok=True)
        grid_filename = f"large_grid_set_{grid_set + 1}.jpg"
        combined.convert("RGB").save(
            os.path.join(output_folder, grid_filename),
            "JPEG",
            quality=85,
            optimize=True,
            subsampling="4:2:0",
        )


def create_pattern(input_folder):
    IMAGE_SIZE = 2048
    GRID_SIZE = 2

    images = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))[:1]  # Only take first image
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
        offsets = [(x,y) for x in (-3,3) for y in (-3,3)]
        for offset_x, offset_y in offsets:
            txtLayer.text(
            (text_position[0] + offset_x, text_position[1] + offset_y),
            text,
            font=font,
            fill=(255, 255, 255, 192),
            anchor="mm",
            align="center"
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

def create_irl_video(irl_folder):
    """Create a video from IRL images with fade transitions"""
    # Updated output folder to be in the parent directory's mocks subfolder
    output_folder = os.path.join(os.path.dirname(irl_folder), "mocks")
    os.makedirs(output_folder, exist_ok=True)
    
    images = sorted(glob.glob(os.path.join(irl_folder, "*.[jp][pn][g]")))
    if not images:
        return
        
    # Read first image to get dimensions
    img = cv2.imread(images[0])
    height, width = 1500, 1500  # Fixed dimensions
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(
        os.path.join(output_folder, "irl_showcase.mp4"), 
        fourcc, 30.0, (width, height)
    )
    
    def resize_image(img):
        # Resize and pad to square
        aspect = img.shape[1] / img.shape[0]
        if aspect > 1:
            new_w = width
            new_h = int(width / aspect)
            img = cv2.resize(img, (new_w, new_h))
            pad_y = (height - new_h) // 2
            return cv2.copyMakeBorder(img, pad_y, pad_y, 0, 0, cv2.BORDER_CONSTANT, value=(255,255,255))
        else:
            new_h = height
            new_w = int(height * aspect)
            img = cv2.resize(img, (new_w, new_h))
            pad_x = (width - new_w) // 2
            return cv2.copyMakeBorder(img, 0, 0, pad_x, pad_x, cv2.BORDER_CONSTANT, value=(255,255,255))
    
    # Parameters
    display_frames = 60  # 2 seconds display
    transition_frames = 30  # 1 second transition
    
    for i in range(len(images)):
        current = resize_image(cv2.imread(images[i]))
        next_img = resize_image(cv2.imread(images[(i + 1) % len(images)]))
        
        # Display current image
        for _ in range(display_frames):
            video.write(current)
        
        # Fade transition
        for j in range(transition_frames):
            alpha = j / transition_frames
            blend = cv2.addWeighted(current, 1 - alpha, next_img, alpha, 0)
            video.write(blend)
    
    video.release()

# New function to create seamless zoom video when no irl folder exists
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
    video_path = os.path.join(output_folder, "irl_showcase.mp4")
    video = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))
    
    total_frames = 90
    initial_zoom = 1.5  # start zoomed in (crop factor)
    for i in range(total_frames):
        t = i / (total_frames - 1)
        zoom_factor = initial_zoom - (initial_zoom - 1) * t  # interpolate zoom factor to 1.0
        new_w = int(width / zoom_factor)
        new_h = int(height / zoom_factor)
        x1 = (width - new_w) // 2
        y1 = (height - new_h) // 2
        crop = img[y1:y1+new_h, x1:x1+new_w]
        frame = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)
        video.write(frame)
    video.release()

if __name__ == "__main__":
    script_directory = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_directory, "input")

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder
            # First, create seamless patterns (needed for zoom video)
            create_pattern(subfolder_path)
            
            irl_path = os.path.join(subfolder_path, 'irl')
            if os.path.isdir(irl_path):
                print(f"Processing IRL folder in {title}...")
                create_irl_video(irl_path)
            else:
                print(f"No IRL folder found in {title}, creating seamless zoom video...")
                create_seamless_zoom_video(subfolder_path)
            
            # Continue processing other mockups
            create_main_mockup(subfolder_path, title)
            create_large_grid(subfolder_path)
