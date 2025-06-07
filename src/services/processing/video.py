"""
Module for creating video mockups.
"""

import os
from typing import List, Tuple, Dict, Optional, Any
import logging

from utils.common import setup_logging, safe_load_image, ensure_dir_exists

# Set up logging
logger = setup_logging(__name__)


def create_video_mockup(
    image_paths: List[str],
    output_path: str,
    target_size: Tuple[int, int] = (2000, 2000),
    fps: int = 30,
    transition_frames: int = 20,
    display_frames: int = 50,
) -> bool:
    """
    Create a video mockup from a series of images.

    Args:
        image_paths: List of paths to images
        output_path: Path to save the output video
        target_size: Target size of the video (width, height)
        fps: Frames per second
        transition_frames: Number of frames for transitions
        display_frames: Number of frames to display each image

    Returns:
        True if the video was created successfully, False otherwise
    """
    logger.info(f"Creating video mockup: {output_path}")

    if not image_paths:
        logger.warning("No image paths provided for video mockup.")
        return False

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("OpenCV (cv2) is not installed. Cannot create video.")
        logger.info("Install using: pip install opencv-python numpy")
        return False

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create videos folder for Etsy integration
    input_folder = os.path.dirname(os.path.dirname(output_path))
    videos_folder = os.path.join(input_folder, "videos")
    ensure_dir_exists(videos_folder)

    # Path for the video in the videos folder
    videos_output_path = os.path.join(videos_folder, "clipart_showcase.mp4")

    # Create video writer only for the videos folder
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
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

            # Resize to target size
            pil_img = pil_img.resize(target_size, resample=1)  # LANCZOS

            # Convert to OpenCV format
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            cv_images.append(cv_img)

        except Exception as e:
            logger.error(f"Error processing image {img_path} for video: {e}")

    if not cv_images:
        logger.warning("No valid images loaded for video.")
        video_writer.release()
        return False

    # Create frames
    try:
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
            logger.info(f"Video created successfully: {videos_output_path}")
            return True
        else:
            logger.error(f"Video file was created but is empty: {videos_output_path}")
            return False

    except Exception as e:
        logger.error(f"Error creating video: {e}")
        video_writer.release()
        return False
