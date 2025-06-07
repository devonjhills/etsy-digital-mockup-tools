"""Clipart processor implementation."""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension, ensure_directory
from src.services.processing.video import VideoProcessor


@register_processor("clipart")
class ClipartProcessor(BaseProcessor):
    """Processor for clipart/illustration processing."""
    
    def get_default_workflow_steps(self) -> List[str]:
        """Return default workflow steps for clipart."""
        return ["resize", "mockup", "video", "zip"]
    
    def resize_images(self) -> Dict[str, Any]:
        """Resize clipart images for processing."""
        from src.utils.resize_utils import ImageResizer
        
        try:
            resizer = ImageResizer(max_size=1500, dpi=(300, 300))
            result = resizer.resize_clipart_style(self.config.input_dir)
            
            self.logger.info(f"Resized {result.get('processed', 0)} clipart images")
            return result
            
        except Exception as e:
            self.logger.error(f"Clipart resize failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_mockups(self) -> Dict[str, Any]:
        """Create clipart mockups."""
        try:
            results = {}
            
            # Create square mockup
            results["square_mockup"] = self._create_square_mockup()
            
            # Create grid mockup (2x2)
            results["grid_mockup"] = self._create_grid_mockup()
            
            # Create transparency demo
            if self.config.custom_settings.get("create_transparency_demo", True):
                results["transparency_demo"] = self._create_transparency_demo()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Mockup creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_square_mockup(self) -> Dict[str, Any]:
        """Create square clipart mockup."""
        from src.products.clipart.mockups import create_square_mockup
        from src.utils.file_operations import find_files_by_extension
        from PIL import Image
        import os
        
        # Create mocks folder inside the input directory (like patterns)
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
            
            # Create a background canvas
            canvas_bg = Image.new("RGB", (3000, 2250), "white")
            
            # Generate subtitles
            subtitle_top = f"{len(image_files)} clip arts • Commercial Use"
            subtitle_bottom = "300 DPI • Transparent PNG"
            
            # Create mockup
            result = create_square_mockup(
                input_image_paths=image_files,
                canvas_bg_image=canvas_bg,
                title=title,
                subtitle_top=subtitle_top,
                subtitle_bottom=subtitle_bottom,
                grid_size=(3000, 2250),
                padding=30
            )
            
            # Handle the return value (image, used_images tuple)
            if isinstance(result, tuple):
                mockup_image, _ = result  # Don't need used_images
            else:
                mockup_image = result
            
            # Save the mockup
            output_path = os.path.join(mockup_dir, "main.png")
            mockup_image.save(output_path)
            
            return {"success": True, "file": output_path, "output_folder": mockup_dir}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_grid_mockup(self) -> Dict[str, Any]:
        """Create multiple 2x2 grid mockups to show all images."""
        from src.services.processing.grid import GridProcessor
        from src.utils.file_operations import find_files_by_extension
        import os
        
        # Create mocks folder inside the input directory (like patterns)
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            # Find image files (excluding the mocks folder)
            all_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            image_files = [f for f in all_files if '/mocks/' not in f and '\\mocks\\' not in f]
            
            if len(image_files) < 4:
                return {"success": False, "error": f"Need at least 4 images for grid, found {len(image_files)}"}
            
            # Calculate how many 2x2 grids we need (4 images per grid)
            images_per_grid = 4
            num_grids = len(image_files) // images_per_grid  # Only complete grids
            remaining_images = len(image_files) % images_per_grid
            
            # If there are remaining images, create one more grid
            if remaining_images > 0:
                num_grids += 1
            
            self.logger.info(f"Total images: {len(image_files)}, will create {num_grids} grids")
            
            # Use the unified grid processor
            grid_processor = GridProcessor("clipart")
            
            created_files = []
            
            for grid_num in range(num_grids):
                start_idx = grid_num * images_per_grid
                end_idx = min(start_idx + images_per_grid, len(image_files))
                grid_images = image_files[start_idx:end_idx]
                
                # If last grid has fewer than 4 images, pad with the first images to make it look complete
                if len(grid_images) < images_per_grid:
                    remaining_slots = images_per_grid - len(grid_images)
                    grid_images.extend(image_files[:remaining_slots])
                
                # Save the grid with numbered filename
                if num_grids == 1:
                    output_path = os.path.join(mockup_dir, "grid.png")
                else:
                    output_path = os.path.join(mockup_dir, f"grid_{grid_num + 1}.png")
                
                # Create grid using unified processor
                result_path = grid_processor.create_2x2_grid(
                    image_paths=grid_images,
                    output_path=output_path,
                    grid_size=(2000, 2000),
                    padding=30
                )
                
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
                font_size=50,
                text_color=(120, 120, 120),
                opacity=80,
                diagonal_spacing=350
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
        
        # Create mocks folder inside the input directory (like patterns)
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
        """Generate clipart-specific content for Etsy listings."""
        if not self.ai_provider:
            return {}
        
        try:
            # Find a representative image for analysis
            image_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            
            if not image_files:
                self.logger.warning("No images found for content generation")
                return {}
            
            representative_image = image_files[0]  # Use first image
            
            # Generate title
            title_prompt = """
            Analyze this clipart/illustration image and create a compelling Etsy listing title.
            The title should be SEO-optimized, descriptive, and under 140 characters.
            Focus on the illustration style, subject matter, and potential uses.
            Return only the title, nothing else.
            """
            
            title = generate_content_with_ai(
                self.ai_provider,
                title_prompt,
                representative_image
            )
            
            # Generate description
            description_prompt = """
            Create a detailed Etsy listing description for this clipart/illustration set.
            Include:
            - Description of the illustrations/clipart
            - Style and artistic approach
            - Suggested uses (digital scrapbooking, crafts, design projects)
            - Technical details (PNG format, transparent background, high resolution)
            - Commercial use information
            
            Keep it engaging and SEO-friendly.
            """
            
            description = generate_content_with_ai(
                self.ai_provider,
                description_prompt,
                representative_image
            )
            
            # Generate tags
            tags_prompt = """
            Generate 13 relevant Etsy tags for this clipart/illustration set.
            Focus on:
            - Subject matter/theme
            - Style keywords
            - Uses/applications
            - Format details
            
            Return only comma-separated tags, nothing else.
            """
            
            tags_text = generate_content_with_ai(
                self.ai_provider,
                tags_prompt,
                representative_image
            )
            
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()][:13]
            
            # Count images for description enhancement
            image_count = len(image_files)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category": "Digital",
                "subcategory": "Clipart",
                "image_count": image_count,
                "image_analyzed": representative_image
            }
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return {"error": str(e)}
    
    def extract_from_sheets(self) -> Dict[str, Any]:
        """Extract individual clipart from sprite sheets - custom workflow step."""
        try:
            from src.products.clipart.utils import extract_clipart_from_sheets
            
            extracted_dir = os.path.join(self.config.output_dir, "extracted")
            ensure_directory(extracted_dir)
            
            return extract_clipart_from_sheets(
                input_folder=self.config.input_dir,
                output_folder=extracted_dir
            )
            
        except Exception as e:
            self.logger.error(f"Clipart extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_videos(self) -> Dict[str, Any]:
        """Create videos using unified video processor."""
        try:
            video_processor = VideoProcessor("clipart")
            video_path = video_processor.create_product_showcase_video(self.config.input_dir)
            
            if video_path:
                self.logger.info(f"Video created: {video_path}")
                return {"success": True, "file": video_path}
            else:
                return {"success": False, "error": "Failed to create video"}
                
        except Exception as e:
            self.logger.error(f"Video creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def process_custom_step(self, step: str) -> Dict[str, Any]:
        """Process clipart-specific custom steps."""
        if step == "extract":
            return self.extract_from_sheets()
        
        return super().process_custom_step(step)