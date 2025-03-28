# clipart/config.py
import os
from typing import Tuple, Optional, Dict

# --- Directory Configuration ---
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
OUTPUT_DIR_BASE = os.path.join(PROJECT_ROOT, "clipart_output")
ASSETS_DIR: str = os.path.join(PROJECT_ROOT, "assets")
DEFAULT_LOGO_PATH: str = os.path.join(ASSETS_DIR, "logo.png")
CANVAS_PATH: str = os.path.join(ASSETS_DIR, "canvas.png")
FONTS_DIR: str = os.path.join(ASSETS_DIR, "fonts")
AVAILABLE_FONTS: Dict[str, str] = {
    "Clattering": os.path.join(FONTS_DIR, "Clattering.ttf"),
    "Cravelo": os.path.join(FONTS_DIR, "Cravelo DEMO.otf"),
    "MarkerFelt": os.path.join(FONTS_DIR, "DSMarkerFelt.ttf"),
    "Angelina": os.path.join(FONTS_DIR, "Free Version Angelina.ttf"),
    "Poppins": os.path.join(FONTS_DIR, "Poppins-Regular.ttf"),
}
DEFAULT_TITLE_FONT: str = "Angelina"
DEFAULT_SUBTITLE_FONT: str = "Poppins"

# --- Mockup Dimensions ---
OUTPUT_SIZE: Tuple[int, int] = (3000, 2250)
GRID_2x2_SIZE: Tuple[int, int] = (2000, 2000)
CELL_PADDING: int = 30  # Used for 2x2 grid

# --- Title Bar & Text Settings ---
SUBTITLE_TEXT_TOP: str = "Commercial Use"
SUBTITLE_FONT_SIZE: int = 70
SUBTITLE_TEXT_COLOR: Tuple[int, int, int, int] = (80, 80, 80, 255)
SUBTITLE_SPACING: int = 25
TITLE_BAR_COLOR: Tuple[int, int, int, int] = (255, 255, 255, 255)
TITLE_BAR_GRADIENT: Optional[
    Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]
] = ((245, 245, 245, 255), (255, 255, 255, 255))
TITLE_BAR_OPACITY: int = 235
TITLE_TEXT_COLOR: Tuple[int, int, int, int] = (50, 50, 50, 255)
TITLE_PADDING_X: int = 80
TITLE_PADDING_Y: int = 40
TITLE_MAX_FONT_SIZE: int = 240
TITLE_MIN_FONT_SIZE: int = 40
TITLE_LINE_SPACING: int = 15
TITLE_FONT_STEP: int = 5
TITLE_MAX_LINES: int = 3
TITLE_BACKDROP_PADDING_X: int = 60
TITLE_BACKDROP_PADDING_Y: int = 30
TITLE_BACKDROP_CORNER_RADIUS: int = 40
TITLE_BACKDROP_SHADOW_ENABLE: bool = True  # Easily turn on/off
TITLE_BACKDROP_SHADOW_OFFSET: Tuple[int, int] = (15, 15)  # (x, y) offset
TITLE_BACKDROP_SHADOW_COLOR: Tuple[int, int, int, int] = (
    0,
    0,
    0,
    255,
)  # RGBA, default black
TITLE_BACKDROP_SHADOW_OPACITY: int = 255  # Opacity of the shadow itself (0-255)

# --- Background Settings ---
DEFAULT_BG_COLOR: Tuple[int, int, int] = (248, 248, 248)

# --- Collage Layout Settings --- (Centerpiece Focus)
# Sizing for surrounding items (relative to canvas width)
COLLAGE_SURROUND_MIN_WIDTH_FACTOR: float = 0.20  # Min size for surrounding items
COLLAGE_SURROUND_MAX_WIDTH_FACTOR: float = (
    0.30  # Max size for surrounding items (can be random between min/max)
)
# Centerpiece Sizing
COLLAGE_CENTERPIECE_SCALE_FACTOR: float = (
    0.65  # Size relative to canvas width/height (use min of w/h?)
)

# Placement & Avoidance
COLLAGE_PLACEMENT_STEP: int = (
    5  # Step size for scanning placement positions (smaller is more precise)
)
COLLAGE_TITLE_AVOID_PADDING: int = 20  # Extra padding around title box
COLLAGE_CENTERPIECE_AVOID_PADDING: int = 20  # Extra padding around centerpiece bounds

# Overlap & Rescaling for surrounding items
COLLAGE_RESCALE_FACTOR: float = (
    0.95  # Factor to shrink surrounding items if overlap is too high
)
COLLAGE_RESCALE_ATTEMPTS: int = 3  # Max times to try shrinking a surrounding item
COLLAGE_MAX_ACCEPTABLE_OVERLAP_RATIO: float = (
    0.10  # Overlap ratio (vs item area) above which shrinking is triggered
)
COLLAGE_MIN_SCALE_ABS: float = (
    0.30  # Absolute minimum scale factor relative to original image size (for surrounding items)
)

# --- Transparency Demo Settings ---
CHECKERBOARD_SIZE: int = 30
CHECKERBOARD_COLOR1: Tuple[int, int, int] = (255, 255, 255)
CHECKERBOARD_COLOR2: Tuple[int, int, int] = (200, 200, 200)
TRANSPARENCY_DEMO_SCALE: float = 0.7

# --- Grid Appearance (for 2x2) ---
GRID_ITEM_SHADOW_COLOR: Tuple[int, int, int, int] = (100, 100, 100, 80)
GRID_ITEM_SHADOW_OFFSET: Tuple[int, int] = (8, 8)

# --- Watermark Settings ---
WATERMARK_DEFAULT_OPACITY: int = 100  # General opacity
WATERMARK_TEXT: str = "digital veil"
WATERMARK_TEXT_FONT_NAME: str = "Clattering"  # Choose an available font
WATERMARK_TEXT_FONT_SIZE: int = 50
WATERMARK_TEXT_COLOR: Tuple[int, int, int] = (
    150,
    150,
    150,
)  # Base color (opacity applied later)
WATERMARK_TEXT_ANGLE: float = 45.0  # Angle in degrees
WATERMARK_TEXT_SPACING_FACTOR: float = (
    1.5  # Multiplier for spacing based on text block size
)

# --- Video Settings ---
VIDEO_TARGET_SIZE: Tuple[int, int] = (2000, 2000)
VIDEO_FPS: int = 30
VIDEO_TRANSITION_FRAMES: int = 20
VIDEO_DISPLAY_FRAMES: int = 50

# --- Main Execution Settings ---
DELETE_IDENTIFIERS_ON_START: bool = True
