import os
from PIL import Image

def trim(im):
    """Remove empty space around an image with transparency"""
    bbox = im.convert('RGBA').getbbox()
    if bbox:
        return im.crop(bbox)
    return im

def process_images(input_folder, max_size=1500):
    """
    Processes images: converts to PNG, trims empty space, and resizes maintaining aspect ratio.
    
    Parameters:
        input_folder (str): Path to the input folder containing subfolders with images.
        max_size (int): Maximum size for the longest edge while maintaining aspect ratio.
    """
    for subfolder in os.listdir(input_folder):
        subfolder_path = os.path.join(input_folder, subfolder)

        if os.path.isdir(subfolder_path):
            safe_subfolder_name = subfolder.replace(" ", "_").lower()

            image_files = [
                f for f in os.listdir(subfolder_path)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]

            for index, image_file in enumerate(image_files, start=1):
                image_path = os.path.join(subfolder_path, image_file)

                try:
                    with Image.open(image_path) as img:
                        # Convert to RGBA to ensure transparency support
                        img = img.convert('RGBA')
                        
                        # Trim empty space
                        img = trim(img)
                        
                        # Calculate new size maintaining aspect ratio
                        width, height = img.size
                        if width > height:
                            new_width = max_size
                            new_height = int(height * (max_size / width))
                        else:
                            new_height = max_size
                            new_width = int(width * (max_size / height))
                        
                        # Resize image
                        img = img.resize((new_width, new_height), Image.LANCZOS)

                        # Save as PNG with new name
                        new_name = f"{safe_subfolder_name}_{index}.png"
                        new_path = os.path.join(subfolder_path, new_name)
                        
                        img.save(new_path, format="PNG")

                        # Remove the original file if the name has changed
                        if new_path != image_path:
                            os.remove(image_path)

                        print(f"Processed: {new_path}")

                except Exception as e:
                    print(f"Error processing {image_path}: {e}")

if __name__ == "__main__":
    input_folder = "input"  # Replace with your input folder path
    process_images(input_folder)
