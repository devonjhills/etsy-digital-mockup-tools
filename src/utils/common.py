"""
Common utility functions used across different modules.
"""

import os
import sys
import logging
import math
from typing import Optional, Tuple, List, Dict, Any, Union
from pathlib import Path
import glob
from PIL import Image, ImageDraw, ImageFont


# Configure logging
def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up and return a logger with the given name and level.

    Args:
        name: The name of the logger
        level: The logging level (default: logging.INFO)

    Returns:
        A configured logger instance
    """
    # Check if root logger is already configured
    root = logging.getLogger()
    if not root.handlers:
        # Configure root logger once
        logging.basicConfig(format="%(message)s", level=level)

    # Get the named logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicate messages
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    return logger


# Path handling
def get_project_root() -> str:
    """
    Get the absolute path to the project root directory.

    Returns:
        The absolute path to the project root directory
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_asset_path(asset_name: str) -> Optional[str]:
    """
    Get the absolute path to an asset file.

    Args:
        asset_name: The name of the asset file

    Returns:
        The absolute path to the asset file, or None if not found
    """
    project_root = get_project_root()
    assets_dir = os.path.join(project_root, "assets")

    # Check if it's a font file
    if asset_name.lower().endswith((".ttf", ".otf")):
        path = os.path.join(assets_dir, "fonts", asset_name)
    else:
        path = os.path.join(assets_dir, asset_name)

    if not os.path.exists(path):
        return None

    return path


# Image handling
def safe_load_image(
    image_path: str, mode: Optional[str] = None
) -> Optional[Image.Image]:
    """
    Safely load an image file, with optional conversion to a specific mode.

    Args:
        image_path: The path to the image file
        mode: The mode to convert the image to (e.g., 'RGB', 'RGBA')

    Returns:
        The loaded image, or None if loading failed
    """
    try:
        img = Image.open(image_path)
        if mode and img.mode != mode:
            img = img.convert(mode)
        return img
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None


def get_resampling_filter():
    """
    Get the appropriate resampling filter based on the PIL version.

    Returns:
        The appropriate resampling filter
    """
    try:
        # Newer Pillow versions (>= 9.1.0) use Resampling enum
        return Image.Resampling.LANCZOS
    except AttributeError:
        # Fallback for older Pillow versions
        return Image.LANCZOS


def resize_image(
    img: Image.Image, target_size: Tuple[int, int], maintain_aspect: bool = True
) -> Image.Image:
    """
    Resize an image to the target size.

    Args:
        img: The image to resize
        target_size: The target size (width, height)
        maintain_aspect: Whether to maintain the aspect ratio

    Returns:
        The resized image
    """
    if maintain_aspect:
        img.thumbnail(target_size, get_resampling_filter())
        return img
    else:
        return img.resize(target_size, get_resampling_filter())


