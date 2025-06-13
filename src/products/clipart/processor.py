"""Clipart processor implementation."""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension
from src.utils.common import ensure_dir_exists


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
        ensure_dir_exists(mockup_dir)
        
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
        from src.utils.grid_utils import GridCreator
        from src.utils.file_operations import find_files_by_extension
        import os
        
        # Create mocks folder inside the input directory (like patterns)
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        
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
            
            # Use the unified grid creator
            grid_creator = GridCreator()
            
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
                
                # Create grid using unified creator
                background = grid_creator.load_background("canvas.png", (2000, 2000))
                grid_image = grid_creator.create_2x2_grid(
                    image_paths=grid_images,
                    grid_size=(2000, 2000),
                    padding=30,
                    background=background
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
        from src.utils.grid_utils import apply_watermark_to_grid
        return apply_watermark_to_grid(grid_path, self.logger)
    
    def _create_transparency_demo(self) -> Dict[str, Any]:
        """Create transparency demonstration mockup."""
        from src.products.clipart.transparency import create_transparency_demo
        from src.utils.file_operations import find_files_by_extension
        import os
        
        # Create mocks folder inside the input directory (like patterns)
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_dir_exists(mockup_dir)
        
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
    
    
    def extract_from_sheets(self) -> Dict[str, Any]:
        """Extract individual clipart from sprite sheets - custom workflow step."""
        try:
            from src.products.clipart.utils import extract_clipart_from_sheets
            
            extracted_dir = os.path.join(self.config.output_dir, "extracted")
            ensure_dir_exists(extracted_dir)
            
            return extract_clipart_from_sheets(
                input_folder=self.config.input_dir,
                output_folder=extracted_dir
            )
            
        except Exception as e:
            self.logger.error(f"Clipart extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    
    def process_custom_step(self, step: str) -> Dict[str, Any]:
        """Process clipart-specific custom steps."""
        if step == "extract":
            return self.extract_from_sheets()
        
        return super().process_custom_step(step)