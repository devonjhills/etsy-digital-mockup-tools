"""Unified configuration management for all product types."""

import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from src.utils.common import setup_logging

logger = setup_logging(__name__)

# Import YAML conditionally
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logger.warning(
        "PyYAML not installed. YAML configuration files will not be supported."
    )


# Global font configuration
def get_available_fonts() -> Dict[str, str]:
    """Get available fonts - use project fonts directly."""
    project_root = Path(__file__).parent.parent.parent  # Go up to project root from src/core/
    assets_dir = project_root / "assets"
    fonts_dir = assets_dir / "fonts"

    return {
        # Use Angelina (fancy script) as the main title font
        "GreatVibes-Regular": str(fonts_dir / "Free Version Angelina.ttf"),
        # Use Poppins for subtitles (clean, readable)
        "LibreBaskerville-Italic": str(fonts_dir / "Poppins-SemiBold.ttf"),
        # Project fonts
        "Clattering": str(fonts_dir / "Clattering.ttf"),
        "Cravelo": str(fonts_dir / "Cravelo DEMO.otf"),
        "MarkerFelt": str(fonts_dir / "DSMarkerFelt.ttf"),
        "Angelina": str(fonts_dir / "Free Version Angelina.ttf"),
        "Poppins": str(fonts_dir / "Poppins-SemiBold.ttf"),
    }


# Global path configuration
def get_project_paths() -> Dict[str, Path]:
    """Get standardized project paths."""
    project_root = Path(__file__).parent.parent
    return {
        "project_root": project_root,
        "assets_dir": project_root / "assets",
        "fonts_dir": project_root / "assets" / "fonts",
        "input_dir": project_root / "input",
        "canvas_path": project_root / "assets" / "canvas.png",
        "logo_path": project_root / "assets" / "logo.png",
    }


