"""
Common utility functions used across different modules.
"""

import os
import sys
import logging
import math
from typing import Optional, Tuple, List, Union, Callable
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from contextlib import contextmanager
from enum import Enum
from dataclasses import dataclass


# Constants for image processing
class ImageConstants:
    """Constants for image processing operations."""

    MAX_FILE_SIZE_MB = 100  # Maximum image file size in MB
    MAX_FONT_SIZE = 500  # Maximum font size
    MIN_FONT_SIZE = 8  # Minimum font size
    DEFAULT_DPI = 300  # Default DPI for image processing
    WATERMARK_PADDING = 20  # Padding around watermark text
    WATERMARK_SPACING_RATIO = 0.35  # Ratio of image size for watermark spacing
    FONT_SCALE_RATIO = 0.05  # Ratio for auto-scaling fonts


class FileConstants:
    """Constants for file operations."""

    SYSTEM_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
    IDENTIFIER_EXTENSIONS = (".Identifier", ".identifier")
    EXCLUDED_DIRS = {
        "mocks",
        "zipped",
        "temp_zip_creation",
        "temp",
        ".git",
        "__pycache__",
    }
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


class WatermarkDefaults:
    """Default values for watermarking."""

    TEXT = "digital veil"
    FONT_NAME = "Poppins-SemiBold"
    FONT_SIZE = 50
    COLOR = (120, 120, 120)
    OPACITY = 80
    ROTATION_ANGLE = -45.0


class LogLevel(Enum):
    """Enumeration of log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class ImageProcessingError(Exception):
    """Exception raised for image processing errors."""

    pass


class FontError(Exception):
    """Exception raised for font-related errors."""

    pass


class FileOperationError(Exception):
    """Exception raised for file operation errors."""

    pass


# Global GUI log function (set by GUI when available)
_gui_log_function: Optional[Callable[[str, str], None]] = None


def set_gui_log_function(log_func: Callable[[str, str], None]) -> None:
    """Set the GUI log function to route logs to GUI instead of console.

    Args:
        log_func: Function that accepts message and level parameters
    """
    global _gui_log_function
    _gui_log_function = log_func


def gui_log(message: str, level: str = LogLevel.INFO.value) -> None:
    """Send log message to GUI if available, otherwise ignore.

    Args:
        message: Log message to send
        level: Log level (info, warning, error, success)
    """
    if _gui_log_function:
        _gui_log_function(message, level)


# Configure logging for GUI-only mode
def setup_logging(
    name: str, level: int = logging.INFO, gui_only: bool = True
) -> logging.Logger:
    """
    Set up and return a logger with the given name and level.

    Args:
        name: The name of the logger
        level: The logging level (default: logging.INFO)
        gui_only: If True, only log to GUI, not console (default: True)

    Returns:
        A configured logger instance
    """
    # Get the named logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicate messages
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if gui_only:
        # Custom handler that routes to GUI only
        class GUIHandler(logging.Handler):
            def emit(self, record):
                message = self.format(record)
                level = (
                    "error"
                    if record.levelno >= logging.ERROR
                    else (
                        "success"
                        if "success" in message.lower() or "✓" in message
                        else "info"
                    )
                )
                gui_log(message, level)

        handler = GUIHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.propagate = False  # Prevent propagation to root logger
    else:
        # Fall back to console logging if GUI not available
        if not logging.getLogger().handlers:
            logging.basicConfig(format="%(message)s", level=level)

    return logger


# Path handling
def get_project_root() -> str:
    """
    Get the absolute path to the project root directory.

    Returns:
        The absolute path to the project root directory
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
@contextmanager
def image_context(image_path: Union[str, Path], mode: Optional[str] = None):
    """Context manager for safely loading and handling images.

    Args:
        image_path: Path to the image file
        mode: Optional mode to convert the image to

    Yields:
        PIL Image object

    Raises:
        ImageProcessingError: If image cannot be loaded or processed
    """
    img = None
    try:
        img = safe_load_image(str(image_path), mode)
        if img is None:
            raise ImageProcessingError(f"Failed to load image: {image_path}")
        yield img
    finally:
        if img:
            img.close()


