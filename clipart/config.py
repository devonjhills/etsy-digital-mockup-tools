import os
from typing import Tuple, Dict

# === Directories & Paths ===
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
OUTPUT_DIR_BASE = os.path.join(PROJECT_ROOT, "clipart_output")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
DEFAULT_LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
CANVAS_PATH = os.path.join(ASSETS_DIR, "canvas.png")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
AVAILABLE_FONTS: Dict[str, str] = {
    "Clattering": os.path.join(FONTS_DIR, "Clattering.ttf"),
    "Cravelo": os.path.join(FONTS_DIR, "Cravelo DEMO.otf"),
    "MarkerFelt": os.path.join(FONTS_DIR, "DSMarkerFelt.ttf"),
    "Angelina": os.path.join(FONTS_DIR, "Free Version Angelina.ttf"),
    "Poppins": os.path.join(FONTS_DIR, "Poppins-SemiBold.ttf"),
}
DEFAULT_TITLE_FONT = "Clattering"
DEFAULT_SUBTITLE_FONT = "Poppins"

# === Dimensions & Appearance ===
OUTPUT_SIZE: Tuple[int, int] = (3000, 2250)
GRID_2x2_SIZE: Tuple[int, int] = (2000, 2000)
CELL_PADDING: int = 30

# Title & Subtitle Settings
# Top subtitle is a format string that will be populated with num_images at runtime
SUBTITLE_TEXT_TOP = "{num_images} clip arts • Commercial Use"
# Bottom subtitle format string that will be populated with num_images at runtime
SUBTITLE_BOTTOM_TEXT_FORMAT = "300 DPI • Transparent PNG"
SUBTITLE_FONT_SIZE = 60
SUBTITLE_TEXT_COLOR: Tuple[int, int, int, int] = (80, 80, 80, 255)
SUBTITLE_SPACING: int = 35


TITLE_TEXT_COLOR: Tuple[int, int, int, int] = (50, 50, 50, 255)
TITLE_PADDING_X: int = 80
TITLE_PADDING_Y: int = 40
TITLE_MAX_FONT_SIZE: int = 250
TITLE_MIN_FONT_SIZE: int = 40
TITLE_LINE_SPACING: int = 15
TITLE_FONT_STEP: int = 5
TITLE_MAX_LINES: int = 3

# Background Color
DEFAULT_BG_COLOR: Tuple[int, int, int] = (248, 248, 248)


# === Collage Layout Settings ===
COLLAGE_SURROUND_MIN_WIDTH_FACTOR: float = 0.25
COLLAGE_SURROUND_MAX_WIDTH_FACTOR: float = 0.40
COLLAGE_CENTERPIECE_SCALE_FACTOR: float = 0.90
COLLAGE_PLACEMENT_STEP: int = 10
COLLAGE_TITLE_AVOID_PADDING: int = 20
COLLAGE_CENTERPIECE_AVOID_PADDING: int = 10

COLLAGE_RESCALE_FACTOR: float = 0.95
COLLAGE_RESCALE_ATTEMPTS: int = 3
COLLAGE_MAX_ACCEPTABLE_OVERLAP_RATIO: float = 0.30
COLLAGE_MIN_SCALE_ABS: float = 0.30

# === Transparency Demo Settings ===
CHECKERBOARD_SIZE: int = 30
CHECKERBOARD_COLOR1: Tuple[int, int, int] = (255, 255, 255)
CHECKERBOARD_COLOR2: Tuple[int, int, int] = (200, 200, 200)
TRANSPARENCY_DEMO_SCALE: float = 0.7


# === Watermark Settings ===
WATERMARK_DEFAULT_OPACITY: int = 100
WATERMARK_TEXT: str = "digital veil"
WATERMARK_TEXT_FONT_NAME: str = "Clattering"
WATERMARK_TEXT_FONT_SIZE: int = 50
WATERMARK_TEXT_COLOR: Tuple[int, int, int] = (150, 150, 150)
WATERMARK_TEXT_ANGLE: float = 45.0
WATERMARK_TEXT_SPACING_FACTOR: float = 2.5

# === Video Settings ===
CREATE_VIDEO: bool = True
VIDEO_TARGET_SIZE: Tuple[int, int] = (2000, 2000)
VIDEO_FPS: int = 30
VIDEO_TRANSITION_FRAMES: int = 20
VIDEO_DISPLAY_FRAMES: int = 50


# === Main Execution Settings ===
DELETE_IDENTIFIERS_ON_START: bool = True