@dataclass
class ProductTypeConfig:
    """Configuration for a specific product type."""

    name: str
    display_name: str
    processor_class: str
    default_workflow_steps: list = field(default_factory=list)

    # Processing settings
    resize_settings: Dict[str, Any] = field(default_factory=dict)
    mockup_settings: Dict[str, Any] = field(default_factory=dict)
    video_settings: Dict[str, Any] = field(default_factory=dict)

    # Typography settings
    font_settings: Dict[str, Any] = field(default_factory=dict)
    color_settings: Dict[str, Any] = field(default_factory=dict)
    layout_settings: Dict[str, Any] = field(default_factory=dict)

    # External integrations
    etsy_settings: Dict[str, Any] = field(default_factory=dict)
    ai_prompts: Dict[str, str] = field(default_factory=dict)

    # Extensibility
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages configuration for all product types."""

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__), "..", "config", "product_types"
            )

        self.config_dir = Path(config_dir)
        self.configs: Dict[str, ProductTypeConfig] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """Load all product type configurations."""
        # Load built-in configurations first
        self._load_builtin_configs()

        # Then load any YAML configurations if the directory exists
        if self.config_dir.exists():
            self._load_yaml_configs()

    def _load_builtin_configs(self):
        """Load built-in configurations for existing product types."""

        # Pattern configuration
        pattern_config = ProductTypeConfig(
            name="pattern",
            display_name="Seamless Patterns",
            processor_class="processors.pattern_processor.PatternProcessor",
            default_workflow_steps=["resize", "mockup", "video", "zip"],
            resize_settings={
                "max_size": 3600,
                "format": "png",
                "maintain_aspect": True,
            },
            mockup_settings={
                "create_main": True,
                "create_grid": True,
                "create_layered": True,
                "use_dynamic_colors": True,
            },
            font_settings={
                "title_font": "GreatVibes-Regular",
                "subtitle_font": "LibreBaskerville-Italic",
                "title_font_size": 250,
                "top_subtitle_font_size": 90,  # Increased from auto-calc (~75)
                "bottom_subtitle_font_size": 80,  # Increased from auto-calc (~60)
                "available_fonts": get_available_fonts(),
            },
            color_settings={
                "use_dynamic_title_colors": True,
                "dynamic_title_contrast_threshold": 4.5,  # WCAG AA standard
                "dynamic_title_color_clusters": 5,
            },
            layout_settings={"top_subtitle_padding": 85, "bottom_subtitle_padding": 85},
            video_settings={
                "fps": 30,
                "duration_per_image": 2.0,
                "target_size": [1080, 1080],
            },
            etsy_settings={
                "category": "Digital",
                "subcategory": "Patterns",
                "default_tags": [
                    "seamless pattern",
                    "digital pattern",
                    "printable",
                    "commercial use",
                ],
            },
            ai_prompts={
                "title": "Analyze this seamless pattern and create a compelling Etsy listing title under 140 characters.",
                "description": "Create a detailed Etsy listing description for this seamless pattern including style, colors, uses, and technical details.",
                "tags": "Generate 13 relevant Etsy tags for this seamless pattern focusing on style, colors, and applications.",
            },
        )

        # Clipart configuration
        clipart_config = ProductTypeConfig(
            name="clipart",
            display_name="Clipart & Illustrations",
            processor_class="processors.clipart_processor.ClipartProcessor",
            default_workflow_steps=["resize", "mockup", "video", "zip"],
            resize_settings={
                "max_size": 1500,
                "format": "png",
                "preserve_transparency": True,
            },
            mockup_settings={
                "create_square": True,
                "create_grid": True,
                "create_transparency_demo": True,
                "grid_size": [2, 2],
                "output_size": (3000, 2250),
                "grid_2x2_size": (2000, 2000),
                "cell_padding": 30,
            },
            font_settings={
                "title_font": "GreatVibes-Regular",
                "subtitle_font": "LibreBaskerville-Italic",
                "title_max_font_size": 250,
                "title_min_font_size": 40,
                "subtitle_font_size": 85,
                "title_padding_x": 80,
                "title_padding_y": 40,
                "title_line_spacing": 15,
                "title_font_step": 5,
                "title_max_lines": 3,
                "available_fonts": get_available_fonts(),
            },
            color_settings={
                "title_text_color": (50, 50, 50, 255),
                "subtitle_text_color": (80, 80, 80, 255),
                "background_color": (248, 248, 248),
                "checkerboard_color1": (255, 255, 255),
                "checkerboard_color2": (200, 200, 200),
            },
            layout_settings={
                "subtitle_text_top": "{num_images} clip arts • Commercial Use",
                "subtitle_bottom_text": '300 DPI • 5" • Transparent PNG',
                "subtitle_spacing": 35,
                "checkerboard_size": 30,
                "transparency_demo_scale": 0.7,
            },
            video_settings={
                "fps": 30,
                "duration_per_image": 2.5,
                "target_size": [1080, 1080],
                "create_video": True,
            },
            etsy_settings={
                "category": "Digital",
                "subcategory": "Clipart",
                "shop_section": "→ CLIP ART",
                "default_tags": [
                    "clipart",
                    "digital clipart",
                    "png",
                    "transparent",
                    "commercial use",
                ],
            },
            ai_prompts={
                "title": "Analyze this clipart/illustration and create a compelling Etsy listing title under 140 characters.",
                "description": "Create a detailed Etsy listing description for this clipart set including style, uses, and technical details.",
                "tags": "Generate 13 relevant Etsy tags for this clipart focusing on subject matter, style, and applications.",
            },
        )

        # Journal papers configuration
        journal_papers_config = ProductTypeConfig(
            name="journal_papers",
            display_name="Journal Papers",
            processor_class="src.products.journal_papers.processor.JournalPapersProcessor",
            default_workflow_steps=["resize", "mockup", "video", "zip"],
            resize_settings={
                "target_width": 2550,  # 8.5 inches at 300 DPI
                "target_height": 3300,  # 11 inches at 300 DPI
                "format": "jpg",
                "dpi": 300,
                "quality": 95,
            },
            mockup_settings={
                "create_grid": True,
                "create_single_page": True,
                "page_size": "8.5x11",
                "orientation": "portrait",
            },
            font_settings={
                "title_font": "GreatVibes-Regular",
                "subtitle_font": "LibreBaskerville-Italic",
                "title_font_size": 250,
                "top_subtitle_font_size": 90,  # Larger subtitle text
                "bottom_subtitle_font_size": 80,  # Larger subtitle text
                "available_fonts": get_available_fonts(),
            },
            color_settings={
                "background_color": (
                    255,
                    255,
                    255,
                ),  # White background for journal papers
                "border_color": (240, 240, 240),
            },
            layout_settings={"top_subtitle_padding": 85, "bottom_subtitle_padding": 85},
            video_settings={
                "fps": 30,
                "duration_per_image": 2.5,
                "target_size": [1080, 1350],  # Portrait aspect ratio
            },
            etsy_settings={
                "category": "Digital",
                "subcategory": "Journal Pages",
                "default_tags": [
                    "journal pages",
                    "printable",
                    "planner",
                    "digital download",
                    "8.5x11",
                ],
            },
            ai_prompts={
                "title": "Analyze this journal page design and create a compelling Etsy listing title under 140 characters for digital journal pages.",
                "description": "Create a detailed Etsy listing description for these digital journal pages including design style, size (8.5x11), uses, and technical details.",
                "tags": "Generate 13 relevant Etsy tags for these digital journal pages focusing on journaling, planning, and design themes.",
            },
        )

        # Border clipart configuration
        border_clipart_config = ProductTypeConfig(
            name="border_clipart",
            display_name="Border Clip Arts",
            processor_class="src.products.border_clipart.processor.BorderClipartProcessor",
            default_workflow_steps=["resize", "mockup", "video", "zip"],
            resize_settings={
                "max_size": 1500,
                "format": "png",
                "preserve_transparency": True,
                "dpi": 300,
            },
            mockup_settings={
                "create_horizontal_seamless": True,
                "create_grid": True,
                "create_transparency_demo": True,
                "rows": 3,
                "grid_size": [2, 2],
                "output_size": (3000, 2250),
                "grid_2x2_size": (2000, 2000),
                "cell_padding": 30,
            },
            font_settings={
                "title_font": "GreatVibes-Regular",
                "subtitle_font": "LibreBaskerville-Italic",
                "title_max_font_size": 250,
                "title_min_font_size": 40,
                "subtitle_font_size": 85,
                "title_padding_x": 80,
                "title_padding_y": 40,
                "title_line_spacing": 15,
                "title_font_step": 5,
                "title_max_lines": 3,
                "available_fonts": get_available_fonts(),
            },
            color_settings={
                "title_text_color": (50, 50, 50, 255),
                "subtitle_text_color": (80, 80, 80, 255),
                "background_color": (248, 248, 248),
                "checkerboard_color1": (255, 255, 255),
                "checkerboard_color2": (200, 200, 200),
            },
            layout_settings={
                "subtitle_text_top": "Seamless Borders Cliparts",
                "subtitle_bottom_text": "transparent png  |  300 dpi  |  commercial use",
                "subtitle_spacing": 35,
                "checkerboard_size": 30,
                "transparency_demo_scale": 0.7,
            },
            video_settings={
                "fps": 30,
                "duration_per_image": 2.5,
                "target_size": [1080, 1080],
                "create_video": True,
            },
            etsy_settings={
                "category": "Digital",
                "subcategory": "Border Clipart",
                "shop_section": "BORDER CLIP ARTS",
                "default_tags": [
                    "border clipart",
                    "seamless border",
                    "digital border",
                    "png",
                    "transparent",
                    "commercial use",
                ],
            },
            ai_prompts={
                "title": "Analyze this seamless border clipart and create a compelling Etsy listing title under 140 characters emphasizing the horizontal seamless nature.",
                "description": "Create a detailed Etsy listing description for this seamless border clipart set including seamless tiling, style, uses, and technical details (300 DPI, transparent PNG).",
                "tags": "Generate 13 relevant Etsy tags for this seamless border clipart focusing on borders, seamless patterns, digital design, and applications.",
            },
        )

        self.configs["pattern"] = pattern_config
        self.configs["clipart"] = clipart_config
        self.configs["border_clipart"] = border_clipart_config
        self.configs["journal_papers"] = journal_papers_config

    def _load_yaml_configs(self):
        """Load configurations from YAML files."""
        if not HAS_YAML:
            logger.debug("YAML not available, skipping YAML configuration loading")
            return

        try:
            for yaml_file in self.config_dir.glob("*.yaml"):
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)

                config = ProductTypeConfig(**data)
                self.configs[config.name] = config

                logger.info(f"Loaded configuration for product type: {config.name}")

        except Exception as e:
            logger.error(f"Error loading YAML configurations: {e}")

    def get_config(self, product_type: str) -> Optional[ProductTypeConfig]:
        """Get configuration for a product type."""
        return self.configs.get(product_type)

    def list_product_types(self) -> list[str]:
        """List all available product types."""
        return list(self.configs.keys())

    def add_config(self, config: ProductTypeConfig):
        """Add a new product type configuration."""
        self.configs[config.name] = config

    def save_config_to_yaml(self, product_type: str, filename: str = None):
        """Save a configuration to a YAML file."""
        config = self.get_config(product_type)
        if not config:
            raise ValueError(f"Product type '{product_type}' not found")

        if filename is None:
            filename = f"{product_type}.yaml"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = self.config_dir / filename

        # Convert dataclass to dict
        config_dict = {
            "name": config.name,
            "display_name": config.display_name,
            "processor_class": config.processor_class,
            "default_workflow_steps": config.default_workflow_steps,
            "resize_settings": config.resize_settings,
            "mockup_settings": config.mockup_settings,
            "video_settings": config.video_settings,
            "etsy_settings": config.etsy_settings,
            "ai_prompts": config.ai_prompts,
            "custom_settings": config.custom_settings,
        }

        if not HAS_YAML:
            raise RuntimeError(
                "PyYAML is required to save YAML configurations. Install with: pip install PyYAML"
            )

        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

        logger.info(f"Saved configuration for {product_type} to {yaml_path}")

    def get_ai_prompt(self, product_type: str, prompt_type: str) -> str:
        """Get an AI prompt for a specific product type and prompt type."""
        config = self.get_config(product_type)
        if not config:
            return ""

        return config.ai_prompts.get(prompt_type, "")

    def get_workflow_steps(self, product_type: str, custom_steps: list = None) -> list:
        """Get workflow steps for a product type."""
        config = self.get_config(product_type)
        if not config:
            return []

        return custom_steps or config.default_workflow_steps

    def get_resize_settings(self, product_type: str) -> Dict[str, Any]:
        """Get resize settings for a product type."""
        config = self.get_config(product_type)
        if not config:
            return {}

        return config.resize_settings

    def get_mockup_settings(self, product_type: str) -> Dict[str, Any]:
        """Get mockup settings for a product type."""
        config = self.get_config(product_type)
        if not config:
            return {}

        return config.mockup_settings

    def get_font_settings(self, product_type: str) -> Dict[str, Any]:
        """Get font settings for a product type."""
        config = self.get_config(product_type)
        if not config:
            return {}

        return config.font_settings

    def get_color_settings(self, product_type: str) -> Dict[str, Any]:
        """Get color settings for a product type."""
        config = self.get_config(product_type)
        if not config:
            return {}

        return config.color_settings

    def get_layout_settings(self, product_type: str) -> Dict[str, Any]:
        """Get layout settings for a product type."""
        config = self.get_config(product_type)
        if not config:
            return {}

        return config.layout_settings


# Global configuration manager instance
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager
