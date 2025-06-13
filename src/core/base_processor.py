"""
Base processor class for all product types.
Provides common interface and workflow orchestration.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.utils.common import setup_logging, ensure_dir_exists
from src.utils.ai_utils import get_ai_provider


@dataclass
class ProcessingConfig:
    """Configuration for processing operations."""
    product_type: str
    input_dir: str
    output_dir: str
    ai_provider: str = "gemini"
    create_video: bool = True
    create_zip: bool = True
    watermark_opacity: int = 100
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_settings is None:
            self.custom_settings = {}


class BaseProcessor(ABC):
    """Base class for all product type processors."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = setup_logging(f"{config.product_type}_processor")
        self.ai_provider = get_ai_provider(config.ai_provider)
        
        # Ensure output directory exists
        ensure_dir_exists(config.output_dir)
    
    def run_workflow(self, steps: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete processing workflow.
        
        Args:
            steps: List of workflow steps to execute. If None, runs all steps.
            
        Returns:
            Dict containing results of each step
        """
        if steps is None:
            steps = self.get_default_workflow_steps()
        
        results = {}
        
        try:
            for step in steps:
                step_name = step.replace("_", " ").title()
                self.logger.info(f"Processing {step_name}...")
                
                if step == "resize":
                    results[step] = self.resize_images()
                elif step == "mockup":
                    results[step] = self.create_mockups()
                elif step == "video":
                    results[step] = self.create_videos()
                elif step == "zip":
                    if self.config.create_zip:
                        results[step] = self.create_zip_files()
                elif step == "etsy_content":
                    results[step] = self.generate_etsy_content()
                else:
                    results[step] = self.process_custom_step(step)
                
                # Check if step was successful
                step_result = results[step]
                if isinstance(step_result, dict):
                    if step_result.get("success", True):
                        self.logger.info(f"✓ {step_name} completed successfully")
                    else:
                        self.logger.error(f"✗ {step_name} failed: {step_result.get('error', 'Unknown error')}")
                else:
                    self.logger.info(f"✓ {step_name} completed")
        
        except Exception as e:
            self.logger.error(f"✗ Workflow failed at {step.replace('_', ' ').title()}: {str(e)}")
            raise
        
        return results
    
    @abstractmethod
    def get_default_workflow_steps(self) -> List[str]:
        """Return the default workflow steps for this processor type."""
        pass
    
    @abstractmethod
    def resize_images(self) -> Dict[str, Any]:
        """Resize and prepare images for processing."""
        pass
    
    @abstractmethod
    def create_mockups(self) -> Dict[str, Any]:
        """Create mockup images."""
        pass
    
    def create_videos(self) -> Dict[str, Any]:
        """Create promotional videos using unified video processor."""
        try:
            from src.services.processing.video import VideoProcessor
            
            video_processor = VideoProcessor(self.config.product_type)
            video_path = video_processor.create_product_showcase_video(self.config.input_dir)
            
            if video_path:
                self.logger.info(f"Video created: {video_path}")
                return {"success": True, "file": video_path}
            else:
                return {"success": False, "error": "Failed to create video"}
                
        except Exception as e:
            self.logger.error(f"Video creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_zip_files(self) -> Dict[str, Any]:
        """Create ZIP files for download with intelligent splitting to stay under 20MB per Etsy limits."""
        from src.utils.file_operations import create_smart_zip_files
        import os
        
        # Create zipped folder within the input directory
        zipped_dir = os.path.join(self.config.input_dir, "zipped")
        
        # Use the smart ZIP creation utility
        result = create_smart_zip_files(
            source_dir=self.config.input_dir,
            output_dir=zipped_dir,
            max_size_mb=20.0,
            exclude_patterns=["mocks", "zipped", "videos", "seamless", ".DS_Store", "Thumbs.db"]
        )
        
        # Add output folder info for compatibility
        if result.get("success"):
            result["output_folder"] = zipped_dir
        
        return result
    
    def generate_etsy_content(self) -> Dict[str, Any]:
        """Generate Etsy listing content using AI."""
        if not self.ai_provider:
            self.logger.warning("No AI provider available for content generation")
            return {}
        
        # Use centralized content generator to avoid code duplication
        from src.services.etsy.content_generator import generate_etsy_content
        
        # Get product-specific category and subcategory
        category, subcategory = self._get_etsy_categories()
        
        # Generate content using unified logic
        content = generate_etsy_content(
            input_dir=self.config.input_dir,
            ai_provider=self.ai_provider,
            product_type=self.config.product_type,
            category=category,
            subcategory=subcategory,
            logger=self.logger
        )
        
        # Allow processors to add custom attributes
        if content and not content.get("error"):
            custom_attributes = self._generate_custom_attributes(content.get("image_analyzed"))
            if custom_attributes:
                content["attributes"] = custom_attributes
        
        return content
    
    def _get_etsy_categories(self) -> tuple[str, Optional[str]]:
        """Get Etsy category and subcategory for this product type."""
        # Default mapping for common product types
        category_map = {
            "pattern": ("Digital", "Patterns"),
            "clipart": ("Digital", "Clipart"),
            "border_clipart": ("Digital", "Clipart"),
            "journal_papers": ("Digital", "Papers"),
            "wall_art": ("Digital", "Wall Art")
        }
        
        return category_map.get(self.config.product_type, ("Digital", None))
    
    def _generate_custom_attributes(self, representative_image: Optional[str]) -> Dict[str, Any]:
        """Generate custom attributes for Etsy listings. Override in subclasses."""
        _ = representative_image  # Suppress unused parameter warning
        return {}
    
    # Common helper methods to eliminate duplication across processors
    
    def _setup_mockup_directory(self) -> str:
        """Set up and return the mockup directory path."""
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        return mockup_dir
    
    def _generate_title_from_folder(self) -> str:
        """Generate a title from the folder name."""
        from pathlib import Path
        
        folder_name = Path(self.config.input_dir).name
        return folder_name.replace("_", " ").replace("-", " ").title()
    
    def _count_product_images(self) -> int:
        """Count product images excluding mockups."""
        from src.utils.file_operations import find_files_by_extension
        
        image_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
        # Exclude files in mocks directory
        product_images = [
            f for f in image_files 
            if '/mocks/' not in f and '\\mocks\\' not in f
        ]
        return len(product_images)
    
    def _analyze_primary_color_with_ai(self, representative_image: str) -> str:
        """Analyze primary color using AI with common validation."""
        if not self.ai_provider or not representative_image:
            return "Blue"  # Default fallback
        
        try:
            from src.utils.ai_utils import generate_content_with_ai
            
            color_prompt = """
            Analyze this image and identify the primary color.
            Return only one of these exact color names:
            Red, Orange, Yellow, Green, Blue, Purple, Pink, Black, White, Gray, Brown, Beige
            Return only the color name, nothing else.
            """
            
            primary_color = generate_content_with_ai(
                self.ai_provider,
                color_prompt,
                representative_image
            ).strip()
            
            # Validate against allowed colors
            allowed_colors = ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", 
                            "Pink", "Black", "White", "Gray", "Brown", "Beige"]
            
            return primary_color if primary_color in allowed_colors else "Blue"
            
        except Exception as e:
            self.logger.error(f"Error analyzing primary color: {e}")
            return "Blue"
    
    def _apply_watermark_to_grid(self, grid_path: str) -> Optional[str]:
        """Apply watermark to a grid mockup using unified function."""
        from src.utils.grid_utils import apply_watermark_to_grid
        return apply_watermark_to_grid(grid_path, self.logger)
    
    def process_custom_step(self, step: str) -> Dict[str, Any]:
        """Process custom workflow steps. Override in subclasses."""
        self.logger.warning(f"Unknown workflow step: {step}")
        return {}
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing results."""
        return {
            "product_type": self.config.product_type,
            "input_dir": self.config.input_dir,
            "output_dir": self.config.output_dir,
            "config": self.config
        }