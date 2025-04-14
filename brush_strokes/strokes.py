import os
import glob
import cv2
import sys
from PIL import Image, ImageFont, ImageDraw

# Add the project root to the Python path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up constants for size and padding
OUTPUT_SIZE = (3000, 2250)
GRID_SIZE = (2000, 2000)  # Size for grid mockups
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
    # Use the consolidated watermarking function from utils.common
    from utils.common import apply_watermark as apply_watermark_util

    return apply_watermark_util(
        image=image,
        watermark_type="logo",
        logo_path=logo_path,
        opacity=opacity,
        spacing_factor=spacing_multiplier,
        angle=0,  # No rotation for logo watermarks
    )


def create_brush_strokes_layout(input_images):
    """Create a layout with vertical brush strokes slightly overlapping horizontally."""
    # Load canvas texture for background
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(OUTPUT_SIZE, Image.LANCZOS)
    layout_img = canvas_bg.copy()

    if not input_images:
        return layout_img

    # Limit to 7-8 brush strokes for main mockup
    max_strokes = min(8, len(input_images))
    stroke_images = input_images[:max_strokes]

    # Define the overlap amount. Adjust this value to control overlap:
    # A higher value means more overlap; a lower value means less.
    overlap_amount = 0

    canvas_width = OUTPUT_SIZE[0]
    stroke_width = int(canvas_width / (max_strokes - overlap_amount))

    # Calculate vertical scaling
    canvas_height = OUTPUT_SIZE[1]
    vertical_padding = canvas_height * 0.01  # 10% padding top and bottom
    stroke_height = int(canvas_height - (2 * vertical_padding))  # Convert to integer

    for idx, img_path in enumerate(stroke_images):
        # Load image
        img = Image.open(img_path).convert("RGBA")

        # Calculate target size preserving aspect ratio
        img_aspect = img.width / img.height
        target_height = stroke_height
        target_width = int(target_height * img_aspect)

        # Ensure stroke fits vertically
        if target_width > stroke_width * 2:
            target_width = stroke_width * 2
            target_height = int(target_width / img_aspect)

        # Resize the image
        resized = img.resize((target_width, target_height), Image.LANCZOS)

        # Calculate position (centered vertically, distributed horizontally with overlap)
        x_position = int((idx * stroke_width) - (stroke_width * 0.1))  # Adjust overlap
        y_position = int((canvas_height - target_height) / 2)

        # Paste the image
        layout_img.paste(resized, (x_position, y_position), resized)

    return layout_img


def create_grid_display(input_images, grid_index):
    """Create a grid display with 4 brush strokes in a single horizontal row."""
    # Load canvas texture for background
    script_dir = os.path.dirname(os.path.abspath(__file__))
    canvas_bg = Image.open(os.path.join(script_dir, "canvas.png")).convert("RGBA")
    canvas_bg = canvas_bg.resize(GRID_SIZE, Image.LANCZOS)
    grid_img = canvas_bg.copy()

    # Get the 4 images for this grid based on index
    start_idx = grid_index * 4
    end_idx = start_idx + 4
    current_images = input_images[start_idx:end_idx]

    if not current_images:
        return grid_img

    # Calculate cell dimensions for a single row layout
    cell_width = (GRID_SIZE[0] - 4 * CELL_PADDING) // 4  # 4 images with spacing between
    cell_height = GRID_SIZE[1] - 2 * CELL_PADDING  # Full height with vertical padding

    for idx, img_path in enumerate(current_images):
        # Calculate horizontal position
        x = CELL_PADDING + idx * (cell_width + CELL_PADDING)
        y = CELL_PADDING  # Single row vertical position

        # Load image
        img = Image.open(img_path).convert("RGBA")

        # Resize image to fit cell while maintaining aspect ratio
        img_aspect = img.width / img.height
        cell_aspect = cell_width / cell_height

        if img_aspect > cell_aspect:
            # Fit to width
            target_width = cell_width
            target_height = int(cell_width / img_aspect)
            y_offset = (cell_height - target_height) // 2
            x_offset = 0
        else:
            # Fit to height
            target_height = cell_height
            target_width = int(cell_height * img_aspect)
            x_offset = (cell_width - target_width) // 2
            y_offset = 0

        resized = img.resize((target_width, target_height), Image.LANCZOS)
        grid_img.paste(resized, (x + x_offset, y + y_offset), resized)

    return grid_img


