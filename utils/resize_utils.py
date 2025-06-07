"""
Unified image resizing utilities for all product types.
"""

import os
import re
from typing import Tuple, Dict, List, Optional
from PIL import Image

from utils.common import setup_logging, get_resampling_filter, ensure_dir_exists

logger = setup_logging(__name__)


def extract_number_from_filename(filename: str) -> int:
    """
    Extract a number from a filename, handling various formats.
    
    Args:
        filename: The filename to extract a number from
        
    Returns:
        The extracted number, or 999999 if no number is found
    """
    # Try the pattern "name_N.ext" or "name (N).ext"
    match = re.search(r"[_\s(]+(\d+)[)\s.]*", filename)
    if match:
        return int(match.group(1))
    
    # If no match, try to find any number in the filename
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))
    
    # If no number found, return a high value to sort it at the end
    return 999999


def trim_image(image: Image.Image) -> Image.Image:
    """
    Remove empty space around an image with transparency.
    
    Args:
        image: The image to trim
        
    Returns:
        The trimmed image
    """
    try:
        image = image.convert("RGBA")
        bbox = image.getbbox()
        if bbox:
            return image.crop(bbox)
        logger.warning("Trim: Image appears to be empty or fully transparent, returning original.")
        return image
    except Exception as e:
        logger.error(f"Error during trim: {e}")
        return image


def safe_remove_file(file_path: str) -> bool:
    """
    Safely remove a file with error handling.
    
    Args:
        file_path: Path to the file to remove
        
    Returns:
        True if the file was removed successfully, False otherwise
    """
    try:
        os.remove(file_path)
        return True
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")
        return False


