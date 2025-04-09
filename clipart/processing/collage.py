"""
Module for creating collage layouts.
"""
import os
import random
import math
from typing import List, Tuple, Dict, Optional, Any
from PIL import Image

from utils.common import setup_logging, get_resampling_filter, safe_load_image

# Set up logging
logger = setup_logging(__name__)

def select_centerpiece_image(
    image_paths: List[str],
    alpha_threshold: int = 10
) -> Optional[Image.Image]:
    """
    Select the best image to use as a centerpiece based on colorfulness and fit.
    
    Args:
        image_paths: List of paths to images
        alpha_threshold: Threshold for alpha channel
        
    Returns:
        The selected centerpiece image, or None if no suitable image is found
    """
    logger.info("Selecting candidate image for analysis (best colorful combination)...")
    
    if not image_paths:
        logger.warning("No image paths provided.")
        return None
    
    items = []
    
    for path in image_paths:
        original_img = safe_load_image(path)
        if not original_img or original_img.width <= 0 or original_img.height <= 0:
            logger.warning(f"Skipping invalid image: {os.path.basename(path)}")
            continue
        
        fit_score, content_area = _calculate_fit_score(original_img, alpha_threshold)
        colorfulness = compute_colorfulness(original_img)
        combined_score = colorfulness / (fit_score + 1.0)
        
        items.append({
            "path": path,
            "original_img": original_img,
            "fit_score": fit_score,
            "colorfulness": colorfulness,
            "combined_score": combined_score,
            "content_area": content_area
        })
    
    if not items:
        logger.warning("No valid images found for centerpiece selection.")
        return None
    
    # Sort by combined score (higher is better)
    items.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # Return the best image
    best_item = items[0]
    logger.info(
        f"Selected centerpiece: {os.path.basename(best_item['path'])} "
        f"(Score: {best_item['combined_score']:.2f}, "
        f"Colorfulness: {best_item['colorfulness']:.2f}, "
        f"Fit: {best_item['fit_score']:.2f})"
    )
    
    return best_item["original_img"]

def _calculate_fit_score(image: Image.Image, alpha_threshold: int) -> Tuple[float, int]:
    """
    Calculate a score for how well an image fits as a centerpiece.
    
    Args:
        image: The image to evaluate
        alpha_threshold: Threshold for alpha channel
        
    Returns:
        Tuple of (fit_score, content_area)
    """
    try:
        bbox = image.getbbox()
        if not bbox:
            return float("inf"), 0
        
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        
        if bbox_width <= 0 or bbox_height <= 0:
            return float("inf"), 0
        
        content_area = bbox_width * bbox_height
        aspect_ratio = bbox_width / bbox_height
        
        squareness_score = abs(math.log(aspect_ratio)) if aspect_ratio > 0 else float("inf")
        fill_score = 0.5
        
        # Calculate fill ratio (content area vs. total area)
        if image.width > 0 and image.height > 0:
            total_area = image.width * image.height
            fill_ratio = content_area / total_area
            fill_score = abs(0.7 - fill_ratio)  # Prefer ~70% fill
        
        # Combine scores (lower is better)
        combined_score = squareness_score + fill_score
        
        return combined_score, content_area
        
    except Exception as e:
        logger.error(f"Error calculating fit score: {e}")
        return float("inf"), 0

def compute_colorfulness(image: Image.Image) -> float:
    """
    Calculate the colorfulness of an image.
    
    Args:
        image: The image to evaluate
        
    Returns:
        A colorfulness score (higher is more colorful)
    """
    try:
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Convert to numpy array
        import numpy as np
        img_array = np.array(image)
        
        # Split into channels
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        
        # Calculate rg and yb components
        rg = np.absolute(r.astype(np.int32) - g.astype(np.int32))
        yb = np.absolute(0.5 * (r.astype(np.int32) + g.astype(np.int32)) - b.astype(np.int32))
        
        # Calculate mean and standard deviation
        rg_mean, rg_std = np.mean(rg), np.std(rg)
        yb_mean, yb_std = np.mean(yb), np.std(yb)
        
        # Calculate colorfulness
        std_root = np.sqrt((rg_std ** 2) + (yb_std ** 2))
        mean_root = np.sqrt((rg_mean ** 2) + (yb_mean ** 2))
        
        return std_root + (0.3 * mean_root)
        
    except Exception as e:
        logger.error(f"Error computing colorfulness: {e}")
        return 0.0