def create_transparency_demo(image_path):
    """
    Opens an existing background image (transparency_demo.png) and places
    the provided image (image_path) on the left side, then returns the result.
    No text or arrows are applied.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load the existing background image
    demo = Image.open(os.path.join(script_dir, "transparency_mock.png")).convert("RGBA")

    # Load the image to place
    image = Image.open(image_path).convert("RGBA")

    # Calculate position to place the image on the left side, vertically centered
    x_pos = int(0.25 * demo.width - image.width / 2)
    y_pos = (demo.height - image.height) // 2

    # Paste the image onto the background
    demo.paste(image, (x_pos, y_pos), image)

    return demo


def add_overlay_and_title(image, title):
    """Add clip overlay and centered title text."""
    # Load and apply overlay
    script_dir = os.path.dirname(os.path.abspath(__file__))
    overlay = Image.open(os.path.join(script_dir, "clip_overlay.png")).convert("RGBA")
    overlay = overlay.resize(image.size, Image.LANCZOS)
    image = Image.alpha_composite(image, overlay)

    # Prepare for text
    draw = ImageDraw.Draw(image)
    max_width = 1000
    max_height = 550
    font_size = 125

    def get_text_dimensions(text, font_size):
        font = ImageFont.truetype("./fonts/Free Version Angelina.ttf", font_size)
        words = text.split()
        lines = []

        # Try one line first
        one_line_width = draw.textlength(text, font=font)
        bbox_single = draw.textbbox((0, 0), text, font=font)
        if (
            one_line_width <= max_width
            and (bbox_single[3] - bbox_single[1]) <= max_height
        ):
            return font, [text]

        # Try two lines with balanced word count
        mid_point = len(words) // 2
        line1 = " ".join(words[:mid_point])
        line2 = " ".join(words[mid_point:])

        if (
            draw.textlength(line1, font=font) <= max_width
            and draw.textlength(line2, font=font) <= max_width
        ):
            lines = [line1, line2]
        else:
            return None, None

        # Verify total height
        bbox = draw.textbbox((0, 0), "\n".join(lines), font=font)
        if (bbox[3] - bbox[1]) <= max_height and (bbox[2] - bbox[0]) <= max_width:
            return font, lines
        return None, None

    # Dynamically adjust font size if necessary
    while font_size > 0:
        font, lines = get_text_dimensions(title, font_size)
        if font and lines:
            break
        font_size -= 5

    if not font or not lines:
        return image

    # Calculate center position
    # text = "\n".join(lines)  # This variable is not used
    center_x = image.width // 2
    center_y = (image.height // 2) - 50

    # Draw text with precise centering and reduced line spacing
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

    # Initialize video writer
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


def brush_strokes_mockup(input_folder, title):
    """Main function to generate all mockups for brush strokes."""
    # Set up folders
    output_folder = os.path.join(input_folder, "mocks")
    os.makedirs(output_folder, exist_ok=True)

    # Get all PNG images in the input folder
    input_images = sorted(glob.glob(os.path.join(input_folder, "*png")))
    if not input_images:
        print(f"No PNG images found in {input_folder}")
        return []

    # Create main brush strokes layout
    main_mockup = create_brush_strokes_layout(input_images)

    # Add overlay and title
    if title:
        main_mockup = add_overlay_and_title(main_mockup, title)

    # Save main mockup
    output_main = os.path.join(output_folder, "main.png")
    main_mockup.save(output_main, "PNG")
    output_filenames = [output_main]
    video_filenames = []

    # Create grid displays (3 sets of 4 brush strokes)
    for i in range(3):
        if i * 4 >= len(input_images):
            break

        grid_mockup = create_grid_display(input_images, i)
        grid_with_watermark = apply_watermark(grid_mockup)

        output_filename = os.path.join(output_folder, f"grid_{i + 1}.png")
        grid_with_watermark.save(output_filename, "PNG")

        output_filenames.append(output_filename)
        video_filenames.append(output_filename)

    # Create transparency demo
    if input_images:
        trans_demo = create_transparency_demo(input_images[0])
        output_trans_demo = os.path.join(output_folder, "transparency_demo.png")
        trans_demo.save(output_trans_demo, "PNG")
        output_filenames.append(output_trans_demo)
        video_filenames.append(output_trans_demo)

    # Create video if we have multiple images
    if len(video_filenames) > 1:
        video_path = os.path.join(output_folder, "mockup_video.mp4")
        create_video_mockup(video_filenames, video_path)
        output_filenames.append(video_path)

    print(f"Created {len(output_filenames)} mockups in {output_folder}")
    return output_filenames


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "input")

    # Clean up identifier files using the utility function
    try:
        # Add the project root to the Python path to import utils
        project_root = os.path.dirname(script_dir)
        import sys

        sys.path.insert(0, project_root)
        from utils.common import clean_identifier_files

        num_removed = clean_identifier_files(input_folder)
        print(f"Deleted {num_removed} identifier/system files")
    except ImportError:
        print("Could not import clean_identifier_files from utils.common")
        print("Skipping identifier file cleanup")

    # Process each subfolder
    processed_count = 0
    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(subfolder_path):
            title = subfolder
            print(f"Processing folder: {subfolder_path} with title: {title}")
            brush_strokes_mockup(subfolder_path, title)
            processed_count += 1

    if processed_count == 0:
        print(
            "No subfolders found to process. Creating mockups for images in input folder."
        )
        brush_strokes_mockup(input_folder, "Brush Strokes")

    print("Processing complete!")
