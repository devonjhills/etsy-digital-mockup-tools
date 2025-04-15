"""
Module for renaming input subfolders based on AI image analysis.
"""

import os
import re
import logging
import shutil
from typing import Optional, List, Tuple

# Set up logging
from utils.common import setup_logging

logger = setup_logging(__name__)

# Import AI provider factory
from ai_providers.factory import AIProviderFactory


def find_image_in_subfolder(subfolder_path: str) -> Optional[str]:
    """
    Find a suitable image in the subfolder for analysis.

    Args:
        subfolder_path: Path to the subfolder

    Returns:
        Path to a suitable image or None if no image is found
    """
    # Use os.listdir instead of glob to avoid issues with special characters
    try:
        # Get all files in the subfolder
        all_files = os.listdir(subfolder_path)

        # Filter image files by extension
        image_files = []
        for file in all_files:
            # Check if the file has an image extension (case insensitive)
            lower_file = file.lower()
            if (
                lower_file.endswith(".png")
                or lower_file.endswith(".jpg")
                or lower_file.endswith(".jpeg")
            ):
                image_files.append(os.path.join(subfolder_path, file))

        # Log the found images for debugging
        if image_files:
            logger.info(
                f"Found {len(image_files)} images in {os.path.basename(subfolder_path)}"
            )
        else:
            logger.warning(f"No images found in {os.path.basename(subfolder_path)}")

        # Sort files to get a consistent result
        image_files.sort()

        # Return the first image found, if any
        return image_files[0] if image_files else None
    except Exception as e:
        logger.error(f"Error finding images in {subfolder_path}: {e}")
        return None


def rename_subfolder(subfolder_path: str, new_name: str) -> Optional[str]:
    """
    Rename a subfolder with a new name.

    Args:
        subfolder_path: Path to the subfolder
        new_name: New name for the subfolder

    Returns:
        Path to the renamed subfolder or None if renaming failed
    """
    try:
        # Get the parent directory and original folder name
        parent_dir = os.path.dirname(subfolder_path)
        original_folder_name = os.path.basename(subfolder_path)

        logger.info(
            f"Preparing to rename folder: '{original_folder_name}' to '{new_name}'"
        )

        # Create a safe name for the folder
        safe_name = re.sub(r"[^a-zA-Z0-9\s]", "", new_name)
        # Keep spaces instead of converting to underscores
        safe_name = re.sub(r"\s+", " ", safe_name)

        # Ensure the safe name is not empty
        if not safe_name:
            safe_name = "Unnamed_Item"
            logger.warning(
                f"Generated name was empty after sanitization, using '{safe_name}' instead"
            )

        # Create the new path
        new_path = os.path.join(parent_dir, safe_name)

        # Check if the new path already exists
        if os.path.exists(new_path):
            logger.warning(f"Destination path already exists: {new_path}")
            # Add a suffix to make the name unique
            i = 1
            while os.path.exists(f"{new_path}_{i}"):
                i += 1
            new_path = f"{new_path}_{i}"
            logger.info(f"Using unique name: {os.path.basename(new_path)}")

        # Check if the source path exists
        if not os.path.exists(subfolder_path):
            logger.error(f"Source folder does not exist: {subfolder_path}")
            return None

        # Check if source and destination are the same
        if os.path.normpath(subfolder_path) == os.path.normpath(new_path):
            logger.warning(
                f"Source and destination paths are the same: {subfolder_path}"
            )
            return subfolder_path

        # Rename the folder
        logger.info(
            f"Renaming folder from '{original_folder_name}' to '{os.path.basename(new_path)}'"
        )
        shutil.move(subfolder_path, new_path)
        logger.info(
            f"Successfully renamed folder: {original_folder_name} -> {os.path.basename(new_path)}"
        )

        return new_path

    except Exception as e:
        logger.error(f"Error renaming folder '{subfolder_path}': {e}")
        return None


