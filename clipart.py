import os
import glob
import cv2
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import numpy as np

# Set up constants for size and padding
OUTPUT_SIZE = (3000, 2250)
GRID_2x2_SIZE = (2000, 2000)  # Smaller size for 2x2 grids
GRID_COLS = 2
GRID_ROWS = 2
CELL_PADDING = 10  # Interior padding for grid cells


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


def calculate_text_block_width(title, title_font):
    """Calculate minimum width needed for text block based on title length."""
    BASE_WIDTH = 1550  # Default width
    PADDING = 200  # Extra padding for safety

    title_width = int(title_font.getlength(title))  # Convert to integer
    required_width = max(BASE_WIDTH, title_width + PADDING)

    # Cap maximum width to prevent exceeding screen and ensure integer
    return int(min(required_width, OUTPUT_SIZE[0] - 100))


def create_2x2_grid(input_images):
    """Create a simple 2x2 grid layout."""
    # Load canvas texture instead of white background
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(GRID_2x2_SIZE, Image.LANCZOS)
    grid_img = canvas_bg.copy()

    if not input_images:
        return grid_img

    cell_width = (GRID_2x2_SIZE[0] // GRID_COLS) - (CELL_PADDING * 2)
    cell_height = (GRID_2x2_SIZE[1] // GRID_ROWS) - (CELL_PADDING * 2)

    for idx, img_path in enumerate(input_images[:4]):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x = (col * (cell_width + CELL_PADDING * 2)) + CELL_PADDING
        y = (row * (cell_height + CELL_PADDING * 2)) + CELL_PADDING

        # Load image before processing
        img = Image.open(img_path).convert("RGBA")

        # Resize image to fit cell while maintaining aspect ratio
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


def grid_mockup(input_folder, title):
    global INPUT_FOLDER, OUTPUT_FOLDER

    INPUT_FOLDER = input_folder
    output_folder = os.path.join(INPUT_FOLDER, "mocks")
    OUTPUT_FOLDER = output_folder

    input_images = sorted(glob.glob(os.path.join(INPUT_FOLDER, "*png")))
    loaded_images = load_images(input_images[:12])  # Changed back to 12 images
    
    # Create organic layout for main mockup
    main_mockup = create_organic_layout(loaded_images, OUTPUT_SIZE)
    
    # Add overlay and title
    if title:
        main_mockup = add_overlay_and_title(main_mockup, title)

    # Save main mockup
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_main = os.path.join(OUTPUT_FOLDER, "main.png")
    main_mockup.save(output_main, "PNG")

    # Create 2x2 grid mockups for the rest (unchanged)
    mockup_no_text = create_2x2_grid(input_images[:4])
    mockup_no_text_with_watermark = apply_watermark(mockup_no_text)
    output_no_text = os.path.join(OUTPUT_FOLDER, "mockup_no_text.png")
    mockup_no_text_with_watermark.save(output_no_text, "PNG")

    video_filenames = [output_no_text]
    output_filenames = [output_main, output_no_text]

    # Rest of the function remains unchanged
    for i in range(4, len(input_images), 4):
        mockup = create_2x2_grid(input_images[i : i + 4])
        mockup_with_watermark = apply_watermark(mockup)
        output_filename = os.path.join(OUTPUT_FOLDER, f"mockup_{i // 4 + 1}.png")
        mockup_with_watermark.save(output_filename, "PNG")
        output_filenames.append(output_filename)
        video_filenames.append(output_filename)

    if input_images:
        trans_demo = create_transparency_demo(input_images[0])
        output_trans_demo = os.path.join(OUTPUT_FOLDER, "transparency_demo.png")
        trans_demo.save(output_trans_demo, "PNG")
        output_filenames.append(output_trans_demo)
        video_filenames.append(output_trans_demo)

    if len(video_filenames) > 1:
        video_path = os.path.join(OUTPUT_FOLDER, "mockup_video.mp4")
        create_video_mockup(video_filenames, video_path)
        output_filenames.append(video_path)

    return output_filenames


def create_grid(input_images, title=None, with_text_overlay=True):
    """Create a grid layout with precise measurements for 3000x2250 canvas."""
    grid_img = Image.new("RGBA", OUTPUT_SIZE, (255, 255, 255, 255))

    if len(input_images) == 0:
        return grid_img, None, None

    # Calculate bottom right image dimensions based on actual image
    bottom_right_img = Image.open(input_images[5]) if len(input_images) > 5 else None
    if bottom_right_img:
        img_aspect = bottom_right_img.width / bottom_right_img.height
        available_height = OUTPUT_SIZE[1] * 0.50  # 50% of canvas height
        target_width = available_height * img_aspect
        width_pct = min(
            0.40, target_width / OUTPUT_SIZE[0]
        )  # Cap at 40% of canvas width
    else:
        width_pct = 0.40

    # Calculate remaining width for bottom small images
    remaining_width = 1.0 - width_pct
    small_cell_width = remaining_width / 3  # Split remaining width into 3 columns
    small_cell_height = 0.25  # Two rows in bottom half

    grid_cells = [
        # 1: Large left image (1200x1125)
        (
            CELL_PADDING / OUTPUT_SIZE[0],
            CELL_PADDING / OUTPUT_SIZE[1],
            0.40 - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.50 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
        # 2, 3: Top row small images
        (
            0.40 + (CELL_PADDING / OUTPUT_SIZE[0]),
            CELL_PADDING / OUTPUT_SIZE[1],
            0.30 - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.25 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
        (
            0.70 + (CELL_PADDING / OUTPUT_SIZE[0]),
            CELL_PADDING / OUTPUT_SIZE[1],
            0.30 - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.25 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
        # 4, 5: Second row small images
        (
            0.40 + (CELL_PADDING / OUTPUT_SIZE[0]),
            0.25 + (CELL_PADDING / OUTPUT_SIZE[1]),
            0.30 - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.25 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
        (
            0.70 + (CELL_PADDING / OUTPUT_SIZE[0]),
            0.25 + (CELL_PADDING / OUTPUT_SIZE[1]),
            0.30 - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.25 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
        # 6: Large right image - now positioned at the rightmost edge
        (
            1.0 - width_pct + (CELL_PADDING / OUTPUT_SIZE[0]),
            0.50 + (CELL_PADDING / OUTPUT_SIZE[1]),
            width_pct - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
            0.50 - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
        ),
    ]

    # Add positions for the 6 bottom left images in 2x3 grid
    if len(input_images) > 6:
        for row in range(2):
            for col in range(3):
                x_pos = col * small_cell_width + (CELL_PADDING / OUTPUT_SIZE[0])
                y_pos = (
                    0.50 + (row * small_cell_height) + (CELL_PADDING / OUTPUT_SIZE[1])
                )
                grid_cells.append(
                    (
                        x_pos,
                        y_pos,
                        small_cell_width - (CELL_PADDING * 2 / OUTPUT_SIZE[0]),
                        small_cell_height - (CELL_PADDING * 2 / OUTPUT_SIZE[1]),
                    )
                )

    for idx, img_path in enumerate(input_images[:6]):
        if idx >= len(grid_cells):
            break

        img = Image.open(img_path).convert("RGBA")
        x_pct, y_pct, w_pct, h_pct = grid_cells[idx]
        x = int(OUTPUT_SIZE[0] * x_pct)
        y = int(OUTPUT_SIZE[1] * y_pct)
        width = int(OUTPUT_SIZE[0] * w_pct)
        height = int(OUTPUT_SIZE[1] * h_pct)

        img_aspect = img.width / img.height
        cell_aspect = width / height

        if img_aspect > cell_aspect:
            target_width = width
            target_height = int(width / img_aspect)
            y_offset = (height - target_height) // 2
            x_offset = 0
        else:
            target_height = height
            target_width = int(height * img_aspect)
            x_offset = (width - target_width) // 2
            y_offset = 0

        resized = img.resize((target_width, target_height), Image.LANCZOS)
        grid_img.paste(resized, (x + x_offset, y + y_offset), resized)

    if len(input_images) > 6:
        remaining_width = 0.40
        cell_width_pct = remaining_width / 3  # Percentage of total width
        cell_height_pct = 0.25

        for i in range(6, min(len(input_images), 12)):  # Limit to 12 images total
            col = (i - 6) % 3
            row = (i - 6) // 3

            x_pct = col * cell_width_pct
            y_pct = 0.50 + row * cell_height_pct

            grid_cells.append((x_pct, y_pct, cell_width_pct, cell_height_pct))

        for idx, img_path in enumerate(input_images[6:]):
            if idx >= len(grid_cells) - 6:
                break

            img = Image.open(img_path).convert("RGBA")
            x_pct, y_pct, w_pct, h_pct = grid_cells[idx + 6]
            x = int(OUTPUT_SIZE[0] * x_pct)
            y = int(OUTPUT_SIZE[1] * y_pct)
            width = int(OUTPUT_SIZE[0] * w_pct)
            height = int(OUTPUT_SIZE[1] * h_pct)

            img_aspect = img.width / img.height
            cell_aspect = width / height

            if img_aspect > cell_aspect:
                target_width = width
                target_height = int(width / img_aspect)
                y_offset = (height - target_height) // 2
                x_offset = 0
            else:
                target_height = height
                target_width = int(height * img_aspect)
                x_offset = (width - target_width) // 2
                y_offset = 0

            resized = img.resize((target_width, target_height), Image.LANCZOS)
            grid_img.paste(resized, (x + x_offset, y + y_offset), resized)

    if with_text_overlay and title:
        title_font = ImageFont.truetype("./fonts/Cravelo DEMO.otf", 200)
        details_font = ImageFont.truetype("./fonts/DSMarkerFelt.ttf", 100)
        subtitle_font = ImageFont.truetype("./fonts/DSMarkerFelt.ttf", 100)
        return grid_img, None, (title_font, details_font, subtitle_font, title)
    else:
        return grid_img, None, (None, None, None, None)


def add_text_background(image, text_block_width=1550, text_area_height=500):
    """Adds a colored rectangular background with exact dimensions."""
    text_area_y_start = (OUTPUT_SIZE[1] - text_area_height) // 2
    text_area_x_start = (OUTPUT_SIZE[0] - text_block_width) // 2
    overlay = Image.new("RGBA", (text_block_width, text_area_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle(
        [0, 0, text_block_width - 1, text_area_height - 1],
        radius=40,
        fill=(255, 255, 255, 200),
        outline=(0, 0, 0, 255),
        width=2,
    )
    image.paste(overlay, (text_area_x_start, text_area_y_start), overlay)
    return image, text_area_y_start, text_area_height


def draw_text(image, text_info, text_area_y_start=None, text_area_height=None):
    """Draw title and additional text on the image."""
    if not text_info:
        return
    title_font, details_font, subtitle_font, title = text_info
    draw = ImageDraw.Draw(image)

    # Use passed dimensions instead of getting new ones
    text_top = text_area_y_start
    text_bottom = text_top + text_area_height
    center_x = OUTPUT_SIZE[0] // 2
    center_y = text_top + (text_area_height // 2) - 20

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


def create_transparency_demo(
    image_path, text="Transparent PNG for all your design needs"
):
    """Creates a mockup showing transparency with split dark/light checkerboard pattern."""
    canvas_size = (3000, 2250)
    demo = Image.new("RGBA", canvas_size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(demo)

    # Load the image
    image = Image.open(image_path).convert("RGBA")

    # Split checkerboard pattern
    square_size = 80
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
                    [x, y, x + square_size, y + square_size], fill=fill_color
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

    # Create text background (without logo consideration)
    font = ImageFont.truetype("./fonts/DSMarkerFelt.ttf", 120)
    text_width = font.getlength(text)
    text_height = 150

    # Create background just for text
    text_bg = Image.new(
        "RGBA", (int(text_width + 100), text_height + 40), (255, 255, 255, 255)
    )

    # Load and resize logo (bigger size)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo = Image.open(os.path.join(script_dir, "logo.png")).convert("RGBA")
    logo_height = int(text_height * 2)  # Convert to integer
    logo_width = int(
        logo_height * logo.width / logo.height
    )  # Already converting to int
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    # Calculate positions
    text_bg_x = (canvas_size[0] - text_bg.width) // 2
    logo_x = text_bg_x - logo_width - 40  # Place logo to left of text box

    # Paste elements
    demo.paste(text_bg, (text_bg_x, 80), text_bg)
    demo.paste(logo, (logo_x, 65), logo)  # Adjusted Y position to align with text

    # Draw text
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
    """Create a video with smooth transitions between images."""
    if not images:
        return

    TARGET_SIZE = (2000, 2000)

    def resize_for_video(img):
        """Resize image to target size with padding."""
        h, w = img.shape[:2]
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

        resized = cv2.resize(img, (new_w, new_h))
        padded = cv2.copyMakeBorder(
            resized,
            pad_y,
            pad_y,
            pad_x,
            pad_x,
            cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )
        return padded

    def create_transition(img1, img2, num_frames):
        frames = []
        for i in range(num_frames):
            alpha = i / num_frames
            blended = cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)
            frames.append(blended)
        return frames

    # Load and resize all images
    cv2_images = [resize_for_video(cv2.imread(img)) for img in images]

    # Initialize video writer with new dimensions
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, 30, TARGET_SIZE)

    # Create video frames with transitions
    for i in range(len(cv2_images)):
        # Write current frame for display duration
        for _ in range(display_frames):
            out.write(cv2_images[i])

        # Create transition to next image
        if i < len(cv2_images) - 1:
            transition = create_transition(
                cv2_images[i], cv2_images[(i + 1)], num_transition_frames
            )
            for frame in transition:
                out.write(frame)

    # Write last frame for display duration
    for _ in range(display_frames):
        out.write(cv2_images[-1])

    out.release()


def create_organic_layout(images, canvas_size):
    """Create a uniform 4x3 grid layout with larger corner images and random horizontal flips."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(canvas_size, Image.LANCZOS)
    canvas = canvas_bg.copy()
    
    # Define grid dimensions
    grid_cols = 4
    grid_rows = 3
    cell_width = canvas_size[0] // grid_cols
    cell_height = canvas_size[1] // grid_rows
    
    # Define larger size for corner images
    corner_scale = 1.3
    
    for idx, img in enumerate(images[:12]):
        row = idx // grid_cols
        col = idx % grid_cols
        
        x = col * cell_width
        y = row * cell_height
        
        # Determine if the image is a corner image
        if idx in [0, 3, 8, 11]:
            target_width = int(cell_width * corner_scale)
            target_height = int(cell_height * corner_scale)
        else:
            target_width = cell_width
            target_height = cell_height
        
        # Move interior images in the middle row outward
        if row == 1 and col in [1, 2]:
            if col == 1:
                x -= cell_width // 4
            elif col == 2:
                x += cell_width // 4
        
        # Resize image to fit cell while maintaining aspect ratio
        img_aspect = img.width / img.height
        cell_aspect = target_width / target_height
        
        if img_aspect > cell_aspect:
            target_width = target_width
            target_height = int(target_width / img_aspect)
            y_offset = (cell_height - target_height) // 2
            x_offset = 0
        else:
            target_height = target_height
            target_width = int(target_height * img_aspect)
            x_offset = (cell_width - target_width) // 2
            y_offset = 0
        
        resized = img.resize((target_width, target_height), Image.LANCZOS)
        
        # Randomly flip some images horizontally
        if np.random.random() < 0.5:
            resized = resized.transpose(Image.FLIP_LEFT_RIGHT)
        
        canvas.paste(resized, (x + x_offset, y + y_offset), resized)
    
    return canvas

def add_overlay_and_title(image, title):
    """Add clip overlay and centered title text."""
    # Load and apply overlay
    script_dir = os.path.dirname(os.path.abspath(__file__))
    overlay = Image.open(os.path.join(script_dir, "clip_overlay.png")).convert("RGBA")
    overlay = overlay.resize(image.size, Image.LANCZOS)
    image = Image.alpha_composite(image, overlay)
    
    # Prepare for text with new size constraints
    draw = ImageDraw.Draw(image)
    max_width = 1000   # Updated width constraint
    max_height = 550  # Updated height constraint
    font_size = 125  # Use provided font size directly
    
    def get_text_dimensions(text, font_size):
        font = ImageFont.truetype("./fonts/Free Version Angelina.ttf", font_size)
        words = text.split()
        lines = []
        
        # Try one line first
        one_line_width = draw.textlength(text, font=font)
        bbox_single = draw.textbbox((0, 0), text, font=font)
        if one_line_width <= max_width and (bbox_single[3] - bbox_single[1]) <= max_height:
            return font, [text]
        
        # Try two lines with balanced word count
        mid_point = len(words) // 2
        line1 = ' '.join(words[:mid_point])
        line2 = ' '.join(words[mid_point:])
        
        if draw.textlength(line1, font=font) <= max_width and draw.textlength(line2, font=font) <= max_width:
            lines = [line1, line2]
        else:
            return None, None
        
        # Verify total height with new constraint
        bbox = draw.textbbox((0, 0), '\n'.join(lines), font=font)
        if (bbox[3] - bbox[1]) <= max_height and (bbox[2] - bbox[0]) <= max_width:
            return font, lines
        return None, None
    
    # Dynamically adjust font size if necessary
    while font_size > 0:
        font, lines = get_text_dimensions(title, font_size)
        if font and lines:
            break
        font_size -= 5  # Decrease font size and try again
    
    if not font or not lines:
        return image
    
    # Calculate center position
    text = '\n'.join(lines)
    
    center_x = image.width // 2
    center_y = (image.height // 2) - 50  # Keep slight upward offset
    
    # Draw text with precise centering and reduced line spacing
    line_spacing = 60  # Adjust this value to reduce the gap between lines
    y_offset = center_y - (font_size + line_spacing) // 2 * (len(lines) - 1)
    
    for line in lines:
        draw.text((center_x, y_offset), line, font=font, fill=(0, 0, 0), anchor="mm", align="center")
        y_offset += font_size + line_spacing
    
    return image

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "input")

    print("Deleting all .Identifier files...")
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".Identifier"):
                file_path = os.path.join(root, file)
                os.remove(file_path)

    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder

        print(f"Processing folder: {subfolder_path} with title: {title}")
        grid_mockup(subfolder_path, title)

    print("Processing complete!")
