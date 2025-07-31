"""
Base processor class for all product types.
Provides common interface and workflow orchestration.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Protocol
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from src.utils.common import setup_logging, ensure_dir_exists
from src.utils.ai_utils import get_ai_provider


class WorkflowStep(Enum):
    """Enumeration of available workflow steps."""
    RESIZE = "resize"
    MOCKUP = "mockup"
    VIDEO = "video"
    ZIP = "zip"
    ETSY_CONTENT = "etsy_content"


class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


class ConfigurationError(ProcessingError):
    """Exception raised for configuration-related errors."""
    pass


class ValidationError(ProcessingError):
    """Exception raised for validation errors."""
    pass


@dataclass
class ProcessingConfig:
    """Configuration for processing operations.
    
    Args:
        product_type: The type of product being processed
        input_dir: Input directory containing source files
        output_dir: Output directory for processed files
        ai_provider: AI provider to use for content generation
        create_video: Whether to create video content
        create_zip: Whether to create ZIP archives
        watermark_opacity: Opacity level for watermarks (0-255)
        custom_settings: Additional product-specific settings
        
    Raises:
        ValidationError: If configuration parameters are invalid
    """
    product_type: str
    input_dir: Union[str, Path]
    output_dir: Union[str, Path]
    ai_provider: str = "gemini"
    create_video: bool = True
    create_zip: bool = True
    watermark_opacity: int = 100
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_config()
        
        # Convert paths to strings for backward compatibility
        self.input_dir = str(self.input_dir)
        self.output_dir = str(self.output_dir)
    
    def _validate_config(self) -> None:
        """Validate configuration parameters.
        
        Raises:
            ValidationError: If any configuration parameter is invalid
        """
        if not self.product_type or not isinstance(self.product_type, str):
            raise ValidationError("product_type must be a non-empty string")
            
        if not self.input_dir:
            raise ValidationError("input_dir must be specified")
            
        if not self.output_dir:
            raise ValidationError("output_dir must be specified")
            
        if not isinstance(self.watermark_opacity, int) or not (0 <= self.watermark_opacity <= 255):
            raise ValidationError("watermark_opacity must be an integer between 0 and 255")
            
        if self.ai_provider not in ["gemini", "openai"]:
            raise ValidationError(f"Unsupported ai_provider: {self.ai_provider}. Must be 'gemini' or 'openai'")


class BaseProcessor(ABC):
    """Base class for all product type processors."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = setup_logging(f"{config.product_type}_processor")
        self.ai_provider = get_ai_provider(config.ai_provider)
        
        # Ensure output directory exists
        ensure_dir_exists(config.output_dir)
    
    def run_workflow(self, steps: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run the complete processing workflow.
        
        Args:
            steps: List of workflow steps to execute. If None, runs default steps.
            
        Returns:
            Dict containing results of each step with success/error status
            
        Raises:
            ProcessingError: If workflow execution fails
            ValidationError: If workflow steps are invalid
        """
        if steps is None:
            steps = self.get_default_workflow_steps()
            
        self._validate_workflow_steps(steps)
        results: Dict[str, Any] = {}
        
        try:
            for step in steps:
                step_name = step.replace("_", " ").title()
                self.logger.info(f"Processing {step_name}...")
                
                try:
                    result = self._execute_workflow_step(step)
                    results[step] = result
                    
                    # Check if step was successful
                    if isinstance(result, dict):
                        if result.get("success", True):
                            self.logger.info(f"✓ {step_name} completed successfully")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            self.logger.error(f"✗ {step_name} failed: {error_msg}")
                    else:
                        self.logger.info(f"✓ {step_name} completed")
                        
                except Exception as step_error:
                    error_msg = f"Step '{step}' failed: {str(step_error)}"
                    self.logger.error(f"✗ {error_msg}")
                    results[step] = {"success": False, "error": str(step_error)}
                    # Continue with remaining steps instead of failing entirely
        
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            self.logger.error(f"✗ {error_msg}")
            raise ProcessingError(error_msg) from e
        
        return results
    
    def _validate_workflow_steps(self, steps: List[str]) -> None:
        """Validate that workflow steps are valid.
        
        Args:
            steps: List of workflow steps to validate
            
        Raises:
            ValidationError: If any step is invalid
        """
        if not isinstance(steps, list):
            raise ValidationError("Workflow steps must be a list")
            
        valid_steps = {step.value for step in WorkflowStep} | {"custom"}
        for step in steps:
            if not isinstance(step, str):
                raise ValidationError(f"Workflow step must be a string, got {type(step)}")
            # Allow custom steps that start with underscore or contain custom logic
            if step not in valid_steps and not step.startswith("_") and "custom" not in step.lower():
                self.logger.warning(f"Unknown workflow step: {step}. It will be processed as a custom step.")
    
    def _execute_workflow_step(self, step: str) -> Dict[str, Any]:
        """Execute a single workflow step.
        
        Args:
            step: The workflow step to execute
            
        Returns:
            Result dictionary with success status and data
            
        Raises:
            ProcessingError: If step execution fails
        """
        if step == WorkflowStep.RESIZE.value:
            return self.resize_images()
        elif step == WorkflowStep.MOCKUP.value:
            return self.create_mockups()
        elif step == WorkflowStep.VIDEO.value:
            return self.create_videos()
        elif step == WorkflowStep.ZIP.value:
            if self.config.create_zip:
                return self.create_zip_files()
            else:
                return {"success": True, "message": "ZIP creation disabled in configuration"}
        elif step == WorkflowStep.ETSY_CONTENT.value:
            return self.generate_etsy_content()
        else:
            return self.process_custom_step(step)
    
    @abstractmethod
    def get_default_workflow_steps(self) -> List[str]:
        """Return the default workflow steps for this processor type.
        
        Returns:
            List of default workflow step names
        """
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
        """Create promotional videos using unified video processor.
        
        Returns:
            Dict with success status and video file path or error message
        """
        try:
            from src.services.processing.video import VideoProcessor
            
            if not os.path.exists(self.config.input_dir):
                raise ValidationError(f"Input directory does not exist: {self.config.input_dir}")
            
            video_processor = VideoProcessor(self.config.product_type)
            video_path = video_processor.create_product_showcase_video(self.config.input_dir)
            
            if video_path and os.path.exists(video_path):
                self.logger.info(f"Video created: {video_path}")
                return {"success": True, "file": video_path}
            else:
                return {"success": False, "error": "Video creation failed - no output file generated"}
                
        except ImportError as e:
            error_msg = f"Video processor module not available: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Video creation failed: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
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
        
        # Note: Etsy API does not support setting attributes via API, so no custom attributes are generated
        
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
        """Count product images excluding mockups and system files.
        
        Returns:
            Number of valid product images found
        """
        try:
            from src.utils.file_operations import find_files_by_extension
            
            if not os.path.exists(self.config.input_dir):
                self.logger.warning(f"Input directory does not exist: {self.config.input_dir}")
                return 0
            
            image_files = find_files_by_extension(self.config.input_dir, ['.png', '.jpg', '.jpeg'])
            
            # Exclude files in specific directories and system files
            excluded_patterns = ['/mocks/', '\\mocks\\', '/.DS_Store', 'Thumbs.db', '/temp/', '\\temp\\']
            product_images = [
                f for f in image_files 
                if not any(pattern in f for pattern in excluded_patterns)
            ]
            
            return len(product_images)
            
        except Exception as e:
            self.logger.error(f"Error counting product images: {e}")
            return 0
    
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