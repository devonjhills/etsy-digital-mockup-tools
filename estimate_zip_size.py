def estimate_zip_size(file_paths, subfolder_path, image_quality):
    """Estimate the final zip size based on file sizes and compression ratios"""
    import os
    
    # Estimated compression ratio for different file types
    compression_ratio = {
        ".png": 1.2,  # PNG files are already compressed
        ".jpg": 1.05,  # JPEG files are already compressed
        ".jpeg": 1.05,
        ".webp": 1.1,
    }
    default_ratio = 1.2  # Default for unknown file types
    
    total_estimated_size = 0
    
    for file_path in file_paths:
        full_path = os.path.join(subfolder_path, file_path)
        if not os.path.isfile(full_path):
            continue
            
        # Get original file size
        file_size = os.path.getsize(full_path)
        
        # Apply estimated compression ratio based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        ratio = compression_ratio.get(ext, default_ratio)
        
        # Adjust ratio based on image quality for JPEGs
        if ext in ['.jpg', '.jpeg'] and image_quality < 95:
            # Lower quality means better compression
            quality_factor = (100 - image_quality) / 25  # 0.2 to 4.0
            ratio *= (1 + quality_factor * 0.2)  # Increase ratio for lower quality
            
        # Estimate compressed size
        estimated_size = file_size / ratio
        total_estimated_size += estimated_size
    
    # Add overhead for zip structure (headers, etc.)
    zip_overhead = 1.05  # 5% overhead
    return total_estimated_size * zip_overhead / (1024 * 1024)  # Convert to MB
