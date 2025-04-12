"""
Command-line interface for wall art processing.
"""

import os
import sys
import argparse

from utils.common import setup_logging, run_script

# Set up logging
logger = setup_logging(__name__)


def main():
    """
    Main entry point for the wall art CLI.
    """
    parser = argparse.ArgumentParser(description="Wall art processing tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # All-in-one command
    all_parser = subparsers.add_parser("all", help="Run the complete wall art workflow")

    # Process command
    process_parser = subparsers.add_parser("process", help="Process wall art images")

    # Mockup command
    mockup_parser = subparsers.add_parser("mockup", help="Create wall art mockups")

    args = parser.parse_args()

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Define paths to scripts
    wall_art_script = os.path.join(script_dir, "wall_art.py")
    wall_art_mocks_script = os.path.join(script_dir, "wall_art_mocks.py")

    if args.command == "all":
        # Step 1: Process wall art images
        logger.info("Step 1: Processing wall art images...")
        if not run_script(wall_art_script, "Wall Art Processor"):
            logger.error("Error processing wall art images")
            sys.exit(1)

        # Step 2: Create mockups
        logger.info("Step 2: Creating wall art mockups...")
        if not run_script(wall_art_mocks_script, "Wall Art Mockup Generator"):
            logger.error("Error creating wall art mockups")
            sys.exit(1)

        logger.info("Wall art workflow completed successfully")

    elif args.command == "process":
        if not run_script(wall_art_script, "Wall Art Processor"):
            logger.error("Error processing wall art images")
            sys.exit(1)

    elif args.command == "mockup":
        if not run_script(wall_art_mocks_script, "Wall Art Mockup Generator"):
            logger.error("Error creating wall art mockups")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
