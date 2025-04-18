"""
Configuration settings for pattern mockups.
"""

import os
from typing import Dict, Tuple

# === Directories & Paths ===
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# === Font Settings ===
AVAILABLE_FONTS: Dict[str, str] = {
    "Angelina": os.path.join(FONTS_DIR, "Free Version Angelina.ttf"),
    "MarkerFelt": os.path.join(FONTS_DIR, "DSMarkerFelt.ttf"),
    "Clattering": os.path.join(FONTS_DIR, "Clattering.ttf"),
    "Cravelo": os.path.join(FONTS_DIR, "Cravelo DEMO.otf"),
    "Poppins": os.path.join(FONTS_DIR, "Poppins-SemiBold.ttf"),
}

# Default font settings
DEFAULT_TITLE_FONT = "Clattering"
DEFAULT_SUBTITLE_FONT = "Poppins"
DEFAULT_TITLE_FONT_SIZE = 250  # 0 means auto-calculated based on divider height
DEFAULT_TOP_SUBTITLE_FONT_SIZE = 0  # 0 means auto-calculated based on divider height
DEFAULT_BOTTOM_SUBTITLE_FONT_SIZE = 0  # 0 means auto-calculated based on divider height

# === Color Settings ===
# Dynamic color selection settings
USE_DYNAMIC_TITLE_COLORS = True
DYNAMIC_TITLE_CONTRAST_THRESHOLD = 4.5  # WCAG AA standard for normal text
DYNAMIC_TITLE_COLOR_CLUSTERS = 5  # Number of color clusters to extract from images

# === Spacing Settings ===
# Vertical spacing between text elements
VERTICAL_SPACING = 20  # Default spacing between text elements
TITLE_BOTTOM_SUBTITLE_SPACING = 10  # Reduced spacing between title and bottom subtitle

# === Font Configuration ===
# Centralized font configuration for easy modification
FONT_CONFIG = {
    # Main font settings
    "TITLE_FONT": DEFAULT_TITLE_FONT,
    "SUBTITLE_FONT": DEFAULT_SUBTITLE_FONT,
    # Font sizes (0 means auto-calculated)
    "TITLE_FONT_SIZE": DEFAULT_TITLE_FONT_SIZE,
    "TOP_SUBTITLE_FONT_SIZE": DEFAULT_TOP_SUBTITLE_FONT_SIZE,
    "BOTTOM_SUBTITLE_FONT_SIZE": DEFAULT_BOTTOM_SUBTITLE_FONT_SIZE,
    # Color settings
    "USE_DYNAMIC_TITLE_COLORS": USE_DYNAMIC_TITLE_COLORS,
    "DYNAMIC_TITLE_CONTRAST_THRESHOLD": DYNAMIC_TITLE_CONTRAST_THRESHOLD,
    "DYNAMIC_TITLE_COLOR_CLUSTERS": DYNAMIC_TITLE_COLOR_CLUSTERS,
    # Spacing settings
    "VERTICAL_SPACING": VERTICAL_SPACING,
    "TITLE_BOTTOM_SUBTITLE_SPACING": TITLE_BOTTOM_SUBTITLE_SPACING,
}


def update_font_config(
    title_font=None,
    subtitle_font=None,
    title_font_size=None,
    top_subtitle_font_size=None,
    bottom_subtitle_font_size=None,
    use_dynamic_title_colors=None,
    dynamic_title_contrast_threshold=None,
    dynamic_title_color_clusters=None,
    vertical_spacing=None,
    title_bottom_subtitle_spacing=None,
):
    """Update font and color configuration with custom values.

    Args:
        title_font: Custom title font name
        subtitle_font: Custom subtitle font name
        title_font_size: Custom title font size (0 for auto-calculation)
        top_subtitle_font_size: Custom top subtitle font size (0 for auto-calculation)
        bottom_subtitle_font_size: Custom bottom subtitle font size (0 for auto-calculation)
        use_dynamic_title_colors: Whether to use dynamic title colors based on input image
        dynamic_title_contrast_threshold: Minimum contrast ratio for title text
        dynamic_title_color_clusters: Number of color clusters to extract from images
    """
    if title_font and title_font in AVAILABLE_FONTS:
        FONT_CONFIG["TITLE_FONT"] = title_font

    if subtitle_font and subtitle_font in AVAILABLE_FONTS:
        FONT_CONFIG["SUBTITLE_FONT"] = subtitle_font

    if title_font_size is not None:
        FONT_CONFIG["TITLE_FONT_SIZE"] = title_font_size

    if top_subtitle_font_size is not None:
        FONT_CONFIG["TOP_SUBTITLE_FONT_SIZE"] = top_subtitle_font_size

    if bottom_subtitle_font_size is not None:
        FONT_CONFIG["BOTTOM_SUBTITLE_FONT_SIZE"] = bottom_subtitle_font_size

    if use_dynamic_title_colors is not None:
        FONT_CONFIG["USE_DYNAMIC_TITLE_COLORS"] = use_dynamic_title_colors

    if dynamic_title_contrast_threshold is not None:
        FONT_CONFIG["DYNAMIC_TITLE_CONTRAST_THRESHOLD"] = (
            dynamic_title_contrast_threshold
        )

    if dynamic_title_color_clusters is not None:
        FONT_CONFIG["DYNAMIC_TITLE_COLOR_CLUSTERS"] = dynamic_title_color_clusters

    if vertical_spacing is not None:
        FONT_CONFIG["VERTICAL_SPACING"] = vertical_spacing

    if title_bottom_subtitle_spacing is not None:
        FONT_CONFIG["TITLE_BOTTOM_SUBTITLE_SPACING"] = title_bottom_subtitle_spacing