def create_safe_filename(folder_name: str, index: int, extension: str = "png") -> str:
    """
    Create a safe filename based on folder name and index.
    
    Args:
        folder_name: The folder name to base the filename on
        index: The index number for the file
        extension: The file extension (without dot)
        
    Returns:
        A safe filename
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name).lower()
    return f"{safe_name}_{index}.{extension}"


def get_existing_numbers(folder_path: str, safe_folder_name: str) -> set:
    """
    Get existing file numbers for a folder to avoid conflicts.
    
    Args:
        folder_path: Path to the folder to check
        safe_folder_name: The safe folder name pattern to match
        
    Returns:
        Set of existing numbers
    """
    existing_numbers = set()
    if not os.path.exists(folder_path):
        return existing_numbers
    
    for filename in os.listdir(folder_path):
        match = re.search(f"{re.escape(safe_folder_name)}_([0-9]+)", filename.lower())
        if match:
            existing_numbers.add(int(match.group(1)))
    
    return existing_numbers


class ImageResizer:
    """Unified image resizer for all product types."""
    
    def __init__(self, max_size: int = 3600, dpi: Tuple[int, int] = (300, 300)):
        self.max_size = max_size
        self.dpi = dpi
        self.supported_extensions = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"]
    
    def should_resize(self, image: Image.Image) -> bool:
        """Check if an image needs resizing."""
        if isinstance(self.max_size, int):
            return image.width > self.max_size or image.height > self.max_size
        else:
            return image.width > self.max_size[0] or image.height > self.max_size[1]
    
    def calculate_new_size(self, original_size: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate new size while maintaining aspect ratio."""
        width, height = original_size
        
        if isinstance(self.max_size, int):
            max_width = max_height = self.max_size
        else:
            max_width, max_height = self.max_size
        
        if width > height:
            new_width = min(width, max_width)
            new_height = int(height * (new_width / width))
            if new_height > max_height:
                new_height = max_height
                new_width = int(width * (new_height / height))
        else:
            new_height = min(height, max_height)
            new_width = int(width * (new_height / height))
            if new_width > max_width:
                new_width = max_width
                new_height = int(height * (new_width / width))
        
        return new_width, new_height
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """Get all image files in a folder."""
        if not os.path.exists(folder_path):
            return []
        
        image_files = []
        for ext in self.supported_extensions:
            image_files.extend([
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith(ext) and os.path.isfile(os.path.join(folder_path, f))
            ])
        
        # Sort by extracted number from filename
        return sorted(image_files, key=lambda x: extract_number_from_filename(os.path.basename(x)))
    
    def resize_clipart_style(self, input_folder: str) -> Dict:
        """
        Resize images using clipart-style processing (trim, PNG output).
        
        Args:
            input_folder: Path to folder containing images or subfolders
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting clipart-style resize in: {input_folder}")
        
        if not os.path.isdir(input_folder):
            return {"success": False, "error": f"Input folder not found: {input_folder}"}
        
        results = {
            "success": True,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "deleted": 0,
            "folders_processed": []
        }
        
        # Check for subfolders or process current folder
        subfolders = [d for d in os.listdir(input_folder) 
                     if os.path.isdir(os.path.join(input_folder, d)) and d not in ["mocks", "zipped"]]
        
        if not subfolders:
            # Process images directly in folder
            direct_images = self.get_image_files(input_folder)
            if direct_images:
                subfolders = ["."]
        
        for subfolder in subfolders:
            if subfolder == ".":
                folder_path = input_folder
                folder_name = os.path.basename(input_folder)
            else:
                folder_path = os.path.join(input_folder, subfolder)
                folder_name = subfolder
            
            folder_results = self._process_clipart_folder(folder_path, folder_name)
            results["processed"] += folder_results["processed"]
            results["errors"] += folder_results["errors"]
            results["deleted"] += folder_results["deleted"]
            results["folders_processed"].append(folder_name)
        
        return results
    
    def resize_pattern_style(self, input_folder: str) -> Dict:
        """
        Resize images using pattern-style processing (JPG output, no trim).
        
        Args:
            input_folder: Path to folder containing subfolders with images
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting pattern-style resize in: {input_folder}")
        
        if not os.path.isdir(input_folder):
            return {"success": False, "error": f"Input folder not found: {input_folder}"}
        
        results = {
            "success": True,
            "processed": 0,
            "folders_processed": []
        }
        
        for subfolder in os.listdir(input_folder):
            subfolder_path = os.path.join(input_folder, subfolder)
            
            if not os.path.isdir(subfolder_path) or subfolder in ["mocks", "zipped"]:
                continue
            
            folder_results = self._process_pattern_folder(subfolder_path, subfolder)
            results["processed"] += folder_results["processed"]
            results["folders_processed"].append(subfolder)
        
        return results
    
    def _process_clipart_folder(self, folder_path: str, folder_name: str) -> Dict:
        """Process a single folder for clipart-style resizing."""
        logger.info(f"Processing clipart folder: {folder_name}")
        
        image_files = self.get_image_files(folder_path)
        if not image_files:
            logger.warning(f"No images found in {folder_path}")
            return {"processed": 0, "errors": 0, "deleted": 0}
        
        safe_folder_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name)
        processed = errors = deleted = 0
        
        for i, image_path in enumerate(image_files, start=1):
            try:
                original_filename = os.path.basename(image_path)
                target_name = f"{safe_folder_name}_{i}.png"
                target_path = os.path.join(folder_path, target_name)
                
                logger.info(f"Processing {original_filename} -> {target_name}")
                
                with Image.open(image_path) as img:
                    img = img.convert("RGBA")
                    img = trim_image(img)
                    
                    if img.size == (0, 0):
                        logger.warning(f"Skipping {original_filename} - invalid size after trim")
                        errors += 1
                        continue
                    
                    if self.should_resize(img):
                        new_size = self.calculate_new_size(img.size)
                        logger.info(f"Resizing from {img.size} to {new_size}")
                        img = img.resize(new_size, get_resampling_filter())
                    
                    img.info["dpi"] = self.dpi
                    img.save(target_path, format="PNG", dpi=self.dpi)
                    
                    # Remove original if different from target
                    if os.path.abspath(target_path) != os.path.abspath(image_path):
                        if safe_remove_file(image_path):
                            deleted += 1
                    
                    processed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                errors += 1
        
        return {"processed": processed, "errors": errors, "deleted": deleted}
    
    def _process_pattern_folder(self, folder_path: str, folder_name: str) -> Dict:
        """Process a single folder for pattern-style resizing."""
        logger.info(f"Processing pattern folder: {folder_name}")
        
        image_files = self.get_image_files(folder_path)
        if not image_files:
            logger.warning(f"No images found in {folder_path}")
            return {"processed": 0}
        
        safe_folder_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name).lower()
        existing_numbers = get_existing_numbers(folder_path, safe_folder_name)
        
        # Find next available number
        next_number = 1
        while next_number in existing_numbers:
            next_number += 1
        
        processed = 0
        files_to_process = []
        
        # Check which files need processing
        for image_file in image_files:
            filename = os.path.basename(image_file)
            is_correct = False
            
            if re.match(f"^{re.escape(safe_folder_name)}_\\d+\\.jpe?g$", filename.lower()):
                try:
                    with Image.open(image_file) as img:
                        if not self.should_resize(img):
                            is_correct = True
                except Exception:
                    pass
            
            if not is_correct:
                files_to_process.append(image_file)
        
        if not files_to_process:
            logger.info(f"All files in {folder_name} are already correctly processed")
            return {"processed": 0}
        
        for image_path in files_to_process:
            try:
                original_filename = os.path.basename(image_path)
                new_filename = f"{safe_folder_name}_{next_number}.jpg"
                new_path = os.path.join(folder_path, new_filename)
                
                logger.info(f"Processing {original_filename} -> {new_filename}")
                
                with Image.open(image_path) as img:
                    if self.should_resize(img):
                        new_size = self.calculate_new_size(img.size)
                        logger.info(f"Resizing from {img.size} to {new_size}")
                        img = img.resize(new_size, get_resampling_filter())
                    
                    if hasattr(img, "info"):
                        img.info["dpi"] = self.dpi
                    
                    img.save(new_path, format="JPEG", dpi=self.dpi, quality=85, optimize=True)
                    
                    # Remove original if different
                    if image_path != new_path:
                        safe_remove_file(image_path)
                    
                    processed += 1
                    next_number += 1
                    
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
        
        return {"processed": processed}