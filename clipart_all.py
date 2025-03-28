# clipart_all.py (incorporating fixes for zip.py call and clipart.py call)
import subprocess
import sys
import argparse
import os
from subprocess import CalledProcessError  # Import the exception class

# --- Determine Paths ---
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(script_path)

clipart_dir = os.path.join(project_root, "clipart")
brush_strokes_dir = os.path.join(project_root, "brush_strokes")
input_dir_default = os.path.join(project_root, "input")
main_output_dir_default = os.path.join(project_root, "clipart_output")

clipart_resize_script = os.path.join(clipart_dir, "clipart_resize.py")
strokes_script = os.path.join(brush_strokes_dir, "strokes.py")
# Note: We will call clipart.py using the module path 'clipart.clipart'
zip_script = os.path.join(project_root, "zip.py")

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
    help="Maximum pixel dimension for clipart_resize.py.",
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

args = parser.parse_args()

effective_input_dir = args.input_dir
effective_output_dir = args.output_dir  # This is the source for zipping later

# --- Running Subprocesses ---
python_executable = sys.executable

print("-" * 60)
print(f"Starting Clipart Pipeline")
print("-" * 60)
print(f"Project Root: {project_root}")
print(f"Using Python: {python_executable}")
print(f"Input Directory: {effective_input_dir}")
print(f"Output Directory: {effective_output_dir}")
print(f"Resize Max Dimension: {args.max_size}")
print(f"Processing Mode: {'Strokes' if args.strokes else 'Clipart'}")
print(f"Zip Max Part Size: {args.zip_max_mb} MB")
print(f"Zip Image Quality: {args.zip_quality}")
print("-" * 60)

# --- Step 1: Run clipart_resize.py ---
print("\nSTEP 1: Resizing source images...")
clipart_resize_cmd = [
    python_executable,
    clipart_resize_script,
    "--input_folder",
    effective_input_dir,
    "--max_size",
    str(args.max_size),
]
print(f"Running: {' '.join(clipart_resize_cmd)}")
print(f"  (Working directory: {clipart_dir})")
try:
    subprocess.run(clipart_resize_cmd, check=True, cwd=clipart_dir)
    print("STEP 1: Resizing completed successfully.")
except CalledProcessError as e:
    print(f"Error running clipart_resize.py: {e}", file=sys.stderr)
    sys.exit(1)

# --- Step 2: Run strokes.py or clipart.py ---
print(f"\nSTEP 2: Running {'Strokes' if args.strokes else 'Clipart'} processing...")
if args.strokes:
    # --- Running strokes.py (Assumes it doesn't use relative imports like clipart.py) ---
    script_name = "strokes.py"
    run_script_path = strokes_script
    run_dir = brush_strokes_dir  # Run from its own directory
    run_cmd = [
        python_executable,
        run_script_path,
        # Example: Pass args if strokes.py is modified to accept them
        # '--input_dir', effective_input_dir,
        # '--output_dir', effective_output_dir, # If strokes needs separate output
    ]
    run_cwd = run_dir  # Run strokes from its own directory by default
    print(f"Running: {' '.join(run_cmd)}")
    print(f"  (Working directory: {run_cwd})")

else:
    # --- Running clipart.py AS A MODULE ---
    script_name = "clipart.py (as module)"
    module_path = "clipart.clipart"  # Module path to run
    # --- Pass necessary arguments to the module ---
    run_cmd = [
        python_executable,
        "-m",
        module_path,  # Use -m flag
        "--input_dir",
        effective_input_dir,  # Pass input dir
        # '--output_dir', effective_output_dir # <<< REMOVE THIS LINE >>>
        # Add any other arguments clipart.py needs (like --title if desired)
        # Example: Add title if needed from clipart_all.py args
        # if args.mockup_title: run_cmd.extend(['--title', args.mockup_title])
    ]
    run_cwd = project_root  # Run from PROJECT ROOT for module resolution

    print(f"Running: {' '.join(run_cmd)}")
    print(f"  (Working directory: {run_cwd})")  # CWD is project root

# Execute the chosen command (either strokes script or clipart module)
try:
    subprocess.run(run_cmd, check=True, cwd=run_cwd)  # Use calculated CWD
    print(f"STEP 2: {script_name} completed successfully.")
except CalledProcessError as e:
    print(f"Error running {script_name}: {e}", file=sys.stderr)
    # Add more specific error info if possible
    if e.stderr:
        print(f"Subprocess stderr:\n{e.stderr.decode()}", file=sys.stderr)
    if e.stdout:
        print(f"Subprocess stdout:\n{e.stdout.decode()}", file=sys.stderr)
    sys.exit(1)

# --- Step 3: Run zip.py ---
print("\nSTEP 3: Zipping output files...")
zip_source_dir = effective_input_dir

# Check if the source directory for zipping actually exists
if not os.path.isdir(zip_source_dir):
    print(
        f"Error: Source directory for zipping '{zip_source_dir}' not found. Cannot run zip.py.",
        file=sys.stderr,
    )
    sys.exit(1)

zip_cmd = [
    python_executable,
    zip_script,
    "--source_folder",
    zip_source_dir,  # <-- Use input dir as source
    "--max_size_mb",
    str(args.zip_max_mb),
    "--image_quality",
    str(args.zip_quality),
]
print(f"Running: {' '.join(zip_cmd)}")
print(f"  (Working directory: {project_root})")
try:
    subprocess.run(zip_cmd, check=True, cwd=project_root)
    print("STEP 3: Zipping completed successfully.")
except CalledProcessError as e:
    print(f"Error running zip.py: {e}", file=sys.stderr)
    sys.exit(1)

print("-" * 60)
print("\nAll pipeline steps completed successfully.")
print("-" * 60)
