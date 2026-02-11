"""
Pinterest-Optimized Vertical Mockup Generator
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from src.utils.common import setup_logging, get_font

logger = setup_logging(__name__)
from src.utils.color_utils import extract_colors_from_images
from src.utils.image_utils import resize_image


class PinterestMockupGenerator:
    """Generate Pinterest-optimized vertical mockups (1000x1500px)"""

    # Pinterest optimal dimensions
    PINTEREST_WIDTH = 1000
    PINTEREST_HEIGHT = 1500

    # Layout sections (y-coordinates)
    HEADER_HEIGHT = 120
    HERO_START = 120
    HERO_HEIGHT = 680
    FEATURES_START = 800
    FEATURES_HEIGHT = 400
    CTA_START = 1200
    CTA_HEIGHT = 150
    FOOTER_START = 1350
    FOOTER_HEIGHT = 150

    def __init__(self):
        self.assets_dir = Path("assets")
        self.fonts_dir = self.assets_dir / "fonts"

        # Brand settings
        self.brand_name = "Digital Veil"

        # Load background assets and logo
        self._load_background_assets()
        self._load_logo()

    def _load_background_assets(self):
        """Load and prepare background assets"""
        try:
            # Load main background
            canvas_path = self.assets_dir / "canvas.png"
            if canvas_path.exists():
                self.canvas_bg = Image.open(canvas_path).convert("RGBA")
            else:
                self.canvas_bg = None

            # Load overlay assets
            overlay_path = self.assets_dir / "overlay.png"
            if overlay_path.exists():
                self.overlay = Image.open(overlay_path).convert("RGBA")
            else:
                self.overlay = None

            logger.info("📱 Pinterest mockup assets loaded")

        except Exception as e:
            logger.warning(f"⚠️ Pinterest background assets not loaded: {e}")
            self.canvas_bg = None
            self.overlay = None

    def _load_logo(self):
        """Load and prepare logo for branding"""
        try:
            logo_path = self.assets_dir / "logo.png"
            if logo_path.exists():
                self.logo = Image.open(logo_path).convert("RGBA")
                logger.info("📱 Digital Veil logo loaded")
            else:
                self.logo = None
                logger.warning("⚠️ Logo not found at assets/logo.png")

        except Exception as e:
            logger.warning(f"⚠️ Logo loading failed: {e}")
            self.logo = None

    def create_pinterest_mockup(
        self, product_images: List[str], product_data: Dict[str, Any], output_path: str
    ) -> bool:
        """
        Create Pinterest-optimized vertical mockup

        Args:
            product_images: List of product image paths
            product_data: Product information (title, description, type, etc.)
            output_path: Where to save the Pinterest mockup

        Returns:
            bool: Success status
        """
        try:
            # Create main canvas
            canvas = Image.new(
                "RGBA",
                (self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT),
                (255, 255, 255, 255),
            )

            # Store product type for background creation
            self._current_product_type = product_data.get("product_type", "generic")

            # Extract colors from product images for dynamic theming
            main_colors = self._extract_product_colors(product_images)

            # Create background (with tiled pattern for pattern products)
            canvas = self._create_background(canvas, main_colors, product_images)

            # Add header section
            canvas = self._add_header_section(canvas, product_data, main_colors)

            # Add main product showcase
            canvas = self._add_hero_section(
                canvas, product_images, product_data, main_colors
            )

            # Add features section
            canvas = self._add_features_section(canvas, product_data, main_colors)

            # Add call-to-action section
            canvas = self._add_cta_section(canvas, product_data, main_colors)

            # Add footer/branding
            canvas = self._add_footer_section(canvas, main_colors)

            # Save final mockup
            canvas = canvas.convert("RGB")  # Convert to RGB for saving as JPEG/PNG
            canvas.save(output_path, "PNG", quality=95, optimize=True)

            logger.info(f"✅ Pinterest mockup created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error creating Pinterest mockup: {e}")
            return False

    def _extract_product_colors(
        self, product_images: List[str]
    ) -> Dict[str, Tuple[int, int, int]]:
        """Extract dominant colors from product images for theming"""
        try:
            if not product_images:
                return self._get_default_colors()

            # Use first available image for color extraction
            main_image_path = None
            for img_path in product_images:
                if os.path.exists(img_path):
                    main_image_path = img_path
                    break

            if not main_image_path:
                return self._get_default_colors()

            # Extract colors using existing utility
            colors = extract_colors_from_images([main_image_path], num_colors=5)

            if colors:
                # Get the dominant color but ensure we have good contrast
                primary_color = colors[0] if len(colors) > 0 else (51, 51, 51)
                secondary_color = colors[1] if len(colors) > 1 else (102, 102, 102)
                accent_color = colors[2] if len(colors) > 2 else (204, 204, 204)

                # Create high-contrast color scheme for text legibility
                return {
                    "primary": primary_color,  # Keep original for accents
                    "secondary": secondary_color,  # Keep original for accents
                    "accent": accent_color,  # Keep original for accents
                    "text_dark": (30, 30, 30),  # Dark gray instead of pure black
                    "text_light": (255, 255, 255),  # Pure white
                    "background": (248, 248, 248),  # Very light gray background
                    "badge_bg": (255, 255, 255),  # White badges for contrast
                    "badge_text": (30, 30, 30),  # Dark text on white badges
                    "button_bg": (76, 128, 92),  # Dark pastel green for CTA button
                    "button_text": (255, 255, 255),  # White text on dark green button
                }

            return self._get_default_colors()

        except Exception as e:
            logger.warning(f"⚠️ Color extraction failed, using defaults: {e}")
            return self._get_default_colors()

    def _get_default_colors(self) -> Dict[str, Tuple[int, int, int]]:
        """Get default color scheme with high contrast for legibility"""
        return {
            "primary": (51, 51, 51),  # Dark charcoal
            "secondary": (102, 102, 102),  # Medium gray
            "accent": (204, 204, 204),  # Light gray
            "text_dark": (30, 30, 30),  # Dark gray text
            "text_light": (255, 255, 255),  # Pure white
            "background": (248, 248, 248),  # Very light gray
            "badge_bg": (255, 255, 255),  # White badges for contrast
            "badge_text": (30, 30, 30),  # Dark text on white badges
            "button_bg": (76, 128, 92),  # Dark pastel green for CTA button
            "button_text": (255, 255, 255),  # White button text
        }

    def _ensure_contrast(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Ensure color has good contrast for text overlays"""
        r, g, b = color

        # Calculate luminance
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        # If color is too light, darken it. If too dark, keep it dark for contrast
        if luminance > 0.7:  # Too light
            # Darken the color
            factor = 0.3  # Darken by 70%
            return (int(r * factor), int(g * factor), int(b * factor))
        elif luminance < 0.2:  # Very dark, good for contrast
            return color
        else:  # Medium luminance, darken for better contrast
            factor = 0.5
            return (int(r * factor), int(g * factor), int(b * factor))

    def _get_contrast_text(
        self, background_color: Tuple[int, int, int]
    ) -> Tuple[int, int, int]:
        """Get contrasting text color for a given background"""
        r, g, b = background_color
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        # If background is light, use dark text. If dark, use light text
        if luminance > 0.5:
            return (30, 30, 30)  # Dark text
        else:
            return (255, 255, 255)  # Light text

    def _create_background(
        self,
        canvas: Image.Image,
        colors: Dict[str, Tuple[int, int, int]],
        product_images: List[str] = None,
    ) -> Image.Image:
        """Create Pinterest mockup background with optional tiled pattern"""
        try:
            # For patterns, create a tiled background. For others, use solid color
            product_type = getattr(self, "_current_product_type", None)

            if product_type == "pattern" and product_images:
                return self._create_tiled_pattern_background(
                    canvas, product_images, colors
                )
            else:
                return self._create_solid_background(canvas, colors)

        except Exception as e:
            logger.warning(f"⚠️ Background creation error: {e}")
            return self._create_solid_background(canvas, colors)

    def _create_tiled_pattern_background(
        self,
        canvas: Image.Image,
        product_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Create a beautiful tiled pattern background"""
        try:
            # Find a pattern image to tile
            pattern_image_path = None
            for img_path in product_images:
                if os.path.exists(img_path) and not img_path.endswith(
                    ("_mockup.png", "_grid.png")
                ):
                    pattern_image_path = img_path
                    break

            if not pattern_image_path:
                return self._create_solid_background(canvas, colors)

            # Load pattern image
            pattern_img = Image.open(pattern_image_path).convert("RGBA")

            # Create a tiled background with subtle opacity
            tile_size = 200  # Smaller tiles for background

            # Calculate how many tiles we need
            tiles_x = (self.PINTEREST_WIDTH // tile_size) + 2
            tiles_y = (self.PINTEREST_HEIGHT // tile_size) + 2

            # Resize pattern to tile size
            pattern_tile = resize_image(pattern_img, tile_size, tile_size)

            # Create lighter overlay for better pattern visibility
            overlay = Image.new(
                "RGBA",
                (self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT),
                (255, 255, 255, 120),
            )

            # Tile the pattern across the background
            for row in range(tiles_y):
                for col in range(tiles_x):
                    x = col * tile_size - tile_size // 2  # Offset for seamless look
                    y = row * tile_size - tile_size // 2

                    if x < self.PINTEREST_WIDTH and y < self.PINTEREST_HEIGHT:
                        # Make pattern tiles more visible
                        pattern_copy = pattern_tile.copy()
                        alpha = Image.new(
                            "L", pattern_copy.size, 140
                        )  # Much more visible
                        pattern_copy.putalpha(alpha)

                        # Paste the tile
                        canvas.paste(pattern_copy, (x, y), pattern_copy)

            # Add lighter overlay to maintain text readability
            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Tiled pattern background error: {e}")
            return self._create_solid_background(canvas, colors)

    def _create_solid_background(
        self, canvas: Image.Image, colors: Dict[str, Tuple[int, int, int]]
    ) -> Image.Image:
        """Create solid color background"""
        try:
            # Simple solid background
            draw = ImageDraw.Draw(canvas)
            bg_color = colors["background"]

            # Fill with background color
            draw.rectangle(
                [0, 0, self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT], fill=bg_color
            )

            # Add subtle texture overlay if available
            if self.canvas_bg:
                try:
                    texture = resize_image(
                        self.canvas_bg, self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT
                    )
                    texture = texture.convert("RGBA")

                    # Ensure texture is exactly the same size as canvas
                    if texture.size != (self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT):
                        texture = texture.resize((self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT))

                    # Very subtle texture
                    alpha = Image.new("L", texture.size, 20)
                    texture.putalpha(alpha)

                    canvas = Image.alpha_composite(canvas.convert("RGBA"), texture)
                except Exception as tex_e:
                    logger.warning(f"⚠️ Texture overlay error: {tex_e}. Skipping texture.")
                    # Continue with plain background if texture fails

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Solid background creation error: {e}")
            return canvas

    def _add_header_section(
        self,
        canvas: Image.Image,
        product_data: Dict[str, Any],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add header section with product type badge"""
        try:
            draw = ImageDraw.Draw(canvas)

            # Use subfolder name as header, like main mockup
            badge_text = product_data.get("name", "Digital Product")

            # Badge text - use GreatVibes-Regular like main mockup titles - WAY LARGER
            try:
                font = get_font("GreatVibes-Regular", 72)  # Much larger font size
            except:
                try:
                    font = get_font(
                        "Great Vibes", 72
                    )  # System Great Vibes font fallback
                except:
                    try:
                        font = get_font(
                            "Clattering.ttf", 64
                        )  # Fallback to project font
                    except:
                        try:
                            font = get_font(
                                "Free Version Angelina.ttf", 64
                            )  # Artistic fallback
                        except:
                            font = get_font("Poppins-SemiBold.ttf", 60)

            # Calculate actual text dimensions first
            text_bbox = draw.textbbox((0, 0), badge_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Badge background - fit to actual text width with padding
            padding = 60  # Extra padding around text
            badge_width = text_width + (padding * 2)
            badge_height = max(110, text_height + 40)  # Ensure minimum height
            badge_x = (self.PINTEREST_WIDTH - badge_width) // 2
            badge_y = 25  # Moved up slightly

            # Rounded rectangle for badge with white background
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
                radius=35,  # Proportional radius for the larger badge
                fill=colors["badge_bg"],
                outline=colors["primary"],
                width=3,
            )

            # Center text in badge
            text_x = badge_x + (badge_width - text_width) // 2
            text_y = badge_y + (badge_height - text_height) // 2

            draw.text(
                (text_x, text_y), badge_text, fill=colors["badge_text"], font=font
            )

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Header section error: {e}")
            return canvas

    def _add_hero_section(
        self,
        canvas: Image.Image,
        product_images: List[str],
        product_data: Dict[str, Any],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add main product showcase section"""
        try:
            product_type = product_data.get("product_type", "pattern")

            if product_type == "pattern":
                return self._add_pattern_hero(canvas, product_images, colors)
            elif product_type == "clipart":
                return self._add_clipart_hero(canvas, product_images, colors)
            elif product_type == "border_clipart":
                return self._add_border_clipart_hero(canvas, product_images, colors)
            else:
                return self._add_generic_hero(canvas, product_images, colors)

        except Exception as e:
            logger.warning(f"⚠️ Hero section error: {e}")
            return canvas

    def _add_pattern_hero(
        self,
        canvas: Image.Image,
        product_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add pattern-specific hero section with beautiful pattern grid showcase"""
        try:
            if not product_images:
                return canvas

            # Find all pattern images (could be multiple patterns in a set)
            pattern_images = []
            for img_path in product_images:
                if os.path.exists(img_path) and not img_path.endswith(
                    ("_mockup.png", "_grid.png")
                ):
                    pattern_images.append(img_path)

            if not pattern_images:
                return canvas

            # Create a centered grid showcase
            grid_size = 180  # Size of each pattern square
            grid_padding = 15  # Padding between squares

            # For patterns, create a 2x2 or 1x3 grid depending on how many we have
            if len(pattern_images) == 1:
                # Single pattern - show 1x3 variation grid
                return self._create_single_pattern_variations(
                    canvas, pattern_images[0], colors
                )
            else:
                # Multiple patterns - show them in a grid
                return self._create_multiple_pattern_grid(
                    canvas, pattern_images, colors
                )

        except Exception as e:
            logger.warning(f"⚠️ Pattern hero error: {e}")
            return canvas

    def _create_single_pattern_variations(
        self,
        canvas: Image.Image,
        pattern_path: str,
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Create variations of a single pattern to show different scales/colors"""
        try:
            pattern_img = Image.open(pattern_path).convert("RGBA")

            # Grid settings - much larger
            grid_size = 280  # Much bigger squares
            grid_padding = 25  # More padding
            variations = 3  # Show 3 variations

            # Calculate total width and center position
            total_width = (variations * grid_size) + ((variations - 1) * grid_padding)
            start_x = (self.PINTEREST_WIDTH - total_width) // 2
            center_y = self.HERO_START + (self.HERO_HEIGHT // 2) - (grid_size // 2)

            # Create 3 variations: original, smaller scale, different saturation
            variations_data = [
                {"scale": 1.0, "saturation": 1.0, "label": "Original"},
                {"scale": 0.5, "saturation": 1.2, "label": "Fine Detail"},
                {"scale": 1.5, "saturation": 0.8, "label": "Large Scale"},
            ]

            for i, variation in enumerate(variations_data):
                x = start_x + (i * (grid_size + grid_padding))
                y = center_y

                # Create variation
                var_pattern = self._create_pattern_variation(
                    pattern_img, grid_size, variation
                )

                # Add larger white background frame
                frame = Image.new(
                    "RGBA", (grid_size + 16, grid_size + 16), (255, 255, 255, 255)
                )
                frame_x = x - 8
                frame_y = y - 8
                canvas.paste(frame, (frame_x, frame_y), frame)

                # Add larger shadow
                shadow = Image.new(
                    "RGBA", (grid_size + 12, grid_size + 12), (0, 0, 0, 60)
                )
                canvas.paste(shadow, (x + 6, y + 6), shadow)

                # Paste variation
                canvas.paste(var_pattern, (x, y), var_pattern)

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Single pattern variations error: {e}")
            return canvas

    def _create_multiple_pattern_grid(
        self,
        canvas: Image.Image,
        pattern_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Create a grid showcasing multiple patterns"""
        try:
            # Grid settings - much larger
            grid_size = 220  # Much bigger squares
            grid_padding = 20  # More padding
            max_patterns = 6  # Show up to 6 patterns

            # Use up to max_patterns
            display_patterns = pattern_images[:max_patterns]
            pattern_count = len(display_patterns)

            # Determine grid layout
            if pattern_count <= 3:
                cols = pattern_count
                rows = 1
            elif pattern_count <= 6:
                cols = 3
                rows = 2
            else:
                cols = 3
                rows = 2

            # Calculate grid dimensions and center position
            total_width = (cols * grid_size) + ((cols - 1) * grid_padding)
            total_height = (rows * grid_size) + ((rows - 1) * grid_padding)

            start_x = (self.PINTEREST_WIDTH - total_width) // 2
            start_y = self.HERO_START + (self.HERO_HEIGHT - total_height) // 2

            # Place patterns in grid
            for i, pattern_path in enumerate(display_patterns):
                if i >= cols * rows:
                    break

                row = i // cols
                col = i % cols

                x = start_x + (col * (grid_size + grid_padding))
                y = start_y + (row * (grid_size + grid_padding))

                # Load and resize pattern
                pattern_img = Image.open(pattern_path).convert("RGBA")
                pattern_resized = resize_image(pattern_img, grid_size, grid_size)

                # Add larger white frame
                frame = Image.new(
                    "RGBA", (grid_size + 12, grid_size + 12), (255, 255, 255, 255)
                )
                canvas.paste(frame, (x - 6, y - 6), frame)

                # Add larger shadow
                shadow = Image.new(
                    "RGBA", (grid_size + 8, grid_size + 8), (0, 0, 0, 50)
                )
                canvas.paste(shadow, (x + 4, y + 4), shadow)

                # Paste pattern
                canvas.paste(pattern_resized, (x, y), pattern_resized)

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Multiple pattern grid error: {e}")
            return canvas

    def _create_pattern_variation(
        self, pattern_img: Image.Image, size: int, variation: Dict[str, float]
    ) -> Image.Image:
        """Create a variation of a pattern with different scale/saturation"""
        try:
            scale = variation["scale"]
            saturation = variation["saturation"]

            # Scale the pattern
            if scale != 1.0:
                new_size = int(pattern_img.width * scale)
                scaled_pattern = resize_image(pattern_img, new_size, new_size)
            else:
                scaled_pattern = pattern_img

            # Create tiled version to fill the square
            tiled = Image.new("RGBA", (size, size), (255, 255, 255, 0))

            # Tile the scaled pattern
            for y in range(0, size, scaled_pattern.height):
                for x in range(0, size, scaled_pattern.width):
                    tiled.paste(scaled_pattern, (x, y), scaled_pattern)

            # Crop to exact size
            tiled = tiled.crop((0, 0, size, size))

            return tiled

        except Exception as e:
            logger.warning(f"⚠️ Pattern variation error: {e}")
            return resize_image(pattern_img, size, size)

    def _add_clipart_hero(
        self,
        canvas: Image.Image,
        product_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add clipart-specific hero section with clean 6-clipart grid, no backdrops"""
        try:
            if not product_images:
                return canvas

            # Filter clipart images (avoid mockups) and get exactly 6
            clipart_images = [
                img
                for img in product_images
                if os.path.exists(img)
                and not img.endswith(("_mockup.png", "_grid.png"))
            ][
                :6
            ]  # Take exactly 6 items

            if not clipart_images:
                return canvas

            # Use almost all available space between header and features sections
            # Leave minimal margins (30px top/bottom) for breathing room
            available_height = self.HERO_HEIGHT - 60  # 30px margin top and bottom
            available_width = self.PINTEREST_WIDTH - 60  # 30px margin left and right

            # Simple clean grid: 2 rows x 3 cols for up to 6 cliparts
            rows = 2
            cols = 3

            # Calculate maximum item size to fill available space
            # Account for spacing between items (20px between items)
            max_item_width = (available_width - ((cols - 1) * 20)) // cols
            max_item_height = (available_height - ((rows - 1) * 20)) // rows

            # Use the smaller dimension to keep items square and fit perfectly
            item_size = min(max_item_width, max_item_height)
            grid_spacing = 20  # Minimal clean spacing between items

            # Calculate actual grid dimensions
            total_width = (cols * item_size) + ((cols - 1) * grid_spacing)
            total_height = (rows * item_size) + ((rows - 1) * grid_spacing)

            # Position grid slightly lower than center, with more space below the header text
            start_x = (self.PINTEREST_WIDTH - total_width) // 2
            start_y = (
                self.HERO_START + 60
            )  # Start 60px below the hero section start (more space from header text)

            # Place clipart items in clean grid
            for i, img_path in enumerate(clipart_images):
                try:
                    row = i // cols
                    col = i % cols

                    x = start_x + (col * (item_size + grid_spacing))
                    y = start_y + (row * (item_size + grid_spacing))

                    # Load and resize clipart
                    clipart_img = Image.open(img_path).convert("RGBA")
                    clipart_resized = resize_image(clipart_img, item_size, item_size)

                    # No background - just paste the clipart directly for clean look
                    canvas.paste(clipart_resized, (x, y), clipart_resized)

                except Exception as e:
                    logger.warning(f"⚠️ Error processing clipart item {i}: {e}")
                    continue

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Clipart hero error: {e}")
            return canvas

    def _add_border_clipart_hero(
        self,
        canvas: Image.Image,
        product_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add border clipart hero section"""
        try:
            if not product_images:
                return canvas

            # Find border image
            border_image_path = None
            for img_path in product_images:
                if os.path.exists(img_path) and not img_path.endswith(
                    ("_mockup.png", "_grid.png")
                ):
                    border_image_path = img_path
                    break

            if not border_image_path:
                return canvas

            # Load border image
            border_img = Image.open(border_image_path).convert("RGBA")

            # Create horizontal tiled display
            border_height = 60
            border_width = self.PINTEREST_WIDTH - 100  # Margins

            # Resize border to appropriate height
            aspect_ratio = border_img.width / border_img.height
            new_width = int(border_height * aspect_ratio)
            border_resized = resize_image(border_img, new_width, border_height)

            # Calculate how many tiles fit
            tiles_needed = (border_width // new_width) + 1

            # Create seamless border rows
            start_x = 50
            rows = [
                self.HERO_START + 100,
                self.HERO_START + 200,
                self.HERO_START + 300,
                self.HERO_START + 400,
            ]

            for row_y in rows:
                current_x = start_x
                for i in range(tiles_needed):
                    if current_x < self.PINTEREST_WIDTH - 50:
                        canvas.paste(border_resized, (current_x, row_y), border_resized)
                        current_x += new_width

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Border clipart hero error: {e}")
            return canvas

    def _add_generic_hero(
        self,
        canvas: Image.Image,
        product_images: List[str],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add generic hero section for other product types"""
        try:
            if not product_images:
                return canvas

            # Use first available image
            main_image_path = None
            for img_path in product_images:
                if os.path.exists(img_path):
                    main_image_path = img_path
                    break

            if not main_image_path:
                return canvas

            # Load and center main image
            main_img = Image.open(main_image_path).convert("RGBA")

            # Resize to fit hero section
            max_size = min(600, self.HERO_HEIGHT - 100)
            main_resized = resize_image(main_img, max_size, max_size)

            # Center in hero section
            x = (self.PINTEREST_WIDTH - main_resized.width) // 2
            y = self.HERO_START + (self.HERO_HEIGHT - main_resized.height) // 2

            # Add shadow
            shadow_offset = 5
            shadow = Image.new("RGBA", main_resized.size, (0, 0, 0, 80))
            canvas.paste(shadow, (x + shadow_offset, y + shadow_offset), shadow)

            # Paste main image
            canvas.paste(main_resized, (x, y), main_resized)

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Generic hero error: {e}")
            return canvas

    def _add_features_section(
        self,
        canvas: Image.Image,
        product_data: Dict[str, Any],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add features/selling points section"""
        try:
            draw = ImageDraw.Draw(canvas)

            # Feature points - no emojis for better font compatibility
            features = [
                "High Quality Design",
                "Instant Download",
                "Digital and Printed Uses",
                "Commercial Use Included",
            ]

            # Feature styling - use clean, legible font instead of stylized
            try:
                feature_font = get_font(
                    "Poppins-SemiBold.ttf", 34
                )  # Clean, legible font
            except:
                try:
                    feature_font = get_font(
                        "Poppins-Regular.ttf", 34
                    )  # Poppins regular fallback
                except:
                    try:
                        feature_font = get_font("Arial", 34)  # System Arial fallback
                    except:
                        try:
                            feature_font = get_font(
                                "Helvetica", 34
                            )  # System Helvetica fallback
                        except:
                            feature_font = get_font(
                                "LibreBaskerville-Regular.ttf", 32
                            )  # Project font fallback

            # Calculate layout - bigger spacing for larger fonts
            feature_height = 75  # More space for larger fonts
            start_y = self.FEATURES_START + 40

            for i, feature in enumerate(features):
                y = start_y + (i * feature_height)

                # Feature background - larger for bigger fonts
                bg_width = 700  # Wider for bigger text
                bg_height = 55  # Taller for bigger fonts
                bg_x = (self.PINTEREST_WIDTH - bg_width) // 2
                bg_y = y - 8

                # Rounded background - white with border
                draw.rounded_rectangle(
                    [bg_x, bg_y, bg_x + bg_width, bg_y + bg_height],
                    radius=20,
                    fill=(255, 255, 255),  # White background
                    outline=colors["primary"],
                    width=2,
                )

                # Feature text - dark on white background
                text_bbox = draw.textbbox((0, 0), feature, font=feature_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (self.PINTEREST_WIDTH - text_width) // 2

                draw.text(
                    (text_x, y), feature, fill=colors["text_dark"], font=feature_font
                )

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Features section error: {e}")
            return canvas

    def _add_cta_section(
        self,
        canvas: Image.Image,
        product_data: Dict[str, Any],
        colors: Dict[str, Tuple[int, int, int]],
    ) -> Image.Image:
        """Add call-to-action section"""
        try:
            draw = ImageDraw.Draw(canvas)

            # CTA text
            cta_text = "Click to Shop Now!"

            # Use GreatVibes-Regular for CTA like main mockup titles
            try:
                cta_font = get_font("GreatVibes-Regular", 48)  # Main mockup font, large
            except:
                try:
                    cta_font = get_font(
                        "Great Vibes", 48
                    )  # System Great Vibes font fallback
                except:
                    try:
                        cta_font = get_font(
                            "DSMarkerFelt.ttf", 44
                        )  # Fallback to project font
                    except:
                        try:
                            cta_font = get_font("Clattering.ttf", 44)
                        except:
                            cta_font = get_font("Free Version Angelina.ttf", 44)

            # Measure text first, then size button to fit
            text_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Size button to text with generous padding
            h_padding = 60
            v_padding = 30
            button_width = text_width + (h_padding * 2)
            button_height = text_height + (v_padding * 2)
            button_x = (self.PINTEREST_WIDTH - button_width) // 2
            # Center button vertically within CTA section
            button_y = self.CTA_START + (self.CTA_HEIGHT - button_height) // 2

            # Clean gradient button background
            draw.rounded_rectangle(
                [button_x, button_y, button_x + button_width, button_y + button_height],
                radius=30,
                fill=colors["button_bg"],
                outline=colors["primary"],
                width=3,
            )

            # Simple highlight effect - just a lighter top section (no alpha)
            button_text_color = colors.get("button_text", colors["text_light"])
            if button_text_color == (255, 255, 255):  # White text = dark button
                highlight_color = tuple(min(255, c + 20) for c in colors["button_bg"])
            else:  # Dark text = light button
                highlight_color = tuple(max(0, c - 20) for c in colors["button_bg"])

            # Top highlight without alpha
            draw.rounded_rectangle(
                [
                    button_x + 3,
                    button_y + 3,
                    button_x + button_width - 3,
                    button_y + button_height // 2,
                ],
                radius=27,
                fill=highlight_color,
            )

            # Center text in button, accounting for textbbox offset
            text_x = button_x + (button_width - text_width) // 2 - text_bbox[0]
            text_y = button_y + (button_height - text_height) // 2 - text_bbox[1]

            draw.text((text_x, text_y), cta_text, fill=button_text_color, font=cta_font)

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ CTA section error: {e}")
            return canvas

    def _add_footer_section(
        self, canvas: Image.Image, colors: Dict[str, Tuple[int, int, int]]
    ) -> Image.Image:
        """Add footer/branding section with Digital Veil logo and name"""
        try:
            draw = ImageDraw.Draw(canvas)

            # Footer background (subtle)
            draw.rectangle(
                [0, self.FOOTER_START, self.PINTEREST_WIDTH, self.PINTEREST_HEIGHT],
                fill=colors["background"],
            )

            # Add logo if available - MUCH LARGER
            logo_size = 80  # Much larger logo
            logo_x = None
            bottom_padding = 20  # Reserve padding so nothing gets clipped

            if self.logo:
                # Resize logo to fit footer
                logo_resized = resize_image(self.logo, logo_size, logo_size)

                # Calculate positions for logo + text layout - use GreatVibes-Regular LARGER
                try:
                    footer_font = get_font(
                        "GreatVibes-Regular", 80
                    )  # Much larger main mockup font
                except:
                    try:
                        footer_font = get_font(
                            "Great Vibes", 80
                        )  # System Great Vibes font fallback - larger
                    except:
                        try:
                            footer_font = get_font(
                                "Clattering.ttf", 72
                            )  # Fallback to project font - larger
                        except:
                            try:
                                footer_font = get_font(
                                    "Free Version Angelina.ttf", 72
                                )  # Artistic fallback - larger
                            except:
                                footer_font = get_font("Poppins-SemiBold.ttf", 64)

                text_bbox = draw.textbbox((0, 0), self.brand_name, font=footer_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Total width for logo + spacing + text
                total_width = logo_size + 15 + text_width
                start_x = (self.PINTEREST_WIDTH - total_width) // 2

                # Usable footer area with bottom padding
                usable_height = self.FOOTER_HEIGHT - bottom_padding
                content_height = max(logo_size, text_height)

                logo_x = start_x
                logo_y = self.FOOTER_START + (usable_height - logo_size) // 2

                # Paste logo
                canvas.paste(logo_resized, (logo_x, logo_y), logo_resized)

                # Brand name text next to logo, accounting for textbbox offset
                text_x = logo_x + logo_size + 15
                text_y = (
                    self.FOOTER_START
                    + (usable_height - text_height) // 2
                    - text_bbox[1]
                )

                draw.text(
                    (text_x, text_y),
                    self.brand_name,
                    fill=colors["text_dark"],
                    font=footer_font,
                )

            else:
                # Just brand name if no logo - use GreatVibes-Regular MUCH LARGER
                try:
                    footer_font = get_font(
                        "GreatVibes-Regular", 88
                    )  # Main mockup font, much larger
                except:
                    try:
                        footer_font = get_font(
                            "Great Vibes", 88
                        )  # System Great Vibes font fallback - much larger
                    except:
                        try:
                            footer_font = get_font(
                                "Clattering.ttf", 80
                            )  # Fallback to project font - much larger
                        except:
                            try:
                                footer_font = get_font(
                                    "Free Version Angelina.ttf", 80
                                )  # Artistic fallback - much larger
                            except:
                                footer_font = get_font("Poppins-SemiBold.ttf", 72)

                text_bbox = draw.textbbox((0, 0), self.brand_name, font=footer_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Usable footer area with bottom padding
                usable_height = self.FOOTER_HEIGHT - bottom_padding

                # Account for textbbox offset for proper centering
                text_x = (self.PINTEREST_WIDTH - text_width) // 2 - text_bbox[0]
                text_y = self.FOOTER_START + (usable_height - text_height) // 2 - text_bbox[1]

                draw.text(
                    (text_x, text_y),
                    self.brand_name,
                    fill=colors["text_dark"],
                    font=footer_font,
                )

            return canvas

        except Exception as e:
            logger.warning(f"⚠️ Footer section error: {e}")
            return canvas


def create_pinterest_mockup(
    product_images: List[str], product_data: Dict[str, Any], output_path: str
) -> bool:
    """
    Create Pinterest-optimized vertical mockup

    Args:
        product_images: List of product image paths
        product_data: Product information
        output_path: Output file path

    Returns:
        bool: Success status
    """
    generator = PinterestMockupGenerator()
    return generator.create_pinterest_mockup(product_images, product_data, output_path)
