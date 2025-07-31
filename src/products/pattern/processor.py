"""Pattern processor implementation."""

import os
from typing import Dict, List, Any
from pathlib import Path

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension
from src.utils.common import ensure_dir_exists


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
            
            # Create Pinterest mockup
            results["pinterest_mockup"] = self._create_pinterest_mockup()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Mockup creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_main_mockup(self) -> Dict[str, Any]:
        """Create main pattern mockup using shared utility."""
        from src.utils.mockup_utils import create_shared_main_mockup
        
        mockup_dir = self._setup_mockup_directory()
        title = self._generate_title_from_folder()
        num_images = self._count_product_images()
        
        # Pattern-specific subtitle text
        top_subtitle_text = f"{num_images} Seamless Patterns"
        bottom_subtitle_text = "commercial use | 300 dpi | 12x12in jpg"
        
        try:
            result_file = create_shared_main_mockup(
                input_folder=self.config.input_dir,
                title=title,
                top_subtitle_text=top_subtitle_text,
                bottom_subtitle_text=bottom_subtitle_text,
                output_filename="main.png",
                config_type="pattern"
            )
            return {"success": True, "file": result_file, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_grid_mockup(self) -> Dict[str, Any]:
        """Create pattern grid mockup."""
        from src.utils.grid_utils import GridCreator
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        
        try:
            grid_creator = GridCreator()
            result_file = grid_creator.create_4x3_grid_with_borders(
                input_folder=self.config.input_dir
            )
            return {"success": True, "file": result_file, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_layered_mockup(self) -> Dict[str, Any]:
        """Create layered pattern mockup."""
        from src.products.pattern.layered import create_large_grid
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        
        try:
            result = create_large_grid(self.config.input_dir)
            return {"success": True, "files": result, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_seamless_tiling_mockup(self) -> Dict[str, Any]:
        """Create seamless tiling mockup showing 2x2 grid with 'Images tile seamlessly' text."""
        from src.products.pattern.seamless import create_seamless_tiling_mockup
        
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        
        try:
            result_file = create_seamless_tiling_mockup(self.config.input_dir)
            if result_file:
                return {"success": True, "file": result_file, "output_folder": mockup_dir}
            else:
                return {"success": False, "error": "Failed to create seamless tiling mockup"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_pinterest_mockup(self) -> Dict[str, Any]:
        """Create Pinterest-optimized vertical mockup for patterns."""
        try:
            from src.services.processing.mockups.base import MockupProcessor
            
            mockup_processor = MockupProcessor(product_type="pattern")
            
            # Get product title from folder name
            folder_name = os.path.basename(self.config.input_dir)
            title = folder_name.replace('_', ' ').replace('-', ' ').title()
            
            # Prepare product data
            product_data = {
                'title': title,
                'description': f'Beautiful seamless {title.lower()} pattern for digital crafting',
                'product_type': 'pattern'
            }
            
            result_file = mockup_processor.create_pinterest_mockup(
                self.config.input_dir, 
                title,
                product_data
            )
            
            if result_file:
                return {"success": True, "file": result_file, "output_folder": os.path.dirname(result_file)}
            else:
                return {"success": False, "error": "Failed to create Pinterest mockup"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_seamless_pattern(self) -> Dict[str, Any]:
        """Create seamless pattern from input image - custom workflow step."""
        from src.products.pattern.seamless import create_seamless_pattern
        
        try:
            seamless_dir = os.path.join(self.config.input_dir, "seamless")
            ensure_dir_exists(seamless_dir)
            
            return create_seamless_pattern(
                input_folder=self.config.input_dir,
                output_folder=seamless_dir
            )
            
        except Exception as e:
            self.logger.error(f"Seamless pattern creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    
    def process_custom_step(self, step: str) -> Dict[str, Any]:
        """Process pattern-specific custom steps."""
        if step == "seamless":
            return self.create_seamless_pattern()
        
        return super().process_custom_step(step)