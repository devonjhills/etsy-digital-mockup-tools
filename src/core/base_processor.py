"""
Base processor class for all product types.
Provides common interface and workflow orchestration.
"""

import os
import logging
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
                self.logger.info(f"Starting step: {step}")
                
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
                
                self.logger.info(f"Completed step: {step}")
        
        except Exception as e:
            self.logger.error(f"Workflow failed at step {step}: {str(e)}")
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
        """Create promotional videos. Default implementation."""
        logger.warning("Video creation not implemented for this processor type")
        return {"videos": [], "success": False}
    
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
        
        # This will be implemented by specific processors
        return self._generate_content_for_type()
    
    @abstractmethod
    def _generate_content_for_type(self) -> Dict[str, Any]:
        """Generate type-specific content for Etsy listings."""
        pass
    
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