"""File operations utilities for zip creation and file handling."""

import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.common import setup_logging, ensure_dir_exists

logger = setup_logging(__name__)


def create_zip_archive(source_dir: str, output_path: str = None, exclude_patterns: List[str] = None) -> Dict[str, Any]:
    """Create a ZIP archive from a directory.
    
    Args:
        source_dir: Directory to zip
        output_path: Output path for ZIP file (defaults to source_dir.zip)
        exclude_patterns: List of patterns to exclude
        
    Returns:
        Dict with zip creation results
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return {"success": False, "error": "Source directory not found"}
    
    if output_path is None:
        output_path = f"{source_dir}.zip"
    
    exclude_patterns = exclude_patterns or [".DS_Store", "Thumbs.db", "__pycache__"]
    
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_path):
                # Remove excluded directories
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                
                for file in files:
                    # Skip excluded files
                    if any(pattern in file for pattern in exclude_patterns):
                        continue
                    
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_path)
                    zipf.write(file_path, arcname)
        
        zip_size = os.path.getsize(output_path)
        logger.info(f"Created ZIP archive: {output_path} ({zip_size} bytes)")
        
        return {
            "success": True,
            "zip_path": output_path,
            "size_bytes": zip_size,
            "size_mb": round(zip_size / (1024 * 1024), 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to create ZIP archive: {e}")
        return {"success": False, "error": str(e)}


def ensure_directory(directory: str) -> bool:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to ensure
        
    Returns:
        True if directory exists or was created successfully
    """
    return ensure_dir_exists(directory)


def clean_directory(directory: str, keep_patterns: List[str] = None) -> bool:
    """Clean a directory, optionally keeping files matching patterns.
    
    Args:
        directory: Directory to clean
        keep_patterns: List of patterns for files to keep
        
    Returns:
        True if cleaning was successful
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return True
    
    keep_patterns = keep_patterns or []
    
    try:
        for item in dir_path.iterdir():
            # Check if item should be kept
            should_keep = any(pattern in item.name for pattern in keep_patterns)
            
            if not should_keep:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        logger.info(f"Cleaned directory: {directory}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clean directory {directory}: {e}")
        return False


def copy_file_safe(src: str, dst: str, overwrite: bool = True) -> bool:
    """Safely copy a file with error handling.
    
    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if copy was successful
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            logger.error(f"Source file does not exist: {src}")
            return False
        
        if dst_path.exists() and not overwrite:
            logger.warning(f"Destination file exists and overwrite=False: {dst}")
            return False
        
        # Ensure destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        logger.debug(f"Copied file: {src} -> {dst}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy file {src} -> {dst}: {e}")
        return False


def get_directory_size(directory: str) -> int:
    """Get the total size of a directory in bytes.
    
    Args:
        directory: Directory path
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Failed to calculate directory size for {directory}: {e}")
    
    return total_size


def find_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    """Find all files with specific extensions in a directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions (with or without dots)
        
    Returns:
        List of file paths
    """
    # Normalize extensions
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
    
    found_files = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext.lower()) for ext in extensions):
                    found_files.append(os.path.join(root, file))
    except Exception as e:
        logger.error(f"Failed to search for files in {directory}: {e}")
    
    return found_files


def create_smart_zip_files(source_dir: str, output_dir: str, max_size_mb: float = 20.0, 
                          exclude_patterns: List[str] = None) -> Dict[str, Any]:
    """Create ZIP files with intelligent splitting to stay under size limits.
    
    Args:
        source_dir: Directory containing files to zip
        output_dir: Directory where ZIP files will be created
        max_size_mb: Maximum size per ZIP file in MB (default 20MB for Etsy)
        exclude_patterns: List of patterns to exclude from zipping
        
    Returns:
        Dict with creation results including list of created ZIP files
    """
    import zipfile
    import math
    import re
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get folder name for ZIP naming
        folder_name = os.path.basename(source_dir)
        safe_folder_name = re.sub(r"[^a-zA-Z0-9_]", "_", folder_name).lower()
        
        # Default exclusions
        exclude_patterns = exclude_patterns or ["mocks", "zipped", "videos", "seamless", ".DS_Store", "Thumbs.db"]
        
        # Find all image files (excluding specified patterns)
        all_files = find_files_by_extension(source_dir, ['.png', '.jpg', '.jpeg', '.gif', '.tif', '.tiff'])
        image_files = [f for f in all_files if not any(pattern in f for pattern in exclude_patterns)]
        
        if not image_files:
            return {"success": False, "error": "No image files found to zip"}
        
        logger.info(f"Found {len(image_files)} image files to zip")
        
        # Calculate total size of all images
        total_size_bytes = sum(os.path.getsize(f) for f in image_files)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Determine how many zip files we need
        num_zips = max(1, math.ceil(total_size_mb / max_size_mb))
        
        if num_zips > 1:
            logger.info(f"Total size: {total_size_mb:.2f} MB, splitting into {num_zips} zip files")
            
            # Sort files by size (largest first) for better distribution
            image_files_with_size = [(f, os.path.getsize(f)) for f in image_files]
            image_files_with_size.sort(key=lambda x: x[1], reverse=True)
            
            # Distribute files across zips using a greedy approach
            zip_contents = [[] for _ in range(num_zips)]
            zip_sizes = [0] * num_zips
            
            # Assign each file to the zip with the smallest current size
            for file_path, file_size in image_files_with_size:
                smallest_zip_idx = zip_sizes.index(min(zip_sizes))
                zip_contents[smallest_zip_idx].append(file_path)
                zip_sizes[smallest_zip_idx] += file_size
            
            zip_sizes_mb = [s/(1024*1024) for s in zip_sizes]
            logger.info(f"Estimated zip sizes: {[f'{size:.2f}' for size in zip_sizes_mb]} MB")
            image_files = zip_contents
        else:
            image_files = [image_files]
        
        # Create the zip files
        zip_files_created = []
        
        for i, files_for_this_zip in enumerate(image_files):
            if not files_for_this_zip:
                continue
            
            # Create zip filename
            if num_zips > 1:
                zip_filename = f"{safe_folder_name}_part{i+1}.zip"
            else:
                zip_filename = f"{safe_folder_name}.zip"
            
            zip_path = os.path.join(output_dir, zip_filename)
            
            logger.info(f"Creating {zip_filename} with {len(files_for_this_zip)} files")
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_for_this_zip:
                    file_name = os.path.basename(file_path)
                    zipf.write(file_path, file_name)
            
            # Verify size
            zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            logger.info(f"Created {zip_filename}: {zip_size_mb:.2f} MB")
            
            if zip_size_mb > max_size_mb:
                logger.warning(f"Warning: {zip_filename} exceeds {max_size_mb} MB limit")
            
            zip_files_created.append(zip_path)
        
        return {
            "success": True,
            "zip_files": zip_files_created,
            "total_files": len(zip_files_created),
            "total_size_mb": round(sum(os.path.getsize(f) for f in zip_files_created) / (1024 * 1024), 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to create smart zip files: {e}")
        return {"success": False, "error": str(e)}


def get_safe_filename(filename: str) -> str:
    """Create a safe filename by removing/replacing problematic characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    import re
    
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # Remove leading/trailing underscores and dots
    safe_name = safe_name.strip('_.')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = "unnamed"
    
    return safe_name