def safe_load_image(
    image_path: Union[str, Path], mode: Optional[str] = None
) -> Optional[Image.Image]:
    """Safely load an image file with optional mode conversion.

    Args:
        image_path: Path to the image file
        mode: Optional mode to convert the image to (e.g., 'RGB', 'RGBA')

    Returns:
        The loaded image, or None if loading failed

    Raises:
        ImageProcessingError: If image format is not supported
    """
    try:
        if not os.path.exists(str(image_path)):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Check file size to prevent loading extremely large files
        file_size = os.path.getsize(str(image_path))
        max_size = ImageConstants.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise ImageProcessingError(
                f"Image file too large: {file_size / (1024*1024):.1f}MB"
            )

        with Image.open(str(image_path)) as img:
            # Verify image is not corrupted
            try:
                img.verify()
            except Exception:
                raise ImageProcessingError(f"Corrupted image file: {image_path}")

            # Reopen for actual use (verify closes the file)
            img = Image.open(str(image_path))

            # Load the image data efficiently
            if hasattr(img, "load"):
                img.load()

            # Convert mode if needed
            if mode and img.mode != mode:
                img = img.convert(mode)

            # Return a copy to avoid issues with closed files
            return img.copy()

    except FileNotFoundError as e:
        logging.getLogger(__name__).error(f"Image file not found: {image_path}")
        return None
    except Image.UnidentifiedImageError as e:
        logging.getLogger(__name__).error(f"Unsupported image format: {image_path}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error loading image {image_path}: {e}")
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
    img: Image.Image,
    target_size: Tuple[int, int],
    maintain_aspect: bool = True,
    optimize: bool = True,
) -> Image.Image:
    """Resize an image to the target size with optimization options.

    Args:
        img: The image to resize
        target_size: The target size (width, height)
        maintain_aspect: Whether to maintain the aspect ratio
        optimize: Whether to optimize for memory usage

    Returns:
        The resized image

    Raises:
        ImageProcessingError: If resizing fails
    """
    try:
        if not isinstance(img, Image.Image):
            raise ImageProcessingError("Input must be a PIL Image object")

        if len(target_size) != 2 or any(s <= 0 for s in target_size):
            raise ImageProcessingError(f"Invalid target size: {target_size}")

        # Check if resizing is actually needed
        if img.size == target_size:
            return img.copy() if optimize else img

        # Use more efficient method for large size reductions
        current_size = img.size
        target_width, target_height = target_size

        # If we're reducing by more than half, use draft mode for better performance
        if current_size[0] > target_width * 2 and current_size[1] > target_height * 2:
            try:
                # Draft mode for JPEG images - much faster for large reductions
                img.draft("RGB", target_size)
            except (OSError, KeyError):
                # Draft mode not available for this image type
                pass

        if maintain_aspect:
            # Create a copy to avoid modifying the original
            img_copy = img.copy() if optimize else img
            img_copy.thumbnail(target_size, get_resampling_filter())
            return img_copy
        else:
            return img.resize(target_size, get_resampling_filter())

    except Exception as e:
        raise ImageProcessingError(f"Image resizing failed: {e}") from e


# File operations
def ensure_dir_exists(directory: Union[str, Path]) -> bool:
    """Ensure that a directory exists, creating it if necessary.

    Args:
        directory: The directory path

    Returns:
        True if the directory exists or was created, False otherwise

    Raises:
        FileOperationError: If directory creation fails due to permissions or other issues
    """
    try:
        directory_path = Path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)

        # Verify the directory was actually created and is writable
        if not directory_path.exists():
            raise FileOperationError(f"Directory creation failed: {directory}")

        if not os.access(str(directory_path), os.W_OK):
            raise FileOperationError(f"Directory is not writable: {directory}")

        return True

    except PermissionError as e:
        error_msg = f"Permission denied creating directory {directory}: {e}"
        logging.getLogger(__name__).error(error_msg)
        raise FileOperationError(error_msg) from e
    except Exception as e:
        error_msg = f"Error creating directory {directory}: {e}"
        logging.getLogger(__name__).error(error_msg)
        return False


