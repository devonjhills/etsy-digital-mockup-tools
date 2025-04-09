#!/usr/bin/env python3
"""
Main script for running the complete pattern workflow.
This is a wrapper around the modularized pattern code for backward compatibility.
"""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the modularized pattern package
from utils.common import setup_logging
from pattern.resize import process_images
from pattern.main import process_all_patterns
from utils.common import run_script

# Set up logging
logger = setup_logging(__name__)

# --- Configuration ---
# Get the directory where this script (pattern_all.py) is located.
# This should be the project root.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Zip Configuration ---
# The base folder containing subfolders with images for zip.py to process
# This should be the 'input' folder relative to the project root
ZIP_SOURCE_FOLDER = os.path.join(PROJECT_ROOT, "input")
MAX_ZIP_SIZE_MB = 20.0  # Corresponds to --max_size_mb in zip.py
ZIP_IMAGE_QUALITY = 75  # Corresponds to --image_quality in zip.py

# --- Main Execution Logic ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting Automated Pattern Processing Workflow")
    print(f"Project Root: {PROJECT_ROOT}")
    print("=" * 50 + "\n")

    # Step 1: Resize pattern images
    # Input: Reads from 'input' subfolders
    # Output: Modifies images *in place* within 'input' subfolders
    print("Step 1: Resizing pattern images...")
    try:
        process_images(ZIP_SOURCE_FOLDER)
        print("Pattern resizing completed successfully.")
    except Exception as e:
        print(f"Workflow halted due to error in Pattern Resizer: {e}")
        sys.exit(1)  # Exit the script with an error code

    # Step 2: Make mockups
    # Input: Reads resized images from 'input' subfolders
    # Output: Creates 'mocks' folders inside each 'input' subfolder
    print("Step 2: Generating mockups...")
    try:
        if not process_all_patterns(ZIP_SOURCE_FOLDER):
            print("Workflow halted due to error in Mockup Generator.")
            sys.exit(1)  # Exit the script with an error code
        print("Mockup generation completed successfully.")
    except Exception as e:
        print(f"Workflow halted due to error in Mockup Generator: {e}")
        sys.exit(1)  # Exit the script with an error code

    # Step 3: Call zip.py to zip the resized original images
    # Input: --source_folder points to the main 'input' directory. zip.py scans subfolders.
    # Output: Creates 'zipped' folders inside each 'input' subfolder containing the final zip(s).
    print("Step 3: Zipping resized pattern images...")
    # Prepare arguments for zip.py
    zip_script = os.path.join(PROJECT_ROOT, "zip.py")
    zip_args = [
        "--source_folder",
        ZIP_SOURCE_FOLDER,
        "--max_size_mb",
        str(MAX_ZIP_SIZE_MB),
        "--image_quality",
        str(ZIP_IMAGE_QUALITY),
    ]
    if not run_script(zip_script, "Zipper", script_args=zip_args, cwd=PROJECT_ROOT):
        print("Workflow halted due to error in Zipper.")
        sys.exit(1)  # Exit the script with an error code

    print("\n" + "=" * 50)
    print("Pattern processing workflow completed successfully!")
    print("=" * 50)
