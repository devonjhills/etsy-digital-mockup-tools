#!/usr/bin/env python3
"""
Main script for running the complete clipart workflow.
This is a wrapper around the modularized clipart code for backward compatibility.
"""
import sys
import os
import argparse

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the modularized clipart package
from utils.common import setup_logging, run_script
from clipart.resize import process_images
from clipart.main import process_clipart

# Set up logging
logger = setup_logging(__name__)

# --- Configuration ---
# Get the directory where this script is located.
# This should be the project root.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Default directories
input_dir_default = os.path.join(PROJECT_ROOT, "input")
main_output_dir_default = os.path.join(PROJECT_ROOT, "clipart_output")
brush_strokes_dir = os.path.join(PROJECT_ROOT, "brush_strokes")
strokes_script = os.path.join(brush_strokes_dir, "strokes.py")

# --- Argument Parsing ---
parser = argparse.ArgumentParser(
    description="Run clipart processing and zipping pipeline."
)
parser.add_argument(
    "-s",
    "--strokes",
    action="store_true",
    help="Run strokes.py processing instead of clipart.py processing.",
)
parser.add_argument(
    "-m",
    "--max_size",
    type=int,
    default=1500,
    help="Maximum pixel dimension for image resizing.",
)
parser.add_argument(
    "--zip_max_mb",
    type=float,
    default=20.0,
    help="Maximum size (MB) for individual zip file parts created by zip.py.",
)
parser.add_argument(
    "--zip_quality",
    type=int,
    default=80,
    choices=range(1, 101),
    metavar="[1-100]",
    help="Image compression quality (1-100) for zip.py.",
)
parser.add_argument(
    "--input_dir",
    default=input_dir_default,
    help=f"Override default input directory ({input_dir_default})",
)
parser.add_argument(
    "--output_dir",
    default=main_output_dir_default,
    help=f"Override default main output directory ({main_output_dir_default})",
)

if __name__ == "__main__":
    args = parser.parse_args()

    effective_input_dir = args.input_dir
    effective_output_dir = args.output_dir

    print("-" * 60)
    print(f"Starting Clipart Pipeline")
    print("-" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Input Directory: {effective_input_dir}")
    print(f"Output Directory: {effective_output_dir}")
    print(f"Resize Max Dimension: {args.max_size}")
    print(f"Processing Mode: {'Strokes' if args.strokes else 'Clipart'}")
    print(f"Zip Max Part Size: {args.zip_max_mb} MB")
    print(f"Zip Image Quality: {args.zip_quality}")
    print("-" * 60)

    # --- Step 1: Resize images ---
    print("\nSTEP 1: Resizing source images...")
    try:
        process_images(effective_input_dir, args.max_size)
        print("STEP 1: Resizing completed successfully.")
    except Exception as e:
        print(f"Error resizing images: {e}")
        sys.exit(1)

    # --- Step 2: Run strokes.py or clipart processing ---
    print(f"\nSTEP 2: Running {'Strokes' if args.strokes else 'Clipart'} processing...")
    if args.strokes:
        # Run strokes.py
        try:
            run_script(strokes_script, "Strokes", cwd=brush_strokes_dir)
            print("STEP 2: Strokes processing completed successfully.")
        except Exception as e:
            print(f"Error running strokes.py: {e}")
            sys.exit(1)
    else:
        # Run clipart processing
        try:
            process_clipart(effective_input_dir)
            print("STEP 2: Clipart processing completed successfully.")
        except Exception as e:
            print(f"Error running clipart processing: {e}")
            sys.exit(1)

    # --- Step 3: Run zip.py ---
    print("\nSTEP 3: Zipping output files...")
    zip_source_dir = effective_input_dir

    # Check if the source directory for zipping actually exists
    if not os.path.isdir(zip_source_dir):
        print(
            f"Error: Source directory for zipping '{zip_source_dir}' not found. Cannot run zip.py."
        )
        sys.exit(1)

    # Run zip.py
    zip_script = os.path.join(PROJECT_ROOT, "zip.py")
    zip_args = [
        "--source_folder",
        zip_source_dir,
        "--max_size_mb",
        str(args.zip_max_mb),
        "--image_quality",
        str(args.zip_quality),
    ]

    try:
        run_script(zip_script, "Zipper", script_args=zip_args, cwd=PROJECT_ROOT)
        print("STEP 3: Zipping completed successfully.")
    except Exception as e:
        print(f"Error running zip.py: {e}")
        sys.exit(1)

    print("-" * 60)
    print("\nAll pipeline steps completed successfully.")
    print("-" * 60)