# File operations
def ensure_dir_exists(directory: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory: The directory path

    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {e}")
        return False


def clean_identifier_files(directory: str) -> int:
    """
    Remove common identifier and system files from a directory and its subdirectories.

    Args:
        directory: The directory to clean

    Returns:
        The number of files removed
    """
    files_removed = 0
    files_to_remove = {".DS_Store", "Thumbs.db", "desktop.ini"}
    extensions_to_remove = (".Identifier", ".identifier")

    try:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [
                d for d in dirs if d not in {"mocks", "zipped", "temp_zip_creation"}
            ]
            for file in files:
                remove_file = False
                if file in files_to_remove:
                    remove_file = True
                else:
                    for ext in extensions_to_remove:
                        if file.endswith(ext):
                            remove_file = True
                            break
                if remove_file:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        files_removed += 1
                    except OSError:
                        pass
    except Exception:
        pass

    return files_removed


def apply_watermark(
    image: Image.Image,
    text: str = "digital veil",
    font_name: str = "Clattering",
    font_size: int = 50,
    text_color: Tuple[int, int, int] = (120, 120, 120),
    opacity: int = 80,
    diagonal_spacing: int = 350,
) -> Image.Image:
    """
    Apply a clean diagonal text watermark to an image.

    Args:
        image: The image to watermark
        text: The watermark text
        font_name: The font name for text watermarks
        font_size: The font size for text watermarks
        text_color: The text color for text watermarks (RGB)
        opacity: The opacity of the watermark (0-255)
        diagonal_spacing: Distance between watermarks diagonally

    Returns:
        The watermarked image
    """
    import math
    
    # Create a copy of the image and ensure it's RGBA
    result = image.copy().convert("RGBA")
    
    # Create a transparent overlay for watermark
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Get font
    font = get_font(font_name, font_size)
    
    # Calculate text size
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = draw.textsize(text, font=font)
    
    # Calculate how many watermarks we need
    image_diagonal = math.sqrt(result.width ** 2 + result.height ** 2)
    num_watermarks = int(image_diagonal / diagonal_spacing) + 2
    
    # Place watermarks diagonally across the image
    for i in range(-2, num_watermarks):
        for j in range(-2, num_watermarks):
            # Calculate position on a diagonal grid
            x = i * diagonal_spacing + j * diagonal_spacing * 0.5
            y = j * diagonal_spacing
            
            # Rotate the grid 45 degrees
            rotated_x = x * math.cos(math.radians(45)) - y * math.sin(math.radians(45))
            rotated_y = x * math.sin(math.radians(45)) + y * math.cos(math.radians(45))
            
            # Offset to center the pattern
            final_x = rotated_x + result.width // 2 - text_width // 2
            final_y = rotated_y + result.height // 2 - text_height // 2
            
            # Only draw if the text would be visible
            if (final_x + text_width > 0 and final_x < result.width and
                final_y + text_height > 0 and final_y < result.height):
                draw.text((final_x, final_y), text, font=font, fill=(*text_color, opacity))
    
    # Composite the watermark onto the original image
    result = Image.alpha_composite(result, overlay)
    
    return result


# Font handling
def get_font(
    font_name: str, size: int, fallback_names: List[str] = None
) -> Optional[ImageFont.FreeTypeFont]:
    """
    Get a font with the given name and size. Checks system fonts first, then project fonts.

    Args:
        font_name: The name of the font
        size: The font size
        fallback_names: A list of fallback font names

    Returns:
        The font, or None if not found
    """

    # Check if font_name is a path
    if os.path.exists(font_name) and font_name.lower().endswith((".ttf", ".otf")):
        try:
            font = ImageFont.truetype(font_name, size)
            return font
        except Exception:
            # Continue with normal font loading
            pass

    if fallback_names is None:
        fallback_names = []

    # System font directories
    system_font_dirs = [
        # macOS system fonts
        "/System/Library/Fonts",
        "/Library/Fonts",
        # User fonts
        os.path.expanduser("~/Library/Fonts"),
    ]

    # First try to find the font in system font directories
    for font_dir in system_font_dirs:
        if os.path.exists(font_dir):
            try:
                font_files = os.listdir(font_dir)
                # Try exact match first
                if f"{font_name}.ttf" in font_files:
                    font_path = os.path.join(font_dir, f"{font_name}.ttf")
                    try:
                        return ImageFont.truetype(font_path, size)
                    except Exception:
                        pass

                # Try to find a partial match
                for font_file in font_files:
                    if (
                        font_file.lower().endswith((".ttf", ".otf"))
                        and font_name.lower() in font_file.lower()
                    ):
                        font_path = os.path.join(font_dir, font_file)
                        try:
                            return ImageFont.truetype(font_path, size)
                        except Exception:
                            pass
            except Exception:
                pass

    # If system fonts didn't work, try project fonts
    project_root = get_project_root()
    fonts_dir = os.path.join(project_root, "assets", "fonts")

    # Check if fonts directory exists
    if not os.path.exists(fonts_dir):
        return ImageFont.load_default()

    # Try to find the font in the assets/fonts directory
    try:
        font_files = os.listdir(fonts_dir)
        matching_fonts = []

        # First, try to find an exact match
        for font_file in font_files:
            if font_file.lower().endswith((".ttf", ".otf")):
                # Check if the font name is in the filename
                if font_name.lower() in font_file.lower():
                    font_path = os.path.join(fonts_dir, font_file)
                    matching_fonts.append(font_path)

        # If we found matching fonts, try to load them
        for font_path in matching_fonts:
            try:
                font = ImageFont.truetype(font_path, size)
                return font
            except Exception:
                pass

        # If we didn't find any matching fonts, try the fallback fonts
        for fallback in fallback_names:
            # Try to find the fallback font in the assets/fonts directory
            for font_file in font_files:
                if font_file.lower().endswith((".ttf", ".otf")):
                    if fallback.lower() in font_file.lower():
                        try:
                            font_path = os.path.join(fonts_dir, font_file)
                            font = ImageFont.truetype(font_path, size)
                            return font
                        except Exception:
                            pass
    except Exception:
        pass

    # If we still haven't found a font, use the default font
    try:
        return ImageFont.load_default().font_variant(size=size)
    except AttributeError:
        return ImageFont.load_default()


# Process execution
def run_script(
    script_path: str, script_name: str, script_args: List[str] = None, cwd: str = None
) -> bool:
    """
    Run a Python script with the given arguments.

    Args:
        script_path: The path to the script
        script_name: A user-friendly name for the script
        script_args: A list of arguments to pass to the script
        cwd: The working directory to run the script in

    Returns:
        True if the script ran successfully, False otherwise
    """
    import subprocess

    if cwd is None:
        cwd = get_project_root()

    python_executable = sys.executable
    command_list = [python_executable, script_path] + (
        script_args if script_args else []
    )

    print(f"Running: {script_name}")

    try:
        result = subprocess.run(
            command_list,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Only print output if there's an error or it's very short
        stdout_lines = result.stdout.splitlines()
        if result.stderr or len(stdout_lines) < 5:
            print(f"Output from {script_name}:")
            if len(stdout_lines) < 20:
                print(result.stdout)
            else:
                # Print just the first few and last few lines
                for line in stdout_lines[:3]:
                    print(line)
                print("...")
                for line in stdout_lines[-3:]:
                    print(line)

        if result.stderr:
            print(f"Error output from {script_name}:")
            print(result.stderr)

        print(f"Finished {script_name} successfully")
        return True

    except FileNotFoundError:
        print(f"Error: Script not found at '{script_path}'")
        return False

    except subprocess.CalledProcessError as e:
        print(f"Error: {script_name} failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

    except Exception as e:
        print(f"Unexpected error running {script_name}: {e}")
        return False