def create_collage_layout(
    image_paths: List[str],
    canvas: Image.Image,
    title_backdrop_bounds: Optional[Tuple[int, int, int, int]] = None,
    centerpiece_scale_factor: float = 0.65,
    surround_min_width_factor: float = 0.20,
    surround_max_width_factor: float = 0.30,
    placement_step: int = 5,
    title_avoid_padding: int = 20,
    centerpiece_avoid_padding: int = 20,
    rescale_factor: float = 0.95,
    rescale_attempts: int = 3,
    max_acceptable_overlap_ratio: float = 0.10,
    min_scale_abs: float = 0.30
) -> Image.Image:
    """
    Create a collage layout with a centerpiece and surrounding images.
    
    Args:
        image_paths: List of paths to images
        canvas: The canvas to draw on
        title_backdrop_bounds: Bounds of the title backdrop to avoid
        centerpiece_scale_factor: Scale factor for the centerpiece
        surround_min_width_factor: Minimum width factor for surrounding images
        surround_max_width_factor: Maximum width factor for surrounding images
        placement_step: Step size for placement attempts
        title_avoid_padding: Padding to avoid the title
        centerpiece_avoid_padding: Padding to avoid the centerpiece
        rescale_factor: Factor to rescale images if they overlap
        rescale_attempts: Number of rescale attempts
        max_acceptable_overlap_ratio: Maximum acceptable overlap ratio
        min_scale_abs: Minimum absolute scale
        
    Returns:
        The collage layout image
    """
    logger.info("Creating collage layout...")
    
    if not image_paths:
        logger.warning("No image paths provided for collage.")
        return canvas
    
    canvas_width, canvas_height = canvas.size
    
    # Load all images
    images = []
    for path in image_paths:
        img = safe_load_image(path, "RGBA")
        if img:
            images.append(img)
        else:
            logger.warning(f"Failed to load image: {path}")
    
    if not images:
        logger.warning("No valid images loaded for collage.")
        return canvas
    
    # Select centerpiece
    centerpiece = select_centerpiece_image(image_paths)
    if not centerpiece:
        logger.warning("No centerpiece selected. Using first image.")
        centerpiece = images[0]
    
    # Calculate centerpiece size
    centerpiece_max_width = int(canvas_width * centerpiece_scale_factor)
    centerpiece_max_height = int(canvas_height * centerpiece_scale_factor)
    
    # Resize centerpiece
    centerpiece_aspect = centerpiece.width / centerpiece.height if centerpiece.height > 0 else 1
    if centerpiece_aspect >= 1:  # Wider than tall
        centerpiece_width = centerpiece_max_width
        centerpiece_height = int(centerpiece_width / centerpiece_aspect)
        if centerpiece_height > centerpiece_max_height:
            centerpiece_height = centerpiece_max_height
            centerpiece_width = int(centerpiece_height * centerpiece_aspect)
    else:  # Taller than wide
        centerpiece_height = centerpiece_max_height
        centerpiece_width = int(centerpiece_height * centerpiece_aspect)
        if centerpiece_width > centerpiece_max_width:
            centerpiece_width = centerpiece_max_width
            centerpiece_height = int(centerpiece_width / centerpiece_aspect)
    
    centerpiece_resized = centerpiece.resize(
        (centerpiece_width, centerpiece_height),
        get_resampling_filter()
    )
    
    # Calculate centerpiece position (centered, but avoid title)
    centerpiece_x = (canvas_width - centerpiece_width) // 2
    centerpiece_y = (canvas_height - centerpiece_height) // 2
    
    # Adjust for title if needed
    if title_backdrop_bounds:
        title_bottom = title_backdrop_bounds[3] + title_avoid_padding
        available_height = canvas_height - title_bottom
        if available_height < centerpiece_height:
            # Title takes too much space, need to resize centerpiece
            scale_factor = available_height / centerpiece_height
            centerpiece_height = int(centerpiece_height * scale_factor)
            centerpiece_width = int(centerpiece_width * scale_factor)
            centerpiece_resized = centerpiece.resize(
                (centerpiece_width, centerpiece_height),
                get_resampling_filter()
            )
        
        # Center in available space below title
        centerpiece_y = title_bottom + (available_height - centerpiece_height) // 2
    
    # Paste centerpiece
    canvas.paste(centerpiece_resized, (centerpiece_x, centerpiece_y), centerpiece_resized)
    
    # Define centerpiece bounds for avoidance
    centerpiece_bounds = (
        centerpiece_x - centerpiece_avoid_padding,
        centerpiece_y - centerpiece_avoid_padding,
        centerpiece_x + centerpiece_width + centerpiece_avoid_padding,
        centerpiece_y + centerpiece_height + centerpiece_avoid_padding
    )
    
    # Place surrounding images
    surrounding_images = [img for img in images if img != centerpiece]
    if not surrounding_images:
        logger.info("No surrounding images to place.")
        return canvas
    
    # Shuffle to randomize placement
    random.shuffle(surrounding_images)
    
    # Calculate size range for surrounding images
    min_surround_width = int(canvas_width * surround_min_width_factor)
    max_surround_width = int(canvas_width * surround_max_width_factor)
    
    # Track placed images
    placed_bounds = []
    if title_backdrop_bounds:
        placed_bounds.append(title_backdrop_bounds)
    placed_bounds.append(centerpiece_bounds)
    
    # Place each surrounding image
    for img in surrounding_images:
        # Calculate initial size
        img_aspect = img.width / img.height if img.height > 0 else 1
        if img_aspect >= 1:  # Wider than tall
            img_width = random.randint(min_surround_width, max_surround_width)
            img_height = int(img_width / img_aspect)
        else:  # Taller than wide
            img_height = random.randint(min_surround_width, max_surround_width)
            img_width = int(img_height * img_aspect)
        
        img_resized = img.resize((img_width, img_height), get_resampling_filter())
        
        # Try to find a placement
        best_position = None
        min_overlap = float('inf')
        
        # Grid search for placement
        for x in range(0, canvas_width - img_width, placement_step):
            for y in range(0, canvas_height - img_height, placement_step):
                current_bounds = (x, y, x + img_width, y + img_height)
                
                # Calculate overlap with existing elements
                total_overlap = 0
                for bounds in placed_bounds:
                    overlap = _calculate_overlap(current_bounds, bounds)
                    total_overlap += overlap
                
                # Update best position if this has less overlap
                if total_overlap < min_overlap:
                    min_overlap = total_overlap
                    best_position = (x, y)
                
                # If we found a position with no overlap, use it immediately
                if min_overlap == 0:
                    break
            
            if min_overlap == 0:
                break
        
        # If we found a position, place the image
        if best_position:
            # Check if overlap is acceptable
            overlap_ratio = min_overlap / (img_width * img_height)
            
            # If overlap is too high, try rescaling
            current_scale = 1.0
            current_img = img_resized
            current_width, current_height = img_width, img_height
            
            for _ in range(rescale_attempts):
                if overlap_ratio <= max_acceptable_overlap_ratio:
                    break
                
                # Rescale
                current_scale *= rescale_factor
                if current_scale < min_scale_abs:
                    break
                
                current_width = int(img_width * current_scale)
                current_height = int(img_height * current_scale)
                
                if current_width <= 0 or current_height <= 0:
                    break
                
                current_img = img.resize((current_width, current_height), get_resampling_filter())
                
                # Recalculate position and overlap
                x, y = best_position
                current_bounds = (x, y, x + current_width, y + current_height)
                
                total_overlap = 0
                for bounds in placed_bounds:
                    overlap = _calculate_overlap(current_bounds, bounds)
                    total_overlap += overlap
                
                overlap_ratio = total_overlap / (current_width * current_height)
            
            # Place the image
            canvas.paste(current_img, best_position, current_img)
            
            # Add to placed bounds
            x, y = best_position
            placed_bounds.append((x, y, x + current_width, y + current_height))
    
    return canvas

def _calculate_overlap(bounds1: Tuple[int, int, int, int], bounds2: Tuple[int, int, int, int]) -> int:
    """
    Calculate the overlap area between two bounding boxes.
    
    Args:
        bounds1: First bounding box (x1, y1, x2, y2)
        bounds2: Second bounding box (x1, y1, x2, y2)
        
    Returns:
        The overlap area in pixels
    """
    x_overlap = max(0, min(bounds1[2], bounds2[2]) - max(bounds1[0], bounds2[0]))
    y_overlap = max(0, min(bounds1[3], bounds2[3]) - max(bounds1[1], bounds2[1]))
    return x_overlap * y_overlap