def clean_identifier_files(directory: Union[str, Path]) -> int:
    """Remove common identifier and system files from a directory and its subdirectories.

    Args:
        directory: The directory to clean

    Returns:
        The number of files removed

    Raises:
        FileOperationError: If directory access fails
    """
    logger = logging.getLogger(__name__)
    directory_path = Path(directory)

    if not directory_path.exists():
        raise FileOperationError(f"Directory does not exist: {directory}")

    if not directory_path.is_dir():
        raise FileOperationError(f"Path is not a directory: {directory}")

    files_removed = 0
    errors_encountered = []

    try:
        for root, dirs, files in os.walk(str(directory_path)):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in FileConstants.EXCLUDED_DIRS]

            for file in files:
                should_remove = file in FileConstants.SYSTEM_FILES or any(
                    file.endswith(ext) for ext in FileConstants.IDENTIFIER_EXTENSIONS
                )

                if should_remove:
                    file_path = Path(root) / file
                    try:
                        file_path.unlink()
                        files_removed += 1
                        logger.debug(f"Removed system file: {file_path}")
                    except OSError as e:
                        error_msg = f"Could not remove {file_path}: {e}"
                        errors_encountered.append(error_msg)
                        logger.warning(error_msg)

    except Exception as e:
        raise FileOperationError(f"Error cleaning directory {directory}: {e}") from e

    if errors_encountered:
        logger.warning(f"Encountered {len(errors_encountered)} errors while cleaning")

    logger.info(f"Removed {files_removed} system/identifier files from {directory}")
    return files_removed


@dataclass
class WatermarkConfig:
    """Configuration for watermark generation."""

    text: str = WatermarkDefaults.TEXT
    font_name: str = WatermarkDefaults.FONT_NAME
    font_size: int = WatermarkDefaults.FONT_SIZE
    text_color: Tuple[int, int, int] = WatermarkDefaults.COLOR
    opacity: int = WatermarkDefaults.OPACITY
    diagonal_spacing: Optional[int] = None
    rotation_angle: float = WatermarkDefaults.ROTATION_ANGLE

    def __post_init__(self) -> None:
        """Validate watermark configuration."""
        if not (0 <= self.opacity <= 255):
            raise ValueError(f"Opacity must be 0-255, got: {self.opacity}")
        if self.font_size <= 0:
            raise ValueError(f"Font size must be positive, got: {self.font_size}")


def _calculate_scaled_font_size(
    image_size: Tuple[int, int], requested_size: int
) -> int:
    """Calculate scaled font size based on image dimensions.

    Args:
        image_size: (width, height) of the image
        requested_size: Requested font size

    Returns:
        Scaled font size appropriate for the image
    """
    reference_size = min(image_size)

    # Scale font size based on image size (base: 1000px = 50pt font)
    if (
        requested_size == WatermarkDefaults.FONT_SIZE
    ):  # Using default font size, scale it
        min_size = max(ImageConstants.MIN_FONT_SIZE * 2, ImageConstants.MIN_FONT_SIZE)
        return max(min_size, int(reference_size * ImageConstants.FONT_SCALE_RATIO))
    else:
        return requested_size


def _get_text_dimensions(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont
) -> Tuple[int, int, int, int]:
    """Get text dimensions and offset using the most appropriate method available.

    Args:
        draw: ImageDraw object
        text: Text to measure
        font: Font to use

    Returns:
        (width, height, offset_x, offset_y) of the text and its positioning offset
    """
    try:
        # New method in newer PIL versions - gives us precise bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        # Offset needed to position text properly (accounting for negative bbox values)
        offset_x = -bbox[0]  # Compensate for negative left bearing
        offset_y = -bbox[1]  # Compensate for ascenders/descenders
        return width, height, offset_x, offset_y
    except AttributeError:
        # Fallback for older PIL versions
        width, height = draw.textsize(text, font=font)
        # For older PIL, assume no offset needed (less precise)
        return width, height, 0, 0


def _calculate_watermark_spacing(
    image_size: Tuple[int, int], diagonal_spacing: Optional[int]
) -> int:
    """Calculate diagonal spacing for watermarks.

    Args:
        image_size: (width, height) of the image
        diagonal_spacing: Optional custom spacing

    Returns:
        Diagonal spacing value
    """
    if diagonal_spacing is not None:
        return diagonal_spacing

    reference_size = min(image_size)
    # Target: ~4-5 watermarks across the shorter dimension
    return int(reference_size * ImageConstants.WATERMARK_SPACING_RATIO)


