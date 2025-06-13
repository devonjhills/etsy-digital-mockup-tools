"""
Unified video creation utilities for all product types.
"""

import os
from typing import List, Tuple, Optional

from src.utils.common import setup_logging, safe_load_image, ensure_dir_exists

logger = setup_logging(__name__)


def validate_video_for_etsy(video_path: str) -> Tuple[bool, str]:
    """
    Validate video file for Etsy upload requirements.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(video_path):
        return False, f"Video file not found: {video_path}"
    
    # Check file size (Etsy limit: 100MB)
    file_size = os.path.getsize(video_path)
    max_size = 100 * 1024 * 1024  # 100MB in bytes
    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        return False, f"Video file too large: {size_mb:.1f}MB (max 100MB)"
    
    # Check video duration using OpenCV (if available)
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False, f"Cannot open video file: {video_path}"
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        if fps > 0:
            duration = frame_count / fps
            if duration < 5.0:
                return False, f"Video too short: {duration:.1f}s (min 5s for Etsy)"
            elif duration > 15.0:
                return False, f"Video too long: {duration:.1f}s (max 15s for Etsy)"
        
    except ImportError:
        logger.warning("OpenCV not available for video duration validation")
    except Exception as e:
        logger.warning(f"Could not validate video duration: {e}")
    
    return True, "Video validation passed"


class VideoCreator:
    """Unified video creator for different product types."""
    
    def __init__(self):
        self.opencv_available = self._check_opencv()
    
    def _check_opencv(self) -> bool:
        """Check if OpenCV is available."""
        try:
            import cv2
            return True
        except ImportError:
            logger.warning("OpenCV (cv2) is not installed. Video creation will be disabled.")
            logger.info("Install using: pip install opencv-python")
            return False
    
    def create_slideshow_video(self, image_paths: List[str], output_path: str,
                              target_size: Tuple[int, int] = (2000, 2000),
                              fps: int = 30, display_frames: int = 90,
                              transition_frames: int = 30,
                              preserve_original_size: bool = False) -> bool:
        """
        Create a slideshow video from images (suitable for clipart).
        
        Args:
            image_paths: List of image paths
            output_path: Where to save the video
            target_size: Target video size (ignored if preserve_original_size=True)
            fps: Frames per second
            display_frames: Frames to display each image
            transition_frames: Frames for transitions
            preserve_original_size: If True, use the size of the first image
            
        Returns:
            True if successful, False otherwise
        """
        if not self.opencv_available:
            return False
        
        if not image_paths:
            logger.warning("No image paths provided for slideshow video")
            return False
        
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("OpenCV not available for video creation")
            return False
        
        logger.info(f"Creating slideshow video: {output_path}")
        
        # Determine video size
        if preserve_original_size and image_paths:
            # Use the size of the first image
            first_img = safe_load_image(image_paths[0])
            if first_img:
                target_size = first_img.size
                logger.info(f"Using original image size for video: {target_size}")
            else:
                logger.warning("Could not load first image, using default target size")
        
        # Ensure output directory exists
        ensure_dir_exists(os.path.dirname(output_path))
        
        # Create videos folder for Etsy integration
        input_folder = os.path.dirname(os.path.dirname(output_path))
        videos_folder = os.path.join(input_folder, "videos")
        ensure_dir_exists(videos_folder)
        
        # Path for the video in the videos folder
        videos_output_path = os.path.join(videos_folder, os.path.basename(output_path))
        
        # Create video writer with avc1 codec for better compatibility  
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        video_writer = cv2.VideoWriter(videos_output_path, fourcc, fps, target_size)
        
        if not video_writer.isOpened():
            logger.error(f"Failed to open video writer for {videos_output_path}")
            return False
        
        # Load and prepare images
        cv_images = []
        for img_path in image_paths:
            try:
                # Load with PIL first for better format support
                pil_img = safe_load_image(img_path)
                if not pil_img:
                    logger.warning(f"Failed to load image: {img_path}")
                    continue
                
                # Convert to RGB if needed
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                
                # Resize to target size
                pil_img = pil_img.resize(target_size, resample=1)  # LANCZOS
                
                # Convert to OpenCV format
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                cv_images.append(cv_img)
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {e}")
        
        if not cv_images:
            logger.warning("No valid images loaded for video")
            video_writer.release()
            return False
        
        # Calculate minimum frames needed for Etsy (5 seconds minimum, 15 seconds maximum)
        min_frames_for_etsy = 5 * fps
        max_frames_for_etsy = 15 * fps
        frames_per_cycle = len(cv_images) * (display_frames + transition_frames)
        
        # Calculate cycles needed to meet minimum duration but not exceed maximum
        cycles_needed = max(1, min_frames_for_etsy // frames_per_cycle + 1)
        total_frames_with_cycles = cycles_needed * frames_per_cycle
        
        # If cycles would exceed 15 seconds, reduce to fit within limit
        if total_frames_with_cycles > max_frames_for_etsy:
            cycles_needed = max(1, max_frames_for_etsy // frames_per_cycle)
            # If even 1 cycle is too long, reduce display frames per image
            if cycles_needed == 1 and frames_per_cycle > max_frames_for_etsy:
                available_frames_per_image = max_frames_for_etsy // len(cv_images)
                display_frames = max(10, available_frames_per_image - transition_frames)
                frames_per_cycle = len(cv_images) * (display_frames + transition_frames)
                logger.info(f"Reduced display frames to {display_frames} to fit 15s limit")
        
        final_duration = (cycles_needed * frames_per_cycle) / fps
        logger.info(f"Creating video with {cycles_needed} cycles, estimated duration: {final_duration:.1f}s")
        
        # Create frames
        try:
            for cycle in range(cycles_needed):
                for i in range(len(cv_images)):
                    current_img = cv_images[i]
                    next_img = cv_images[(i + 1) % len(cv_images)]
                    
                    # Display current image
                    for _ in range(display_frames):
                        video_writer.write(current_img)
                    
                    # Transition to next image
                    for j in range(transition_frames):
                        alpha = j / transition_frames
                        blended = cv2.addWeighted(current_img, 1 - alpha, next_img, alpha, 0)
                        video_writer.write(blended)
            
            video_writer.release()
            
            success = (
                os.path.exists(videos_output_path)
                and os.path.getsize(videos_output_path) > 0
            )
            
            if success:
                logger.info(f"Slideshow video created: {videos_output_path}")
                return True
            else:
                logger.error(f"Video file was created but is empty: {videos_output_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating slideshow video: {e}")
            video_writer.release()
            return False
    
    def create_zoom_video(self, image_path: str, output_path: str,
                         fps: int = 30, total_frames: int = 300,
                         initial_zoom: float = 1.5) -> bool:
        """
        Create a zoom video from a single image (suitable for patterns).
        
        Args:
            image_path: Path to the image
            output_path: Where to save the video
            fps: Frames per second
            total_frames: Total number of frames
            initial_zoom: Initial zoom level
            
        Returns:
            True if successful, False otherwise
        """
        if not self.opencv_available:
            return False
        
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return False
        
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available for video creation")
            return False
        
        logger.info(f"Creating zoom video: {output_path}")
        
        # Ensure output directory exists
        ensure_dir_exists(os.path.dirname(output_path))
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"OpenCV could not read image: {image_path}")
                return False
            
            height, width = img.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            
            video = cv2.VideoWriter(output_path, fourcc, float(fps), (width, height))
            
            if not video.isOpened():
                logger.error(f"Failed to open video writer for {output_path}")
                return False
            
            for i in range(total_frames):
                # Calculate zoom factor for current frame
                t = i / (total_frames - 1) if total_frames > 1 else 0
                zoom_factor = initial_zoom - (initial_zoom - 1) * t
                
                if zoom_factor <= 0:
                    continue
                
                # Calculate crop dimensions
                new_w = int(width / zoom_factor)
                new_h = int(height / zoom_factor)
                x1 = max(0, (width - new_w) // 2)
                y1 = max(0, (height - new_h) // 2)
                
                # Ensure dimensions are valid
                new_w = min(new_w, width - x1)
                new_h = min(new_h, height - y1)
                
                if new_w <= 0 or new_h <= 0:
                    continue
                
                # Crop and resize
                crop = img[y1:y1 + new_h, x1:x1 + new_w]
                
                if crop is not None and crop.size > 0:
                    frame = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)
                    video.write(frame)
            
            video.release()
            
            success = (
                os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            )
            
            if success:
                logger.info(f"Zoom video created: {output_path}")
                return True
            else:
                logger.error(f"Video file was created but is empty: {output_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating zoom video: {e}")
            return False
    
    def create_tiling_video(self, image_path: str, output_path: str,
                           fps: int = 30, total_duration: int = 8) -> bool:
        """
        Create a progressive tiling video showing 2x2 grid building up one tile at a time.
        
        Args:
            image_path: Path to the image to tile
            output_path: Where to save the video
            fps: Frames per second
            total_duration: Total video duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.opencv_available:
            return False
        
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return False
        
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("OpenCV not available for video creation")
            return False
        
        logger.info(f"Creating tiling video: {output_path}")
        
        # Ensure output directory exists
        ensure_dir_exists(os.path.dirname(output_path))
        
        try:
            # Load and prepare the source image using PIL first
            from PIL import Image, ImageDraw, ImageFont
            from utils.common import get_font
            
            pil_img = safe_load_image(image_path)
            if not pil_img:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            # Convert to RGB if needed
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            
            # Video dimensions
            video_size = (1000, 1000)
            tile_size = (video_size[0] // 2, video_size[1] // 2)  # 500x500 each tile
            
            # Resize source image to tile size
            pil_img = pil_img.resize(tile_size, resample=1)  # LANCZOS
            
            # Convert to OpenCV format
            cv_tile = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            video = cv2.VideoWriter(output_path, fourcc, float(fps), video_size)
            
            if not video.isOpened():
                logger.error(f"Failed to open video writer for {output_path}")
                return False
            
            total_frames = fps * total_duration
            
            # Progressive tiling with fade-in (5 seconds)
            phase1_frames = fps * 5
            tiles_positions = [
                (0, 0),           # Top-left
                (tile_size[0], 0), # Top-right  
                (0, tile_size[1]), # Bottom-left
                (tile_size[0], tile_size[1])  # Bottom-right
            ]
            
            frames_per_tile = phase1_frames // 4
            fade_frames = frames_per_tile // 2  # Half the time for fade-in
            
            for tile_idx in range(4):
                for frame_in_tile in range(frames_per_tile):
                    # Create white background
                    frame = np.ones((video_size[1], video_size[0], 3), dtype=np.uint8) * 255
                    
                    # Draw all previous tiles (fully opaque)
                    for i in range(tile_idx):
                        x, y = tiles_positions[i]
                        frame[y:y + tile_size[1], x:x + tile_size[0]] = cv_tile
                    
                    # Draw current tile with fade-in effect
                    if frame_in_tile < fade_frames:
                        # Fade in current tile
                        alpha = frame_in_tile / fade_frames
                        x, y = tiles_positions[tile_idx]
                        
                        # Create alpha blended tile
                        white_tile = np.ones_like(cv_tile) * 255
                        faded_tile = (cv_tile * alpha + white_tile * (1 - alpha)).astype(np.uint8)
                        frame[y:y + tile_size[1], x:x + tile_size[0]] = faded_tile
                    else:
                        # Fully visible current tile
                        x, y = tiles_positions[tile_idx]
                        frame[y:y + tile_size[1], x:x + tile_size[0]] = cv_tile
                    
                    video.write(frame)
            
            # Final display with text overlay (3 seconds)
            phase2_frames = total_frames - phase1_frames
            
            # Create text overlay using PIL
            text_img = Image.new("RGB", video_size, (255, 255, 255))
            text_draw = ImageDraw.Draw(text_img)
            
            # Add tiled background
            for y in range(2):
                for x in range(2):
                    text_img.paste(pil_img, (x * tile_size[0], y * tile_size[1]))
            
            # Add text overlay
            font = get_font("DSMarkerFelt", 80)
            text = "Images tile seamlessly"
            text_position = (video_size[0] // 2, video_size[1] // 2)
            
            # Calculate text size for backdrop
            try:
                text_bbox = text_draw.textbbox(text_position, text, font=font, anchor="mm")
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            except AttributeError:
                text_width, text_height = text_draw.textsize(text, font=font)
            
            # Draw backdrop
            padding = 30
            backdrop_position = (
                text_position[0] - text_width // 2 - padding,
                text_position[1] - text_height // 2 - padding,
                text_position[0] + text_width // 2 + padding,
                text_position[1] + text_height // 2 + padding,
            )
            text_draw.rounded_rectangle(backdrop_position, radius=15, fill=(0, 0, 0, 200))
            
            # Draw text
            text_draw.text(text_position, text, font=font, fill=(255, 255, 255), anchor="mm")
            
            # Convert text overlay to OpenCV format
            text_frame = cv2.cvtColor(np.array(text_img), cv2.COLOR_RGB2BGR)
            
            for i in range(phase2_frames):
                video.write(text_frame)
            
            video.release()
            
            success = (
                os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            )
            
            if success:
                logger.info(f"Tiling video created: {output_path}")
                return True
            else:
                logger.error(f"Video file was created but is empty: {output_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating tiling video: {e}")
            return False
    
    def create_collage_video(self, image_paths: List[str], output_path: str,
                            fps: int = 30, display_duration: int = 8) -> bool:
        """
        Create a slideshow video from multiple images with fade transitions.
        Each image is shown individually, then fades to the next.
        
        Args:
            image_paths: List of image paths (grid mockups)
            output_path: Where to save the video
            fps: Frames per second
            display_duration: Total video duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.opencv_available:
            return False
        
        if not image_paths:
            logger.warning("No image paths provided for collage video")
            return False
        
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.error("OpenCV not available for video creation")
            return False
        
        logger.info(f"Creating slideshow video with {len(image_paths)} images: {output_path}")
        
        # Load all images and scale them
        cv_images = []
        for img_path in image_paths:
            pil_img = safe_load_image(img_path)
            if pil_img:
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                cv_images.append(pil_img)
            else:
                logger.warning(f"Failed to load image: {img_path}")
        
        if not cv_images:
            logger.error("No valid images loaded for slideshow")
            return False
        
        # Scale down images for video to prevent memory issues
        max_img_size = 1920  # Max width or height
        orig_width, orig_height = cv_images[0].size
        scale_factor = min(max_img_size / orig_width, max_img_size / orig_height, 1.0)
        
        video_width = int(orig_width * scale_factor)
        video_height = int(orig_height * scale_factor)
        
        logger.info(f"Creating slideshow video at {video_width}x{video_height}")
        
        # Scale all images to video size
        from PIL import Image
        scaled_cv_images = []
        for img in cv_images:
            if scale_factor < 1.0:
                scaled_img = img.resize((video_width, video_height), Image.Resampling.LANCZOS)
            else:
                scaled_img = img
            # Convert to OpenCV format
            cv_img = cv2.cvtColor(np.array(scaled_img), cv2.COLOR_RGB2BGR)
            scaled_cv_images.append(cv_img)
        
        cv_images = scaled_cv_images
        
        # Ensure output directory exists
        ensure_dir_exists(os.path.dirname(output_path))
        
        # Create videos folder for Etsy integration
        input_folder = os.path.dirname(os.path.dirname(output_path))
        videos_folder = os.path.join(input_folder, "videos")
        ensure_dir_exists(videos_folder)
        
        # Path for the video in the videos folder
        videos_output_path = os.path.join(videos_folder, os.path.basename(output_path))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        video_writer = cv2.VideoWriter(videos_output_path, fourcc, fps, (video_width, video_height))
        
        if not video_writer.isOpened():
            logger.error(f"Failed to open video writer for {videos_output_path}")
            return False
        
        try:
            # Calculate timing
            num_images = len(cv_images)
            time_per_image = display_duration / num_images
            display_frames = int(fps * time_per_image * 0.8)  # 80% display time
            transition_frames = int(fps * time_per_image * 0.2)  # 20% transition time
            
            logger.info(f"Creating slideshow: {display_frames} display frames, {transition_frames} transition frames per image")
            
            # Create slideshow with fade transitions
            for i in range(num_images):
                current_img = cv_images[i]
                next_img = cv_images[(i + 1) % num_images] if num_images > 1 else current_img
                
                # Display current image
                for _ in range(display_frames):
                    video_writer.write(current_img)
                
                # Transition to next image (fade)
                if num_images > 1 and i < num_images - 1:  # Don't fade after last image
                    for j in range(transition_frames):
                        alpha = j / transition_frames
                        blended = cv2.addWeighted(current_img, 1 - alpha, next_img, alpha, 0)
                        video_writer.write(blended)
            
            video_writer.release()
            
            success = (
                os.path.exists(videos_output_path)
                and os.path.getsize(videos_output_path) > 0
            )
            
            if success:
                logger.info(f"Slideshow video created: {videos_output_path}")
                return True
            else:
                logger.error(f"Video file was created but is empty: {videos_output_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error writing slideshow video frames: {e}")
            video_writer.release()
            return False