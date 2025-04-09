"""
Common utility functions used across different modules.
"""

import os
import sys
import logging
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
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
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


# Font handling
def get_font(
    font_name: str, size: int, fallback_names: List[str] = None
) -> Optional[ImageFont.FreeTypeFont]:
    """
    Get a font with the given name and size.

    Args:
        font_name: The name of the font
        size: The font size
        fallback_names: A list of fallback font names

    Returns:
        The font, or None if not found
    """
    logger = logging.getLogger(__name__)
    print(f"DEBUG: Loading font '{font_name}' at size {size}")

    if fallback_names is None:
        fallback_names = []

    # Get the project root and assets directory
    project_root = get_project_root()
    fonts_dir = os.path.join(project_root, "assets", "fonts")
    print(f"DEBUG: Fonts directory: {fonts_dir}")

    # Check if fonts directory exists
    if not os.path.exists(fonts_dir):
        print(f"DEBUG: Fonts directory not found at {fonts_dir}")
        logger.warning(f"Fonts directory not found at {fonts_dir}")
        return ImageFont.load_default()

    # Try to find the font in the assets/fonts directory
    font_files = os.listdir(fonts_dir)
    print(f"DEBUG: Available font files: {font_files}")
    matching_fonts = []

    # First, try to find an exact match
    for font_file in font_files:
        if font_file.lower().endswith((".ttf", ".otf")):
            # Check if the font name is in the filename
            if font_name.lower() in font_file.lower():
                matching_fonts.append(os.path.join(fonts_dir, font_file))
                print(f"DEBUG: Found matching font: {font_file}")

    print(f"DEBUG: Matching fonts: {matching_fonts}")

    # If we found matching fonts, try to load them
    for font_path in matching_fonts:
        try:
            print(f"DEBUG: Trying to load font: {font_path}")
            font = ImageFont.truetype(font_path, size)
            print(f"DEBUG: Successfully loaded font: {font_path}")
            return font
        except Exception as e:
            print(f"DEBUG: Error loading font {font_path}: {e}")
            logger.warning(f"Error loading font {font_path}: {e}")

    # If we didn't find any matching fonts, try the fallback fonts
    for fallback in fallback_names:
        print(f"DEBUG: Trying fallback font: {fallback}")
        # Try to find the fallback font in the assets/fonts directory
        for font_file in font_files:
            if font_file.lower().endswith((".ttf", ".otf")):
                if fallback.lower() in font_file.lower():
                    try:
                        print(f"DEBUG: Found fallback font: {font_file}")
                        font_path = os.path.join(fonts_dir, font_file)
                        font = ImageFont.truetype(font_path, size)
                        print(f"DEBUG: Successfully loaded fallback font: {font_path}")
                        return font
                    except Exception as e:
                        print(f"DEBUG: Error loading fallback font {font_file}: {e}")
                        logger.warning(f"Error loading fallback font {font_file}: {e}")

    # If we still haven't found a font, use the default font
    print(
        f"DEBUG: Could not find font '{font_name}' or any fallbacks. Using default font."
    )
    logger.warning(
        f"Could not find font '{font_name}' or any fallbacks. Using default font."
    )
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

    print("-" * 30)
    print(f"Running: {script_name}")
    print(f"Script Path: {script_path}")
    print(f"Full Command: {' '.join(command_list)}")
    print("-" * 30)

    try:
        result = subprocess.run(
            command_list,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        print(f"--- Output from {script_name} ---")
        stdout_lines = result.stdout.splitlines()
        if len(stdout_lines) < 50:
            print(result.stdout)
        else:
            print(f"(Output truncated - {len(stdout_lines)} lines)")
            for line in stdout_lines[:10]:
                print(line)
            print("...")
            for line in stdout_lines[-10:]:
                print(line)

        if result.stderr:
            print(f"--- Error Output (if any) from {script_name} ---")
            print(result.stderr)

        print(f"--- Finished {script_name} successfully ---")
        print("-" * 30 + "\n")
        return True

    except FileNotFoundError:
        print(f"\n*** Error: Script not found at '{script_path}' ***")
        print("Please ensure the file exists and the path is correct.")
        print("-" * 30 + "\n")
        return False

    except subprocess.CalledProcessError as e:
        print(f"\n*** Error: {script_name} failed with exit code {e.returncode}. ***")
        print("--- Standard Output (if any) ---")
        print(e.stdout)
        print("--- Error Output ---")
        print(e.stderr)
        print("-" * 30 + "\n")
        return False

    except Exception as e:
        print(
            f"\n*** An unexpected error occurred while trying to run {script_name}: {e} ***"
        )
        print("-" * 30 + "\n")
        return False
