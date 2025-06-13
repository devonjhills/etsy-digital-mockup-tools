"""Journal papers processor implementation."""

import os
from typing import Dict, List, Any, Tuple
from pathlib import Path
from PIL import Image, ImageDraw

from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor
from src.utils.ai_utils import generate_content_with_ai
from src.utils.file_operations import find_files_by_extension, ensure_directory
from src.services.processing.video.base import VideoProcessor
from src.utils.common import apply_watermark


@register_processor("journal_papers")
class JournalPapersProcessor(BaseProcessor):
    """Processor for journal papers processing."""

    def get_default_workflow_steps(self) -> List[str]:
        """Return default workflow steps for journal papers."""
        return ["resize", "mockup", "video", "zip"]

    def resize_images(self) -> Dict[str, Any]:
        """Resize journal paper images to 8.5x11 inches (2550x3300 pixels at 300 DPI)."""
        try:
            # Journal paper dimensions: 8.5x11 inches at 300 DPI
            TARGET_WIDTH = 2550  # 8.5 inches * 300 DPI
            TARGET_HEIGHT = 3300  # 11 inches * 300 DPI
            DPI = (300, 300)

            total_processed = 0
            total_errors = 0
            processed_details = []

            # Get all image files in the input directory
            image_files = find_files_by_extension(
                self.config.input_dir,
                [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"],
            )

            if not image_files:
                return {"success": False, "error": "No image files found"}

            # Process images by subfolder (like patterns/cliparts)
            subfolders = {}
            for image_path in image_files:
                # Skip files in special folders
                if "/mocks/" in image_path or "\\mocks\\" in image_path:
                    continue
                if "/zipped/" in image_path or "\\zipped\\" in image_path:
                    continue

                # Determine subfolder
                relative_path = os.path.relpath(image_path, self.config.input_dir)
                if os.path.dirname(relative_path):
                    subfolder = os.path.dirname(relative_path).split(os.sep)[0]
                else:
                    # Direct files in input directory
                    subfolder = Path(self.config.input_dir).name

                if subfolder not in subfolders:
                    subfolders[subfolder] = []
                subfolders[subfolder].append(image_path)

            self.logger.info(f"Found {len(subfolders)} subfolder(s) to process")

            for subfolder, files in subfolders.items():
                self.logger.info(
                    f"Processing subfolder: {subfolder} ({len(files)} files)"
                )

                # Sort files by filename for consistent ordering
                files.sort(key=lambda x: os.path.basename(x))

                for i, image_path in enumerate(files, 1):
                    try:
                        original_filename = os.path.basename(image_path)
                        self.logger.info(f"Processing {original_filename}")

                        # Open and process the image
                        with Image.open(image_path) as img:
                            # Convert to RGB if needed (for JPEG compatibility)
                            if img.mode in ("RGBA", "LA"):
                                # For transparent images, convert to white background
                                background = Image.new("RGB", img.size, (255, 255, 255))
                                if img.mode == "RGBA":
                                    background.paste(img, mask=img.split()[-1])
                                else:
                                    background.paste(img, mask=img.split()[-1])
                                img = background
                            elif img.mode != "RGB":
                                img = img.convert("RGB")

                            # Step 1: Scale down to target width (2550 pixels) maintaining aspect ratio
                            original_width, original_height = img.size
                            scale_factor = TARGET_WIDTH / original_width
                            new_height = int(original_height * scale_factor)

                            # Resize to target width
                            img_resized = img.resize(
                                (TARGET_WIDTH, new_height), Image.Resampling.LANCZOS
                            )

                            # Step 2: Crop to target height (3300 pixels)
                            if new_height >= TARGET_HEIGHT:
                                # Crop from center if image is taller than target
                                crop_top = (new_height - TARGET_HEIGHT) // 2
                                crop_bottom = crop_top + TARGET_HEIGHT
                                img_final = img_resized.crop(
                                    (0, crop_top, TARGET_WIDTH, crop_bottom)
                                )
                            else:
                                # Pad with white if image is shorter than target
                                img_final = Image.new(
                                    "RGB",
                                    (TARGET_WIDTH, TARGET_HEIGHT),
                                    (255, 255, 255),
                                )
                                paste_y = (TARGET_HEIGHT - new_height) // 2
                                img_final.paste(img_resized, (0, paste_y))

                            # Create output filename using subfolder name + index
                            safe_subfolder_name = "".join(
                                c for c in subfolder if c.isalnum() or c in "_-"
                            )
                            output_filename = f"{safe_subfolder_name}_{i}.jpg"

                            # Determine output path (same directory as input for subfolder processing)
                            if os.path.dirname(
                                os.path.relpath(image_path, self.config.input_dir)
                            ):
                                # File is in a subfolder
                                output_path = os.path.join(
                                    os.path.dirname(image_path), output_filename
                                )
                            else:
                                # File is directly in input directory
                                output_path = os.path.join(
                                    self.config.input_dir, output_filename
                                )

                            # Save the processed image
                            img_final.save(
                                output_path, format="JPEG", quality=95, dpi=DPI
                            )

                            # Remove original if different from output
                            if os.path.abspath(image_path) != os.path.abspath(
                                output_path
                            ):
                                try:
                                    os.remove(image_path)
                                except Exception as e:
                                    self.logger.warning(
                                        f"Could not remove original file {image_path}: {e}"
                                    )

                            total_processed += 1
                            processed_details.append(
                                {
                                    "original": original_filename,
                                    "output": output_filename,
                                    "original_size": f"{original_width}x{original_height}",
                                    "final_size": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
                                    "subfolder": subfolder,
                                }
                            )

                            self.logger.info(
                                f"✓ {original_filename} -> {output_filename} ({original_width}x{original_height} -> {TARGET_WIDTH}x{TARGET_HEIGHT})"
                            )

                    except Exception as e:
                        total_errors += 1
                        self.logger.error(
                            f"Error processing {os.path.basename(image_path)}: {e}"
                        )

            result = {
                "success": True,
                "processed": total_processed,
                "errors": total_errors,
                "target_dimensions": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
                "target_size_inches": "8.5x11",
                "dpi": "300",
                "processed_details": processed_details,
            }

            self.logger.info(
                f"Journal papers resize complete: {total_processed} processed, {total_errors} errors"
            )
            return result

        except Exception as e:
            self.logger.error(f"Journal papers resize failed: {e}")
            return {"success": False, "error": str(e)}

    def create_mockups(self) -> Dict[str, Any]:
        """Create journal papers mockups."""
        try:
            results = {}

            # Create main mockup (pattern-style with journal papers branding)
            results["main_mockup"] = self._create_main_mockup()

            # Create 2x2 grid mockups (multiple grids if >4 images)
            results["grid_mockups"] = self._create_grid_mockups()

            return results

        except Exception as e:
            self.logger.error(f"Mockup creation failed: {e}")
            return {"success": False, "error": str(e)}

    def _create_main_mockup(self) -> Dict[str, Any]:
        """Create main journal papers mockup using shared utility."""
        from src.utils.mockup_utils import create_shared_main_mockup

        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)

        # Generate title from folder name
        folder_name = Path(self.config.input_dir).name
        title = folder_name.replace("_", " ").replace("-", " ").title()

        try:
            # Count images for subtitle
            image_files = find_files_by_extension(
                self.config.input_dir, [".jpg", ".jpeg", ".png"]
            )
            image_files = [
                f for f in image_files if "/mocks/" not in f and "\\mocks\\" not in f
            ]
            num_images = len(image_files)

            # Create journal papers-specific subtitles
            top_subtitle = f"{num_images} Digital Journal Pages"
            bottom_subtitle = "8.5×11 inch • Printable • 300 DPI"

            result_file = create_shared_main_mockup(
                input_folder=self.config.input_dir,
                title=title,
                top_subtitle_text=top_subtitle,
                bottom_subtitle_text=bottom_subtitle,
                output_filename="main.png",
                config_type="journal_papers",
            )
            return {"success": True, "file": result_file, "output_folder": mockup_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_grid_mockups(self) -> Dict[str, Any]:
        """Create 2x2 grid mockups for journal papers (multiple grids if >4 images)."""
        mockup_dir = os.path.join(self.config.input_dir, "mocks")
        ensure_directory(mockup_dir)

        try:
            # Find all journal paper images (excluding mocks folder)
            image_files = find_files_by_extension(
                self.config.input_dir, [".jpg", ".jpeg", ".png"]
            )
            image_files = [
                f for f in image_files if "/mocks/" not in f and "\\mocks\\" not in f
            ]

            if not image_files:
                return {"success": False, "error": "No images found for mockup"}

            # Sort files for consistent ordering
            image_files.sort(key=lambda x: os.path.basename(x))

            grid_results = []

            # Create 2x2 grids (4 images per grid)
            for i in range(0, len(image_files), 4):
                batch_images = image_files[i : i + 4]
                grid_num = (i // 4) + 1

                try:
                    grid_file = self._create_2x2_grid(
                        batch_images, mockup_dir, grid_num
                    )
                    if grid_file:
                        grid_results.append(
                            {
                                "success": True,
                                "file": grid_file,
                                "grid_number": grid_num,
                                "images_count": len(batch_images),
                            }
                        )
                except Exception as e:
                    grid_results.append(
                        {"success": False, "error": str(e), "grid_number": grid_num}
                    )

            return {
                "success": True,
                "grids": grid_results,
                "total_grids": len(grid_results),
                "output_folder": mockup_dir,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_2x2_grid(
        self, image_files: List[str], mockup_dir: str, grid_num: int
    ) -> str:
        """Create a single 2x2 grid mockup."""
        # Journal paper dimensions (2550x3300)
        paper_width, paper_height = 2550, 3300

        # Calculate grid dimensions to fit 2x2 papers without warping
        # Add padding between papers and around edges
        padding = 150
        grid_width = (paper_width * 2) + (padding * 3)  # 2 papers + 3 padding spaces
        grid_height = (paper_height * 2) + (padding * 3)  # 2 papers + 3 padding spaces

        # Create the grid canvas
        grid_canvas = Image.new("RGB", (grid_width, grid_height), (245, 245, 245))

        # Position papers in 2x2 layout
        positions = [
            (padding, padding),  # Top-left
            (padding + paper_width + padding, padding),  # Top-right
            (padding, padding + paper_height + padding),  # Bottom-left
            (
                padding + paper_width + padding,
                padding + paper_height + padding,
            ),  # Bottom-right
        ]

        # Place images in grid
        for i, image_path in enumerate(image_files[:4]):  # Max 4 images for 2x2
            if i >= 4:
                break

            try:
                with Image.open(image_path) as img:
                    # Ensure image is the correct size (should be from resize step)
                    if img.size != (paper_width, paper_height):
                        img = img.resize(
                            (paper_width, paper_height), Image.Resampling.LANCZOS
                        )

                    # Paste at the calculated position
                    grid_canvas.paste(img, positions[i])

            except Exception as e:
                self.logger.warning(f"Could not add image {image_path} to grid: {e}")

        # Add subtle drop shadows
        self._add_paper_shadows(
            grid_canvas, positions[: len(image_files)], paper_width, paper_height
        )

        # Apply watermark to the grid mockup
        # Convert to RGBA for watermarking, then back to RGB
        grid_canvas_rgba = grid_canvas.convert("RGBA")
        watermarked_canvas = apply_watermark(
            image=grid_canvas_rgba,
            text="digital veil",
            font_name="DSMarkerFelt",
            text_color=(255, 255, 255),
            opacity=128,
        )
        grid_canvas = watermarked_canvas.convert("RGB")

        # Save the grid
        output_filename = f"journal_papers_grid_{grid_num}.jpg"
        output_path = os.path.join(mockup_dir, output_filename)
        grid_canvas.save(output_path, format="JPEG", quality=95)

        self.logger.info(f"Created 2x2 grid {grid_num}: {output_filename}")
        return output_path

    def _add_paper_shadows(
        self,
        canvas: Image.Image,
        positions: List[Tuple[int, int]],
        paper_width: int,
        paper_height: int,
    ):
        """Add subtle drop shadows to journal papers in the grid."""
        # Create a semi-transparent overlay for shadows
        shadow_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay)

        shadow_offset = 8
        shadow_color = (0, 0, 0, 40)  # Semi-transparent black

        for x, y in positions:
            # Draw shadow rectangle slightly offset
            shadow_draw.rectangle(
                [
                    x + shadow_offset,
                    y + shadow_offset,
                    x + paper_width + shadow_offset,
                    y + paper_height + shadow_offset,
                ],
                fill=shadow_color,
            )

        # Composite the shadow with the main canvas
        canvas_rgba = canvas.convert("RGBA")
        canvas_with_shadow = Image.alpha_composite(canvas_rgba, shadow_overlay)
        canvas.paste(canvas_with_shadow.convert("RGB"))

    def _generate_content_for_type(self) -> Dict[str, Any]:
        """Generate journal papers-specific content for Etsy listings."""
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
                self.ai_provider, DEFAULT_ETSY_INSTRUCTIONS, representative_image
            )

            # Parse the response to extract title, description, and tags
            parsed_content = parse_etsy_listing_response(ai_response)
            title = parsed_content['title']
            description = parsed_content['description']
            tags_text = parsed_content['tags']

            # Convert tags to list
            tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()][:13]

            # Generate attributes for Etsy listing
            attributes = self._generate_etsy_attributes(representative_image)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category": "Digital",
                "subcategory": "Journal Pages",
                "image_analyzed": representative_image,
                "attributes": attributes
            }

        except Exception as e:
            self.logger.error(f"Content generation failed: {e}")
            return {"error": str(e)}
    
    def _generate_etsy_attributes(self, representative_image: str) -> Dict[str, Any]:
        """Generate Etsy listing attributes for journal papers."""
        try:
            attributes = {
                "width": "8.5",
                "height": "11",
                "materials": ["Digital", "Paper"],
                "orientation": "Portrait",
                "occasion": "Everyday",
                "can_be_personalized": "No"
            }
            
            # Use AI to analyze colors and themes if available
            if self.ai_provider and representative_image:
                try:
                    # Analyze primary color
                    color_prompt = """
                    Analyze this journal page design and identify the primary color.
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
                        attributes["primary_color"] = "Blue"  # Default
                    
                    # Analyze occasion/theme
                    occasion_prompt = """
                    Analyze this journal page design and identify the most appropriate occasion or theme.
                    Choose from these options only:
                    Everyday, Wedding, Birthday, Holiday, Valentine's Day, Mother's Day, 
                    Father's Day, Graduation, Anniversary, Back to school, Christmas
                    Return only one option, nothing else.
                    """
                    
                    occasion = generate_content_with_ai(
                        self.ai_provider,
                        occasion_prompt,
                        representative_image
                    ).strip()
                    
                    valid_occasions = ["Everyday", "Wedding", "Birthday", "Holiday", "Valentine's Day", 
                                     "Mother's Day", "Father's Day", "Graduation", "Anniversary", 
                                     "Back to school", "Christmas"]
                    if occasion in valid_occasions:
                        attributes["occasion"] = occasion
                        
                except Exception as e:
                    self.logger.warning(f"Could not analyze journal page attributes: {e}")
                    attributes["primary_color"] = "Blue"  # Default
            else:
                attributes["primary_color"] = "Blue"  # Default
                
            return attributes
            
        except Exception as e:
            self.logger.error(f"Error generating Etsy attributes: {e}")
            return {
                "width": "8.5",
                "height": "11",
                "primary_color": "Blue",
                "materials": ["Digital"],
                "orientation": "Portrait",
                "can_be_personalized": "No"
            }

    def create_videos(self) -> Dict[str, Any]:
        """Create videos using unified video processor."""
        try:
            video_processor = VideoProcessor("journal_papers")
            video_path = video_processor.create_product_showcase_video(
                self.config.input_dir
            )

            if video_path:
                self.logger.info(f"Video created: {video_path}")
                return {"success": True, "file": video_path}
            else:
                return {"success": False, "error": "Failed to create video"}

        except Exception as e:
            self.logger.error(f"Video creation failed: {e}")
            return {"success": False, "error": str(e)}