def process_input_directory(
    input_dir: str,
    provider_type: str = None,
    api_key: str = None,
    model_name: str = None,
    max_retries: int = 2,
) -> List[Tuple[str, str]]:
    """
    Process all subfolders in the input directory and rename them based on AI image analysis.

    Args:
        input_dir: Path to the input directory
        provider_type: Type of AI provider to use ('gemini', 'openrouter', or None for default)
        api_key: API key for the provider (if None, will try to get from environment)
        model_name: Model name to use (if None, will try to get from environment)
        max_retries: Maximum number of retries for API calls

    Returns:
        List of tuples containing (original_path, new_path) for each renamed subfolder
    """
    if not os.path.isdir(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return []

    # Find subfolders to process
    folders_to_ignore = {"mocks", "zipped", "videos"}
    subfolders = [
        os.path.join(input_dir, d)
        for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and d not in folders_to_ignore
    ]

    if not subfolders:
        logger.warning("No valid subfolders found in the input directory to process.")
        return []

    logger.info(f"Found {len(subfolders)} subfolder(s) to process for renaming.")

    # Get the AI provider
    if provider_type:
        provider = AIProviderFactory.create_provider(provider_type, api_key, model_name)
    else:
        provider = AIProviderFactory.get_default_provider()

    if not provider:
        logger.error("Failed to create AI provider. Check API keys and provider type.")
        return []

    logger.info(
        f"Using AI provider: {provider.__class__.__name__} with model: {provider.model_name}"
    )

    renamed_folders = []

    for subfolder in subfolders:
        folder_name = os.path.basename(subfolder)
        logger.info(f"Processing folder for renaming: {folder_name}")

        # Find an image in the subfolder
        image_path = find_image_in_subfolder(subfolder)
        if not image_path:
            logger.warning(f"No image found in {folder_name}. Skipping renaming.")
            continue

        # Generate a title from the image - we want a short, marketable title for Etsy
        # The title will be used as the folder name and should be descriptive of the product
        title = provider.generate_title_from_image(image_path, max_retries)

        # No fallback - if title generation failed, skip this folder
        if not title:
            logger.error(
                f"Failed to generate title for {folder_name} using {provider.__class__.__name__}. Skipping renaming."
            )
            continue

        # Rename the subfolder
        new_path = rename_subfolder(subfolder, title)
        if new_path:
            renamed_folders.append((subfolder, new_path))

    logger.info(f"Renamed {len(renamed_folders)} out of {len(subfolders)} subfolders.")
    return renamed_folders


def main():
    """Main entry point for the folder renamer CLI."""
    import argparse
    import os
    import sys
    from utils.env_loader import load_env_from_file

    parser = argparse.ArgumentParser(
        description="Rename input subfolders based on AI image analysis"
    )
    parser.add_argument(
        "--input_dir", default="input", help="Path to the input directory"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openrouter"],
        help="AI provider to use (default: auto-detect based on available API keys)",
    )
    parser.add_argument(
        "--model",
        help="Model name to use (default: from environment variables)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum number of retries for API calls (default: 2)",
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    load_env_from_file()

    # Set AI_PROVIDER environment variable if provider is specified
    if args.provider:
        os.environ["AI_PROVIDER"] = args.provider

    # Log the configuration
    logger.info(f"Input directory: {args.input_dir}")
    if args.provider:
        logger.info(f"Using provider: {args.provider}")
    if args.model:
        logger.info(f"Using model: {args.model}")
    logger.info(f"Max retries: {args.max_retries}")

    # Process the input directory
    renamed_folders = process_input_directory(
        input_dir=args.input_dir,
        provider_type=args.provider,
        model_name=args.model,
        max_retries=args.max_retries,
    )

    # Print summary
    if renamed_folders:
        logger.info(f"Successfully renamed {len(renamed_folders)} folders:")
        for old_path, new_path in renamed_folders:
            logger.info(
                f"  {os.path.basename(old_path)} -> {os.path.basename(new_path)}"
            )
    else:
        logger.warning("No folders were renamed.")


if __name__ == "__main__":
    main()


# Allow running as a module
def run_module():
    main()
