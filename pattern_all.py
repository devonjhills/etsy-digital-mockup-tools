import subprocess
import sys  # Used to get the python executable reliably
import os  # Used to construct paths reliably

# --- Configuration ---
# Get the directory where this script (pattern_all.py) is located.
# This should be the project root.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Use the same Python interpreter that is running this script
PYTHON_EXECUTABLE = sys.executable

# --- Define paths to the scripts relative to PROJECT_ROOT ---
# Scripts inside the 'pattern' folder
PATTERN_RESIZE_SCRIPT = os.path.join("pattern", "pattern_resize.py")
PATTERN_SCRIPT = os.path.join("pattern", "pattern.py")

# Script in the root folder
ZIP_SCRIPT = "zip.py"

# --- Zip Configuration ---
# The base folder containing subfolders with images for zip.py to process
# This should be the 'input' folder relative to the project root
ZIP_SOURCE_FOLDER = os.path.join(PROJECT_ROOT, "input")
MAX_ZIP_SIZE_MB = 20.0  # Corresponds to --max_size_mb in zip.py
ZIP_IMAGE_QUALITY = 75  # Corresponds to --image_quality in zip.py


def run_script(script_path, script_name, script_args=None):
    """
    Helper function to run a python script, print info, check for errors,
    and pass optional arguments.

    Args:
        script_path (str): Relative path to the script from PROJECT_ROOT.
        script_name (str): User-friendly name for the script being run.
        script_args (list, optional): A list of string arguments to pass to the script. Defaults to None.

    Returns:
        bool: True if the script ran successfully, False otherwise.
    """
    full_script_path = os.path.join(PROJECT_ROOT, script_path)
    command_list = [PYTHON_EXECUTABLE, script_path] + (
        script_args if script_args else []
    )

    print("-" * 30)
    print(f"Running: {script_name}")
    print(f"Script Path: {full_script_path}")
    print(f"Full Command: {' '.join(command_list)}")  # Show the full command with args
    print("-" * 30)

    try:
        # `check=True` will raise a CalledProcessError if the script returns a non-zero exit code
        # `cwd=PROJECT_ROOT` ensures the script runs as if launched from the project root.
        # `capture_output=True` and `text=True` help capture stdout/stderr for debugging
        result = subprocess.run(
            command_list,  # Pass the command list with arguments
            check=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",  # Be explicit about encoding
        )
        print(f"--- Output from {script_name} ---")
        # Only print stdout if it's not excessively long (e.g., > 50 lines)
        stdout_lines = result.stdout.splitlines()
        if len(stdout_lines) < 50:
            print(result.stdout)
        else:
            print(f"(Output truncated - {len(stdout_lines)} lines)")
            # Print first and last few lines for context
            for line in stdout_lines[:10]:
                print(line)
            print("...")
            for line in stdout_lines[-10:]:
                print(line)

        if result.stderr:
            print(f"--- Error Output (if any) from {script_name} ---")
            print(result.stderr)  # Always print stderr if present

        print(f"--- Finished {script_name} successfully ---")
        print("-" * 30 + "\n")
        return True  # Indicate success

    except FileNotFoundError:
        print(f"\n*** Error: Script not found at '{full_script_path}' ***")
        print(
            "Please ensure the file exists and the path is correct relative to the project root."
        )
        print("-" * 30 + "\n")
        return False  # Indicate failure

    except subprocess.CalledProcessError as e:
        print(f"\n*** Error: {script_name} failed with exit code {e.returncode}. ***")
        print("--- Standard Output (if any) ---")
        print(e.stdout)  # Show stdout from the failed script
        print("--- Error Output ---")
        print(e.stderr)  # Show the captured error output from the failed script
        print("--------------------")
        print("-" * 30 + "\n")
        return False  # Indicate failure

    except Exception as e:
        # Catch any other unexpected exceptions during subprocess execution
        print(
            f"\n*** An unexpected error occurred while trying to run {script_name}: {e} ***"
        )
        print("-" * 30 + "\n")
        return False  # Indicate failure


# --- Main Execution Logic ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting Automated Pattern Processing Workflow")
    print(f"Project Root: {PROJECT_ROOT}")
    print("=" * 50 + "\n")

    # Step 1: Call the pattern resizing script
    # Input: Reads from 'input' subfolders
    # Output: Modifies images *in place* within 'input' subfolders (e.g., renames to name_X.jpg)
    print("Step 1: Resizing pattern images...")
    if not run_script(PATTERN_RESIZE_SCRIPT, "Pattern Resizer"):
        print("Workflow halted due to error in Pattern Resizer.")
        sys.exit(1)  # Exit the script with an error code

    # Step 2: Make mockups using the pattern script
    # Input: Reads resized images from 'input' subfolders
    # Output: Creates 'mocks' folders inside each 'input' subfolder
    print("Step 2: Generating mockups...")
    if not run_script(PATTERN_SCRIPT, "Mockup Generator"):
        print("Workflow halted due to error in Mockup Generator.")
        sys.exit(1)  # Exit the script with an error code

    # Step 3: Call zip.py to zip the *resized original images*
    # Input: --source_folder points to the main 'input' directory. zip.py scans subfolders.
    # Output: Creates 'zipped' folders inside each 'input' subfolder containing the final zip(s).
    print("Step 3: Zipping resized pattern images...")
    # Prepare arguments for zip.py
    zip_args = [
        "--source_folder",
        ZIP_SOURCE_FOLDER,
        "--max_size_mb",
        str(MAX_ZIP_SIZE_MB),
        "--image_quality",
        str(ZIP_IMAGE_QUALITY),
    ]
    if not run_script(ZIP_SCRIPT, "Zipper", script_args=zip_args):
        print("Workflow halted due to error in Zipper.")
        sys.exit(1)  # Exit the script with an error code

    # Optional: Add other steps like running seamless.py if it existed

    print("\n" + "=" * 50)
    print("Pattern processing workflow completed successfully!")
    print("=" * 50)