def _calculate_grid_positions(
    image_size: Tuple[int, int], diagonal_spacing: int
) -> List[Tuple[float, float]]:
    """Calculate grid positions for watermark placement.

    Args:
        image_size: (width, height) of the image
        diagonal_spacing: Spacing between watermarks

    Returns:
        List of (x, y) positions for watermarks
    """
    import math

    width, height = image_size
    image_diagonal = math.sqrt(width**2 + height**2)
    num_watermarks = int(image_diagonal / diagonal_spacing) + 2

    positions = []
    angle_rad = math.radians(45)

    for i in range(-2, num_watermarks):
        for j in range(-2, num_watermarks):
            # Create a regular grid pattern
            x = i * diagonal_spacing
            y = j * diagonal_spacing

            # Rotate the entire grid 45 degrees for diagonal placement
            rotated_x = x * math.cos(angle_rad) - y * math.sin(angle_rad)
            rotated_y = x * math.sin(angle_rad) + y * math.cos(angle_rad)

            # Center the pattern on the image
            final_x = rotated_x + width // 2
            final_y = rotated_y + height // 2

            positions.append((final_x, final_y))

    return positions


def _create_rotated_text_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    text_color: Tuple[int, int, int],
    opacity: int,
    rotation_angle: float = -45.0,
) -> Image.Image:
    """Create a rotated text image.

    Args:
        text: Text to render
        font: Font to use
        text_color: RGB color tuple
        opacity: Opacity value (0-255)
        rotation_angle: Rotation angle in degrees

    Returns:
        Rotated text image with transparency
    """
    # Get text size and positioning offset for temporary image
    temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_width, text_height, offset_x, offset_y = _get_text_dimensions(temp_draw, text, font)

    # Create temporary image with padding (extra space for proper positioning)
    padding = ImageConstants.WATERMARK_PADDING
    temp_img = Image.new(
        "RGBA", (text_width + padding * 2, text_height + padding * 2), (0, 0, 0, 0)
    )
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Position text with proper offset to account for descenders/ascenders
    text_x = padding + offset_x
    text_y = padding + offset_y
    temp_draw.text(
        (text_x, text_y), text, font=font, fill=(*text_color, opacity)
    )

    # Rotate the text
    return temp_img.rotate(rotation_angle, expand=True)


def _is_position_visible(
    pos: Tuple[float, float], text_size: Tuple[int, int], image_size: Tuple[int, int]
) -> bool:
    """Check if a watermark position would be visible on the image.

    Args:
        pos: (x, y) position of watermark center
        text_size: (width, height) of the text
        image_size: (width, height) of the image

    Returns:
        True if the watermark would be visible
    """
    x, y = pos
    text_width, text_height = text_size
    img_width, img_height = image_size

    # Check if any part of the text would be visible
    left = x - text_width // 2
    right = x + text_width // 2
    top = y - text_height // 2
    bottom = y + text_height // 2

    return right > 0 and left < img_width and bottom > 0 and top < img_height


