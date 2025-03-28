import os
import numpy as np
from PIL import Image
import cv2

def create_mask_from_reference(ref_mask_path, width, height, debug_mask_path=None):
    """
    Create a binary mask from a reference mask image.
    The reference image is resized to (width, height), thresholded adaptively to preserve details,
    and its contours are filled.
    
    If debug_mask_path is provided, a color version of the mask with red contour outlines is saved.
    """
    try:
        # Load the reference mask as a grayscale image
        ref_img = Image.open(ref_mask_path).convert("L")
    except FileNotFoundError:
        raise FileNotFoundError(f"Reference mask image not found at: {ref_mask_path}")

    # Resize the reference mask to match the target dimensions
    ref_img = ref_img.resize((width, height), Image.LANCZOS)
    ref_np = np.array(ref_img)
    
    # Apply Gaussian blur to reduce noise before processing
    blurred = cv2.GaussianBlur(ref_np, (5, 5), 0)
    
    # Use a much lower threshold value to capture more of the stroke details
    # A threshold of 20-30 should capture most visible pixels in watercolor strokes
    _, thresh_mask = cv2.threshold(blurred, 25, 255, cv2.THRESH_BINARY)
    
    # Alternative: Use adaptive thresholding for better detail preservation
    # This can be enabled if the simple thresholding still doesn't work well
    # adaptive_mask = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    #                                       cv2.THRESH_BINARY, 11, 2)
    # thresh_mask = adaptive_mask

    # Optional: Apply morphological operations to clean up the mask
    kernel = np.ones((3, 3), np.uint8)
    thresh_mask = cv2.morphologyEx(thresh_mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours in the binary image
    contours, _ = cv2.findContours(thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Create a blank mask and fill in the contours
    mask_np = np.zeros((height, width), dtype=np.uint8)
    if contours:
        cv2.drawContours(mask_np, contours, -1, 255, thickness=cv2.FILLED)

    # Optional: Save a debug image showing the filled mask with red contour outlines
    if debug_mask_path:
        mask_debug = cv2.cvtColor(mask_np.copy(), cv2.COLOR_GRAY2BGR)
        cv2.drawContours(mask_debug, contours, -1, (0, 0, 255), thickness=2)
        cv2.imwrite(debug_mask_path, mask_debug)
        print(f"Debug mask saved to {debug_mask_path}")

    return Image.fromarray(mask_np)

def apply_mask_to_image(input_image_path, mask, output_path):
    """
    Applies the provided mask as the alpha channel to the input image and saves the result.
    """
    # Load the input image and convert it to RGBA
    img = Image.open(input_image_path).convert("RGBA")

    # Resize the mask if it doesn't match the image dimensions
    if mask.size != img.size:
        mask = mask.resize(img.size, Image.LANCZOS)

    # Apply the mask as the alpha channel
    img.putalpha(mask)
    img.save(output_path)
    print(f"Processed image saved to {output_path}")

def process_all_images(input_folder="brush_input", output_folder="brush_output",
                       ref_mask_path="mask.png", debug_mask_path=None):
    """
    Processes all images in the input folder using a single mask generated from the reference mask.
    The masked images are saved to the output folder.
    """
    os.makedirs(output_folder, exist_ok=True)

    # Loop over all image files in the input folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            input_image_path = os.path.join(input_folder, filename)
            output_image_path = os.path.join(output_folder, f"masked_{filename}")

            # Open the input image to determine its dimensions
            with Image.open(input_image_path) as img:
                width, height = img.size

            # Create the mask from the reference image for this input image size
            mask = create_mask_from_reference(ref_mask_path, width, height, debug_mask_path)

            # Apply the mask to the input image and save the result
            apply_mask_to_image(input_image_path, mask, output_image_path)

if __name__ == "__main__":
    # Define paths
    input_folder = "brush_input"       # Folder containing input images
    output_folder = "brush_output"     # Folder to save output images
    ref_mask_path = "mask.png"         # Reference mask with brush strokes
    debug_mask_path = "debug_mask.png" # Debug output for the mask (optional)

    process_all_images(input_folder=input_folder,
                       output_folder=output_folder,
                       ref_mask_path=ref_mask_path,
                       debug_mask_path=debug_mask_path)
    print("All images processed!")