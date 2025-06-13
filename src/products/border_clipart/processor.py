"""Border clipart processor implementation."""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension, ensure_directory
from src.services.processing.video import VideoProcessor


@register_processor("border_clipart")
class BorderClipartProcessor(BaseProcessor):
    """Processor for horizontally seamless border clipart processing."""
    
    def get_default_workflow_steps(self) -> List[str]:
        """Return default workflow steps for border clipart."""
        return ["resize", "mockup", "video", "zip"]
    
    def resize_images(self) -> Dict[str, Any]:
        """Resize border clipart images for processing."""
        from src.utils.resize_utils import ImageResizer
        
        try:
            resizer = ImageResizer(max_size=1500, dpi=(300, 300))
            result = resizer.resize_clipart_style(self.config.input_dir)
            
            self.logger.info(f"Resized {result.get('processed', 0)} border clipart images")
            return result
            
        except Exception as e:
            self.logger.error(f"Border clipart resize failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_mockups(self) -> Dict[str, Any]:
        """Create border clipart mockups."""
        try:
            results = {}
            
            # Create horizontal seamless mockup (main mockup)
            results["main_mockup"] = self._create_horizontal_seamless_mockup()
            
            # Create grid mockup showing individual borders
            results["grid_mockup"] = self._create_grid_mockup()
            
            # Create transparency demo
            if self.config.custom_settings.get("create_transparency_demo", True):
                results["transparency_demo"] = self._create_transparency_demo()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Mockup creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_horizontal_seamless_mockup(self) -> Dict[str, Any]:
        """Create the main horizontal seamless border mockup with 3 rows and text overlays."""
        from src.products.border_clipart.mockups import create_horizontal_seamless_mockup
        from src.utils.file_operations import find_files_by_extension
        from PIL import Image
        import os
        
        # Create mocks folder inside the input directory
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            # Find image files (excluding the mocks folder)
            all_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            image_files = [f for f in all_files if '/mocks/' not in f and '\\mocks\\' not in f]
            
            if not image_files:
                return {"success": False, "error": "No images found for mockup"}
            
            # Create title from folder name
            folder_name = Path(self.config.input_dir).name
            title = folder_name.replace("_", " ").replace("-", " ").title()
            
            # Create subtitle with number of images
            num_images = len(image_files)
            subtitle_top = f"{num_images} Seamless Borders Cliparts"
            
            # Create mockup with specific text overlays
            result = create_horizontal_seamless_mockup(
                input_image_paths=image_files,
                title=title,
                subtitle_top=subtitle_top,
                subtitle_bottom="transparent png  |  300 dpi  |  commercial use",
                canvas_size=(3000, 2250),
                rows=4
            )
            
            # Handle the return value
            if isinstance(result, tuple):
                mockup_image, _ = result
            else:
                mockup_image = result
            
            # Save the mockup
            output_path = os.path.join(mockup_dir, "main.png")
            mockup_image.save(output_path)
            
            return {"success": True, "file": output_path, "output_folder": mockup_dir}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_grid_mockup(self) -> Dict[str, Any]:
        """Create multiple 2x2 grid mockups to show individual borders."""
        from src.utils.grid_utils import GridCreator
        from src.utils.file_operations import find_files_by_extension
        import os
        
        # Create mocks folder inside the input directory
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            # Find image files (excluding the mocks folder)
            all_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            image_files = [f for f in all_files if '/mocks/' not in f and '\\mocks\\' not in f]
            
            if len(image_files) < 1:
                return {"success": False, "error": f"Need at least 1 image for grid, found {len(image_files)}"}
            
            # Calculate how many row grids we need (3 images per grid, one per row)
            images_per_grid = 3
            num_grids = len(image_files) // images_per_grid
            remaining_images = len(image_files) % images_per_grid
            
            if remaining_images > 0:
                num_grids += 1
            
            self.logger.info(f"Total images: {len(image_files)}, will create {num_grids} grids")
            
            created_files = []
            
            for grid_num in range(num_grids):
                start_idx = grid_num * images_per_grid
                end_idx = min(start_idx + images_per_grid, len(image_files))
                grid_images = image_files[start_idx:end_idx]
                
                # If last grid has fewer than 3 images, pad with the first images
                if len(grid_images) < images_per_grid:
                    remaining_slots = images_per_grid - len(grid_images)
                    grid_images.extend(image_files[:remaining_slots])
                
                # Save the grid with numbered filename
                if num_grids == 1:
                    output_path = os.path.join(mockup_dir, "grid.png")
                else:
                    output_path = os.path.join(mockup_dir, f"grid_{grid_num + 1}.png")
                
                # Create horizontal rows using border-specific function
                from src.products.border_clipart.mockups import create_border_horizontal_rows
                grid_image = create_border_horizontal_rows(
                    input_image_paths=grid_images,
                    grid_size=(2000, 2000),
                    max_rows=3,
                    padding=30
                )
                
                # Save the grid
                grid_image.save(output_path, "PNG")
                result_path = output_path
                
                if result_path:
                    # Apply watermark to the created grid
                    watermarked_path = self._apply_watermark_to_grid(result_path)
                    if watermarked_path:
                        created_files.append(watermarked_path)
                        self.logger.info(f"Created and watermarked grid {grid_num + 1}/{num_grids}: {watermarked_path}")
                    else:
                        created_files.append(result_path)
                        self.logger.warning(f"Grid created but watermarking failed for grid {grid_num + 1}")
                else:
                    self.logger.warning(f"Failed to create grid {grid_num + 1}")
            
            return {
                "success": True, 
                "files": created_files, 
                "output_folder": mockup_dir,
                "grids_created": num_grids
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_watermark_to_grid(self, grid_path: str) -> Optional[str]:
        """Apply watermark to a grid mockup using unified watermarking."""
        try:
            from PIL import Image
            from src.utils.common import apply_watermark
            
            # Load the grid image
            grid_image = Image.open(grid_path)
            
            # Apply watermark using unified function
            watermarked_image = apply_watermark(
                image=grid_image,
                text="digital veil",
                font_name="Clattering",
                font_size=30,
                text_color=(120, 120, 120),
                opacity=60,
                diagonal_spacing=500
            )
            
            # Save watermarked version (overwrite original)
            watermarked_image.convert("RGB").save(grid_path, "PNG", quality=95, optimize=True)
            self.logger.info(f"Applied watermark to grid: {grid_path}")
            return grid_path
            
        except Exception as e:
            self.logger.error(f"Failed to apply watermark to grid {grid_path}: {e}")
            return None
    
    def _create_transparency_demo(self) -> Dict[str, Any]:
        """Create transparency demonstration mockup."""
        from src.products.clipart.transparency import create_transparency_demo
        from src.utils.file_operations import find_files_by_extension
        import os
        
        # Create mocks folder inside the input directory
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            # Find image files (excluding the mocks folder)
            all_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            image_files = [f for f in all_files if '/mocks/' not in f and '\\mocks\\' not in f]
            
            if not image_files:
                return {"success": False, "error": "No images found for transparency demo"}
            
            # Use the first image for the demo
            demo_image_path = image_files[0]
            
            # Create transparency demo
            demo_image = create_transparency_demo(
                image_path=demo_image_path,
                scale=0.7,
                checkerboard_size=30
            )
            
            if demo_image is None:
                return {"success": False, "error": "Failed to create transparency demo"}
            
            # Save the demo
            output_path = os.path.join(mockup_dir, "transparency.png")
            demo_image.save(output_path)
            
            return {"success": True, "file": output_path, "output_folder": mockup_dir}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_content_for_type(self) -> Dict[str, Any]:
        """Generate border clipart-specific content for Etsy listings."""
        if not self.ai_provider:
            return {}
        
        try:
            # Use main mockup for AI content generation
            main_mockup = os.path.join(self.config.input_dir, "mocks", "main.png")
            
            # Fallback to main.jpg if main.png doesn't exist
            if not os.path.exists(main_mockup):
                main_mockup = os.path.join(self.config.input_dir, "mocks", "main.jpg")
            
            # If no main mockup exists, skip content generation
            if not os.path.exists(main_mockup):
                self.logger.warning("No main mockup found for content generation")
                return {}
            
            representative_image = main_mockup
            
            # Generate complete Etsy listing using DEFAULT_ETSY_INSTRUCTIONS
            from src.services.etsy.constants import DEFAULT_ETSY_INSTRUCTIONS
            from src.utils.ai_utils import parse_etsy_listing_response
            
            ai_response = generate_content_with_ai(
                self.ai_provider,
                DEFAULT_ETSY_INSTRUCTIONS,
                representative_image
            )
            
            # Parse the response to extract title, description, and tags
            parsed_content = parse_etsy_listing_response(ai_response)
            title = parsed_content['title']
            description = parsed_content['description']
            tags_text = parsed_content['tags']
            
            # Convert tags to list
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()][:13]
            
            # Count images for description enhancement
            image_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            image_count = len(image_files)
            
            # Generate attributes for Etsy listing
            attributes = self._generate_etsy_attributes(representative_image)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category": "Digital", 
                "subcategory": "Border Clipart",
                "image_count": image_count,
                "image_analyzed": representative_image,
                "attributes": attributes,
                "shop_section": "BORDER CLIP ARTS"
            }
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return {"error": str(e)}
    
    def _generate_etsy_attributes(self, representative_image: str) -> Dict[str, Any]:
        """Generate Etsy listing attributes for border clipart."""
        try:
            attributes = {
                "materials": ["Digital"],
                "orientation": "Horizontal",
                "occasion": "Everyday",
                "subject": ["Border", "Decorative", "Pattern"],
                "can_be_personalized": "No"
            }
            
            # Use AI to analyze colors and subjects if available
            if self.ai_provider and representative_image:
                try:
                    # Analyze primary color
                    color_prompt = """
                    Analyze this border clipart image and identify the primary color.
                    Return only one of these exact color names:
                    Red, Orange, Yellow, Green, Blue, Purple, Pink, Black, White, Gray, Brown, Beige
                    Return only the color name, nothing else.
                    """
                    
                    primary_color = generate_content_with_ai(
                        self.ai_provider,
                        color_prompt,
                        representative_image
                    ).strip()
                    
                    # Validate the color is in the allowed list
                    allowed_colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", 
                                    "Pink", "Black", "White", "Gray", "Brown", "Beige"]
                    if primary_color in allowed_colors:
                        attributes["primary_color"] = primary_color
                    else:
                        attributes["primary_color"] = "Blue"
                    
                    # Analyze subject matter for borders
                    subject_prompt = """
                    Analyze this border clipart and identify up to 3 main themes or styles.
                    Choose from these categories only:
                    Floral, Geometric, Decorative, Vintage, Modern, Nature, Abstract, 
                    Ornamental, Elegant, Casual, Festive, Simple
                    Return up to 3 categories separated by commas, nothing else.
                    """
                    
                    subjects_text = generate_content_with_ai(
                        self.ai_provider,
                        subject_prompt,
                        representative_image
                    ).strip()
                    
                    subjects = [s.strip() for s in subjects_text.split(',') if s.strip()][:3]
                    if subjects:
                        attributes["subject"] = subjects
                        
                except Exception as e:
                    self.logger.warning(f"Could not analyze border clipart attributes: {e}")
                    attributes["primary_color"] = "Blue"
            else:
                attributes["primary_color"] = "Blue"
                
            return attributes
            
        except Exception as e:
            self.logger.error(f"Error generating Etsy attributes: {e}")
            return {
                "primary_color": "Blue",
                "materials": ["Digital"],
                "can_be_personalized": "No"
            }
    
    def create_videos(self) -> Dict[str, Any]:
        """Create videos using unified video processor."""
        try:
            video_processor = VideoProcessor("border_clipart")
            video_path = video_processor.create_product_showcase_video(self.config.input_dir)
            
            if video_path:
                self.logger.info(f"Video created: {video_path}")
                return {"success": True, "file": video_path}
            else:
                return {"success": False, "error": "Failed to create video"}
                
        except Exception as e:
            self.logger.error(f"Video creation failed: {e}")
            return {"success": False, "error": str(e)}