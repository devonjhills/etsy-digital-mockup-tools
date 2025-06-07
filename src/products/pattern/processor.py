"""Pattern processor implementation."""

import os
from typing import Dict, List, Any
from pathlib import Path

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension, ensure_directory
from src.services.processing.video import VideoProcessor


@register_processor("pattern")
class PatternProcessor(BaseProcessor):
    """Processor for seamless pattern processing."""
    
    def get_default_workflow_steps(self) -> List[str]:
        """Return default workflow steps for patterns."""
        return ["resize", "mockup", "video", "zip"]
    
    def resize_images(self) -> Dict[str, Any]:
        """Resize pattern images for processing."""
        from src.utils.resize_utils import ImageResizer
        
        try:
            resizer = ImageResizer(max_size=3600, dpi=(300, 300))
            result = resizer.resize_pattern_style(self.config.input_dir)
            
            self.logger.info(f"Resized {result.get('processed', 0)} pattern images")
            return result
            
        except Exception as e:
            self.logger.error(f"Pattern resize failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_mockups(self) -> Dict[str, Any]:
        """Create pattern mockups."""
        try:
            results = {}
            
            # Create main mockup
            results["main_mockup"] = self._create_main_mockup()
            
            # Create grid mockup
            results["grid_mockup"] = self._create_grid_mockup()
            
            # Create layered mockup if enabled
            if self.config.custom_settings.get("create_layered", True):
                results["layered_mockup"] = self._create_layered_mockup()
            
            # Create seamless tiling mockup
            results["seamless_tiling_mockup"] = self._create_seamless_tiling_mockup()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Mockup creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_main_mockup(self) -> Dict[str, Any]:
        """Create main pattern mockup."""
        from src.products.pattern.dynamic_main_mockup import create_main_mockup
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        # Generate title from folder name
        folder_name = Path(self.config.input_dir).name
        title = folder_name.replace("_", " ").replace("-", " ").title()
        
        try:
            result_file = create_main_mockup(
                input_folder=self.config.input_dir,
                title=title
            )
            return {"success": True, "file": result_file, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_grid_mockup(self) -> Dict[str, Any]:
        """Create pattern grid mockup."""
        from src.services.processing.grid import GridProcessor
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            grid_processor = GridProcessor("pattern")
            result_file = grid_processor.create_4x3_grid_with_borders(
                input_folder=self.config.input_dir
            )
            return {"success": True, "file": result_file, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_layered_mockup(self) -> Dict[str, Any]:
        """Create layered pattern mockup."""
        from src.products.pattern.layered import create_large_grid
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            result = create_large_grid(self.config.input_dir)
            return {"success": True, "files": result, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_seamless_tiling_mockup(self) -> Dict[str, Any]:
        """Create seamless tiling mockup showing 2x2 grid with 'Images tile seamlessly' text."""
        from src.products.pattern.seamless import create_seamless_tiling_mockup
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)
        
        try:
            result_file = create_seamless_tiling_mockup(self.config.input_dir)
            if result_file:
                return {"success": True, "file": result_file, "output_folder": mockup_dir}
            else:
                return {"success": False, "error": "Failed to create seamless tiling mockup"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_content_for_type(self) -> Dict[str, Any]:
        """Generate pattern-specific content for Etsy listings."""
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
            Analyze this seamless pattern image and create a compelling Etsy listing title.
            The title should be SEO-optimized, descriptive, and under 140 characters.
            Focus on the pattern style, colors, and potential uses.
            Return only the title, nothing else.
            """
            
            title = generate_content_with_ai(
                self.ai_provider,
                title_prompt,
                representative_image
            )
            
            # Generate description
            description_prompt = """
            Create a detailed Etsy listing description for this seamless pattern.
            Include:
            - Pattern description and style
            - Color palette details
            - Suggested uses (fabric, wallpaper, scrapbooking, etc.)
            - Technical details (seamless, high resolution)
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
            Generate 13 relevant Etsy tags for this seamless pattern.
            Focus on:
            - Pattern style/type
            - Colors
            - Uses/applications
            - Style keywords
            
            Return only comma-separated tags, nothing else.
            """
            
            tags_text = generate_content_with_ai(
                self.ai_provider,
                tags_prompt,
                representative_image
            )
            
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()][:13]
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category": "Digital",
                "subcategory": "Patterns",
                "image_analyzed": representative_image
            }
            
        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return {"error": str(e)}
    
    def create_seamless_pattern(self) -> Dict[str, Any]:
        """Create seamless pattern from input image - custom workflow step."""
        from src.products.pattern.seamless import create_seamless_pattern
        
        try:
            seamless_dir = os.path.join(self.config.input_dir, "seamless")
            ensure_directory(seamless_dir)
            
            return create_seamless_pattern(
                input_folder=self.config.input_dir,
                output_folder=seamless_dir
            )
            
        except Exception as e:
            self.logger.error(f"Seamless pattern creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_videos(self) -> Dict[str, Any]:
        """Create videos using unified video processor."""
        try:
            video_processor = VideoProcessor("pattern")
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
        """Process pattern-specific custom steps."""
        if step == "seamless":
            return self.create_seamless_pattern()
        
        return super().process_custom_step(step)