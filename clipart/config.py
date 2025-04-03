import os
from typing import Tuple, Optional, Dict

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
DEFAULT_TITLE_FONT = "Angelina"
DEFAULT_SUBTITLE_FONT = "Poppins"

# === Dimensions & Appearance ===
OUTPUT_SIZE: Tuple[int, int] = (3000, 2250)
GRID_2x2_SIZE: Tuple[int, int] = (2000, 2000)
CELL_PADDING: int = 30

# Title & Subtitle Settings
SUBTITLE_TEXT_TOP = "Commercial Use"
SUBTITLE_FONT_SIZE = 70
SUBTITLE_TEXT_COLOR: Tuple[int, int, int, int] = (80, 80, 80, 255)
SUBTITLE_SPACING: int = 25


TITLE_TEXT_COLOR: Tuple[int, int, int, int] = (50, 50, 50, 255)
TITLE_PADDING_X: int = 80
TITLE_PADDING_Y: int = 40
TITLE_MAX_FONT_SIZE: int = 200
TITLE_MIN_FONT_SIZE: int = 40
TITLE_LINE_SPACING: int = 15
TITLE_FONT_STEP: int = 5
TITLE_MAX_LINES: int = 3

# Title Backdrop & Shadow
TITLE_BACKDROP_PADDING_X: int = 60
TITLE_BACKDROP_PADDING_Y: int = 30
TITLE_BACKDROP_CORNER_RADIUS: int = 40
TITLE_BACKDROP_OPACITY: int = 255
TITLE_BACKDROP_BORDER_WIDTH: int = 5
TITLE_BACKDROP_BORDER_COLOR: Tuple[int, int, int, int] = (218, 165, 32, 255)

# Background Color
DEFAULT_BG_COLOR: Tuple[int, int, int] = (248, 248, 248)

# === Collage Layout Settings ===
COLLAGE_SURROUND_MIN_WIDTH_FACTOR: float = 0.20
COLLAGE_SURROUND_MAX_WIDTH_FACTOR: float = 0.30
COLLAGE_CENTERPIECE_SCALE_FACTOR: float = 0.65
COLLAGE_PLACEMENT_STEP: int = 5
COLLAGE_TITLE_AVOID_PADDING: int = 20
COLLAGE_CENTERPIECE_AVOID_PADDING: int = 20

COLLAGE_RESCALE_FACTOR: float = 0.95
COLLAGE_RESCALE_ATTEMPTS: int = 3
COLLAGE_MAX_ACCEPTABLE_OVERLAP_RATIO: float = 0.10
COLLAGE_MIN_SCALE_ABS: float = 0.30

# === Transparency Demo Settings ===
CHECKERBOARD_SIZE: int = 30
CHECKERBOARD_COLOR1: Tuple[int, int, int] = (255, 255, 255)
CHECKERBOARD_COLOR2: Tuple[int, int, int] = (200, 200, 200)
TRANSPARENCY_DEMO_SCALE: float = 0.7

# === Grid Appearance (2x2) ===
GRID_ITEM_SHADOW_COLOR: Tuple[int, int, int, int] = (100, 100, 100, 80)
GRID_ITEM_SHADOW_OFFSET: Tuple[int, int] = (8, 8)

# === Watermark Settings ===
WATERMARK_DEFAULT_OPACITY: int = 100
WATERMARK_TEXT: str = "digital veil"
WATERMARK_TEXT_FONT_NAME: str = "Clattering"
WATERMARK_TEXT_FONT_SIZE: int = 50
WATERMARK_TEXT_COLOR: Tuple[int, int, int] = (150, 150, 150)
WATERMARK_TEXT_ANGLE: float = 45.0
WATERMARK_TEXT_SPACING_FACTOR: float = 1.5

# === Video Settings ===
CREATE_VIDEO: bool = True
VIDEO_TARGET_SIZE: Tuple[int, int] = (2000, 2000)
VIDEO_FPS: int = 30
VIDEO_TRANSITION_FRAMES: int = 20
VIDEO_DISPLAY_FRAMES: int = 50

# === Dynamic Title Color Settings ===
USE_DYNAMIC_TITLE_COLORS = True
DYNAMIC_TITLE_CONTRAST_THRESHOLD = 4.5
DYNAMIC_TITLE_COLOR_CLUSTERS = 5

# === Main Execution Settings ===
DELETE_IDENTIFIERS_ON_START: bool = True