# === Font Configuration ===
# Centralized font configuration for easy modification
FONT_CONFIG = {
    # Main font settings
    "TITLE_FONT": DEFAULT_TITLE_FONT,  # Default title font
    "SUBTITLE_FONT": DEFAULT_SUBTITLE_FONT,  # Default subtitle font
    # Font sizes
    "TITLE_MAX_FONT_SIZE": TITLE_MAX_FONT_SIZE,
    "TITLE_MIN_FONT_SIZE": TITLE_MIN_FONT_SIZE,
    "SUBTITLE_FONT_SIZE": SUBTITLE_FONT_SIZE,
    # Font spacing
    "TITLE_LINE_SPACING": TITLE_LINE_SPACING,
    "SUBTITLE_SPACING": SUBTITLE_SPACING,
    # Font colors
    "TITLE_TEXT_COLOR": TITLE_TEXT_COLOR,
    "SUBTITLE_TEXT_COLOR": SUBTITLE_TEXT_COLOR,
}


# Function to update font configuration
def update_font_config(
    title_font=None,
    subtitle_font=None,
    title_max_size=None,
    title_min_size=None,
    subtitle_size=None,
    subtitle_spacing=None,
    title_line_spacing=None,
):
    """Update font configuration with custom values.

    Args:
        title_font: Custom title font name
        subtitle_font: Custom subtitle font name
        title_max_size: Custom maximum title font size
        title_min_size: Custom minimum title font size
        subtitle_size: Custom subtitle font size
        subtitle_spacing: Custom spacing between title and subtitles
        title_line_spacing: Custom spacing between title lines
    """
    if title_font:
        FONT_CONFIG["TITLE_FONT"] = title_font
    if subtitle_font:
        FONT_CONFIG["SUBTITLE_FONT"] = subtitle_font
    if title_max_size:
        FONT_CONFIG["TITLE_MAX_FONT_SIZE"] = title_max_size
    if title_min_size:
        FONT_CONFIG["TITLE_MIN_FONT_SIZE"] = title_min_size
    if subtitle_size:
        FONT_CONFIG["SUBTITLE_FONT_SIZE"] = subtitle_size
    if subtitle_spacing:
        FONT_CONFIG["SUBTITLE_SPACING"] = subtitle_spacing
    if title_line_spacing:
        FONT_CONFIG["TITLE_LINE_SPACING"] = title_line_spacing


# === Title Style Arguments ===
# These arguments are passed to the add_title_bar_and_text function
# Include both parameter names to support both implementations
TITLE_STYLE_ARGS = {
    # Font names
    "font_name": FONT_CONFIG["TITLE_FONT"],  # For image_processing.py
    "title_font_name": FONT_CONFIG["TITLE_FONT"],  # For processing/title.py
    "subtitle_font_name": FONT_CONFIG["SUBTITLE_FONT"],
    # Font sizes
    "max_font_size": FONT_CONFIG["TITLE_MAX_FONT_SIZE"],  # For image_processing.py
    "title_max_font_size": FONT_CONFIG[
        "TITLE_MAX_FONT_SIZE"
    ],  # For processing/title.py
    "min_font_size": FONT_CONFIG["TITLE_MIN_FONT_SIZE"],  # For image_processing.py
    "title_min_font_size": FONT_CONFIG[
        "TITLE_MIN_FONT_SIZE"
    ],  # For processing/title.py
    # Line spacing and steps
    "line_spacing": FONT_CONFIG["TITLE_LINE_SPACING"],  # For image_processing.py
    "title_line_spacing": FONT_CONFIG["TITLE_LINE_SPACING"],  # For processing/title.py
    "font_step": TITLE_FONT_STEP,  # For image_processing.py
    "title_font_step": TITLE_FONT_STEP,  # For processing/title.py
    "max_lines": TITLE_MAX_LINES,  # For image_processing.py
    "title_max_lines": TITLE_MAX_LINES,  # For processing/title.py
    # Padding
    "padding_x": TITLE_PADDING_X,  # For image_processing.py
    "title_padding_x": TITLE_PADDING_X,  # For processing/title.py
    "title_padding_y": TITLE_PADDING_Y,  # For processing/title.py
    # Subtitle settings
    "subtitle_spacing": FONT_CONFIG["SUBTITLE_SPACING"],
    "subtitle_font_size": FONT_CONFIG["SUBTITLE_FONT_SIZE"],
    # Colors
    "text_color": FONT_CONFIG["TITLE_TEXT_COLOR"],
    "subtitle_text_color": FONT_CONFIG["SUBTITLE_TEXT_COLOR"],
}
