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
CELL_PADDING: int = 30

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

# --- Background Settings ---
DEFAULT_BG_COLOR: Tuple[int, int, int] = (248, 248, 248)

# --- Smart Puzzle Layout Settings ---
OFFSET_GRID_MIN_PIXEL_DIM: int = 30
OFFSET_GRID_AVOID_CENTER_BOX: bool = True

# Sizing relative to canvas width
PUZZLE_MIN_WIDTH_FACTOR: float = 0.20
PUZZLE_MAX_SIZE_MULTIPLIER: float = 1.5
PUZZLE_MAX_WIDTH_FACTOR: float = 0.35

# Placement Strategy
PUZZLE_PLACEMENT_STEP: int = 5  # Smaller step for denser checking near edges
PUZZLE_MAX_OVERLAP_AREA_RATIO: float = 0.10
# Defines the size of corner/edge search regions
PUZZLE_EDGE_REGION_FACTOR: float = 0.5  # Slightly larger region (50%)
# Allow slightly more than normal, but not excessive, overlap when placing minimum size items
PUZZLE_MIN_SIZE_ACCEPTABLE_OVERLAP_RATIO: float = 0.35


# --- Rescaling Strategy ---
PUZZLE_RESCALE_ATTEMPTS: int = 6
PUZZLE_RESCALE_FACTOR: float = 0.80
PUZZLE_MIN_ABSOLUTE_SCALE: float = 0.10

# --- Simplified Grid ---
SIMPLIFIED_GRID_JITTER_FACTOR: float = 0.10
SIMPLIFIED_GRID_MIN_WIDTH_FACTOR: float = 0.25
SIMPLIFIED_GRID_MAX_SIZE_MULTIPLIER: float = 1.6

# --- Transparency Demo Settings ---
CHECKERBOARD_SIZE: int = 30
CHECKERBOARD_COLOR1: Tuple[int, int, int] = (255, 255, 255)
CHECKERBOARD_COLOR2: Tuple[int, int, int] = (200, 200, 200)
TRANSPARENCY_DEMO_SCALE: float = 0.7

# --- Grid Appearance (for 2x2) ---
GRID_ITEM_SHADOW_COLOR: Tuple[int, int, int, int] = (100, 100, 100, 80)
GRID_ITEM_SHADOW_OFFSET: Tuple[int, int] = (8, 8)

# --- Watermark Settings ---
WATERMARK_DEFAULT_OPACITY: int = 15
WATERMARK_SPACING_MULTIPLIER: int = 4
WATERMARK_SIZE_RATIO: float = 1 / 15

# --- Video Settings ---
VIDEO_TARGET_SIZE: Tuple[int, int] = (2000, 2000)
VIDEO_FPS: int = 30
VIDEO_TRANSITION_FRAMES: int = 20
VIDEO_DISPLAY_FRAMES: int = 50

# --- Main Execution Settings ---
DELETE_IDENTIFIERS_ON_START: bool = True
