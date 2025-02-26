import cv2
import numpy as np
from pathlib import Path
from skimage import measure
from skimage.filters import threshold_otsu
from skimage.morphology import closing, square
import matplotlib.pyplot as plt

def create_output_dir():
    """Create output directory if it doesn't exist"""
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    return output_dir

def delete_identifier_files(input_dir):
    """Delete all .Identifier files in the input directory"""
    for file in input_dir.glob('*.Identifier'):
        file.unlink()
        print(f"Deleted: {file}")

def extract_illustrations(image_path, output_dir):
    """Extract individual illustrations from the composite image, including handling transparency."""
    # Read image with alpha channel if present
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Failed to load image: {image_path}")
        return
    
    # Ensure we have at least 3 channels (BGR) or 4 channels (BGRA)
    if len(img.shape) < 3:
        print(f"Image {image_path} does not have enough channels for processing.")
        return
    
    # Check if we have an alpha channel
    has_alpha = (img.shape[2] == 4)

    if has_alpha:
        # Split into color (BGR) and alpha
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]

        # Create a mask based on alpha > 0 (or a small threshold if partial transparency)
        alpha_thresh = 1  # you can tweak this
        alpha_mask = (alpha > alpha_thresh).astype(np.uint8)

        # Optionally also check for near-white pixels in BGR if you want to exclude them:
        # avg_color = np.mean(bgr, axis=2)
        # color_mask = (avg_color < 250).astype(np.uint8)
        #
        # Combine alpha mask and color mask if desired:
        # mask = cv2.bitwise_and(alpha_mask, color_mask)
        #
        # For now, we rely primarily on alpha:
        mask = alpha_mask * 255

    else:
        # If no alpha channel, fall back to the original near-white detection
        bgr = img
        # Convert to grayscale
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
        # Create initial mask where pixels are significantly different from white
        avg_color = np.mean(bgr, axis=2)
        mask = (avg_color < 250).astype(np.uint8) * 255
    
    # Morphological operations to clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Label connected components
    labels = measure.label(mask, background=0)
    
    # Get properties of connected components
    regions = measure.regionprops(labels)
    
    # Filter regions based on size
    min_size = img.shape[0] * img.shape[1] * 0.05  # 5% of image size
    valid_regions = [region for region in regions if region.area >= min_size]
    
    # Sort regions by position (top to bottom, then left to right)
    valid_regions.sort(key=lambda x: (x.centroid[0], x.centroid[1]))
    
    # Extract and save each region
    for i, region in enumerate(valid_regions):
        # Get bounding box
        minr, minc, maxr, maxc = region.bbox
        
        # Add some padding
        padding = 20
        minr = max(0, minr - padding)
        minc = max(0, minc - padding)
        maxr = min(img.shape[0], maxr + padding)
        maxc = min(img.shape[1], maxc + padding)
        
        # Extract region from original image
        illustration = img[minr:maxr, minc:maxc]
        
        # Generate output filename
        base_name = image_path.stem
        output_path = output_dir / f"{base_name}_illustration_{i+1}.png"
        
        # Save the region
        # Note: If your OpenCV build supports PNG + alpha, this should preserve transparency if present
        cv2.imwrite(str(output_path), illustration)
        print(f"Saved: {output_path}")
        
        # Optional: Create debug visualization
        debug_dir = output_dir / 'debug'
        debug_dir.mkdir(exist_ok=True)
        
        plt.figure(figsize=(12, 4))
        
        # Show the mask portion
        plt.subplot(131)
        plt.imshow(mask[minr:maxr, minc:maxc], cmap='gray')
        plt.title('Mask')
        
        # Show the extracted region (converted to RGB for plotting)
        if has_alpha:
            # If we have alpha, we can show just the color channels
            plt.subplot(132)
            plt.imshow(cv2.cvtColor(illustration[:, :, :3], cv2.COLOR_BGR2RGB))
            plt.title('Extracted (BGR)')
        else:
            plt.subplot(132)
            plt.imshow(cv2.cvtColor(illustration, cv2.COLOR_BGR2RGB))
            plt.title('Extracted')
        
        # Show detection on original
        plt.subplot(133)
        debug_img = img.copy()
        # If debug_img is 4-channel, convert a copy to 3-channel for visualization
        if has_alpha:
            debug_img_bgr = debug_img[:, :, :3].copy()
            cv2.rectangle(debug_img_bgr, (minc, minr), (maxc, maxr), (0, 255, 0), 2)
            plt.imshow(cv2.cvtColor(debug_img_bgr, cv2.COLOR_BGR2RGB))
        else:
            cv2.rectangle(debug_img, (minc, minr), (maxc, maxr), (0, 255, 0), 2)
            plt.imshow(cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB))
        plt.title('Detection')
        
        plt.savefig(debug_dir / f"{base_name}_debug_{i+1}.png")
        plt.close()

def main():
    """Main function to process all images in input directory"""
    # Setup directories
    input_dir = Path('input')
    output_dir = create_output_dir()
    
    # Check if input directory exists
    if not input_dir.exists():
        print("Input directory 'input' not found. Please create it and add images.")
        return
    
    # Delete .IDENTIFIER files
    delete_identifier_files(input_dir)
    
    # Process each image in input directory
    image_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp')
    images = [f for f in input_dir.iterdir() if f.suffix.lower() in image_extensions]
    
    if not images:
        print("No images found in input directory.")
        return
    
    print(f"Found {len(images)} images to process...")
    
    # Process each image
    for image_path in images:
        print(f"\nProcessing: {image_path}")
        extract_illustrations(image_path, output_dir)
    
    print("\nProcessing complete!")

if __name__ == "__main__":
    main()