def apply_watermark(
    image: Image.Image,
    text: str = WatermarkDefaults.TEXT,
    font_name: str = WatermarkDefaults.FONT_NAME,
    font_size: int = WatermarkDefaults.FONT_SIZE,
    text_color: Tuple[int, int, int] = WatermarkDefaults.COLOR,
    opacity: int = WatermarkDefaults.OPACITY,
    diagonal_spacing: Optional[int] = None,
) -> Image.Image:
    """Apply a clean diagonal text watermark to an image.

    Args:
        image: The image to watermark
        text: The watermark text
        font_name: The font name for text watermarks
        font_size: The font size for text watermarks
        text_color: The text color for text watermarks (RGB)
        opacity: The opacity of the watermark (0-255)
        diagonal_spacing: Distance between watermarks diagonally (auto-calculated if None)

    Returns:
        The watermarked image

    Raises:
        ImageProcessingError: If watermarking fails
        ValueError: If parameters are invalid
    """
    try:
        # Validate inputs
        if not isinstance(image, Image.Image):
            raise ValueError("image must be a PIL Image object")

        config = WatermarkConfig(
            text=text,
            font_name=font_name,
            font_size=font_size,
            text_color=text_color,
            opacity=opacity,
            diagonal_spacing=diagonal_spacing,
        )

        # Create a copy of the image and ensure it's RGBA
        result = image.copy().convert("RGBA")
        image_size = (result.width, result.height)

        # Create transparent overlay for watermark
        overlay = Image.new("RGBA", image_size, (0, 0, 0, 0))

        # Calculate scaled font size
        scaled_font_size = _calculate_scaled_font_size(image_size, config.font_size)
        font = get_font(config.font_name, scaled_font_size)

        # Calculate spacing and positions
        spacing = _calculate_watermark_spacing(image_size, config.diagonal_spacing)
        positions = _calculate_grid_positions(image_size, spacing)

        # Pre-calculate rotated text image (reuse for all positions)
        rotated_text = _create_rotated_text_image(
            config.text, font, config.text_color, config.opacity, config.rotation_angle
        )

        # Get dimensions for visibility checking
        temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        text_dimensions = _get_text_dimensions(temp_draw, config.text, font)
        text_size = (text_dimensions[0], text_dimensions[1])  # Only width and height

        # Place watermarks at calculated positions (optimized)
        rotated_width, rotated_height = rotated_text.size
        result_width, result_height = image_size

        for x, y in positions:
            if _is_position_visible((x, y), text_size, image_size):
                paste_x = int(x - rotated_width // 2)
                paste_y = int(y - rotated_height // 2)

                # Optimized bounds check
                if (
                    -rotated_width < paste_x < result_width
                    and -rotated_height < paste_y < result_height
                ):
                    overlay.paste(rotated_text, (paste_x, paste_y), rotated_text)

        # Composite the watermark onto the original image
        result = Image.alpha_composite(result, overlay)

        return result

    except Exception as e:
        raise ImageProcessingError(f"Watermarking failed: {e}") from e


# Font handling
def get_font(
    font_name: str, size: int, fallback_names: Optional[List[str]] = None
) -> ImageFont.FreeTypeFont:
    """Get a font with the given name and size.

    Checks system fonts first, then project fonts, with fallback to default.

    Args:
        font_name: The name of the font
        size: The font size (must be positive)
        fallback_names: Optional list of fallback font names

    Returns:
        The font object (never None - falls back to default if needed)

    Raises:
        FontError: If font size is invalid
        ValueError: If font_name is empty or size is invalid
    """
    if not font_name or not isinstance(font_name, str):
        raise ValueError("font_name must be a non-empty string")

    if not isinstance(size, int) or size <= 0:
        raise FontError(f"Font size must be a positive integer, got: {size}")

    if size < ImageConstants.MIN_FONT_SIZE:
        raise FontError(
            f"Font size too small: {size}. Minimum allowed: {ImageConstants.MIN_FONT_SIZE}"
        )

    if size > ImageConstants.MAX_FONT_SIZE:
        raise FontError(
            f"Font size too large: {size}. Maximum allowed: {ImageConstants.MAX_FONT_SIZE}"
        )

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
        default_font = ImageFont.load_default()
        # Try to create a variant with the requested size if supported
        try:
            return default_font.font_variant(size=size)
        except (AttributeError, TypeError):
            # Fallback for older PIL versions or unsupported operations
            return default_font
    except Exception as e:
        # This should rarely happen, but provide a final fallback
        logging.getLogger(__name__).warning(f"Could not load default font: {e}")
        raise FontError(f"Unable to load any font: {e}") from e


# Process execution
@contextmanager
def managed_subprocess(
    command_list: List[str], cwd: Optional[str] = None, timeout: Optional[int] = None
):
    """Context manager for subprocess execution with proper cleanup.

    Args:
        command_list: Command and arguments to execute
        cwd: Working directory
        timeout: Timeout in seconds

    Yields:
        subprocess.Popen object
    """
    import subprocess

    process = None
    try:
        process = subprocess.Popen(
            command_list,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        yield process
    finally:
        if process:
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"Error cleaning up subprocess: {e}"
                )


def setup_structured_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up structured logging with better formatting and error handling.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger with structured output
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(level)

    # Create formatter with structured output
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler with color support if available
    try:
        import colorlog

        handler = colorlog.StreamHandler()
        handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    except ImportError:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

    handler.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def run_script(
    script_path: Union[str, Path],
    script_name: str,
    script_args: Optional[List[str]] = None,
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
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
