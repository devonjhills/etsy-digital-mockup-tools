"""
Module for creating video mockups.
"""

import os
from typing import Optional
import logging

from utils.common import setup_logging, ensure_dir_exists

# Set up logging
logger = setup_logging(__name__)


def create_seamless_zoom_video(
    input_folder: str, seamless_image_path: Optional[str]
) -> Optional[str]:
    """
    Creates a zoom-out video from the seamless pattern image.

    Args:
        input_folder: Path to the input folder
        seamless_image_path: Path to the seamless pattern image

    Returns:
        Path to the created video file, or None if creation failed
    """
    logger.info("Creating seamless zoom video...")

    # Create videos folder for Etsy integration
    videos_folder = os.path.join(input_folder, "videos")
    ensure_dir_exists(videos_folder)

    # Also save to mocks folder for backward compatibility
    mocks_folder = os.path.join(input_folder, "mocks")
    ensure_dir_exists(mocks_folder)

    if not seamless_image_path or not os.path.exists(seamless_image_path):
        logger.warning(
            f"Seamless pattern image '{seamless_image_path or 'None'}' not found. Skipping zoom video."
        )
        return None

    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV (cv2) is not installed. Skipping video creation.")
        logger.info("Install using: pip install opencv-python")
        return None

    try:
        img = cv2.imread(seamless_image_path)
        if img is None:
            logger.error(f"OpenCV could not read image: {seamless_image_path}")
            return None

        height, width = img.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # Save to videos folder for Etsy integration
        video_path = os.path.join(videos_folder, "seamless_pattern.mp4")
        video = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

        total_frames = 90
        initial_zoom = 1.5

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
            crop = img[y1 : y1 + new_h, x1 : x1 + new_w]

            if crop is not None and crop.size > 0:
                frame = cv2.resize(
                    crop, (width, height), interpolation=cv2.INTER_LINEAR
                )
                video.write(frame)

        video.release()

        # Only save to videos folder, no need to duplicate in mocks folder
        logger.info(f"Seamless zoom video saved to videos folder: {video_path}")

        return video_path

    except Exception as e:
        logger.error(f"Error creating seamless zoom video: {e}")
        return None
