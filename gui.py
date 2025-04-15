#!/usr/bin/env python3
"""
Simple web-based GUI for the mockup tools and Etsy integration.
Uses Flask to create a simple web interface.
"""
import os
import re
import subprocess
import sys
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify
from utils.env_loader import load_env_from_file

# Load environment variables from .env file
load_env_from_file()

# Global variables for logging
log_messages = []

# Try to import the Gemini API client
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold

    print("Gemini API client found.")

    # Check if GEMINI_API_KEY is set
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key:
        # Configure the Gemini API
        genai.configure(api_key=gemini_api_key)
        print(
            f"Gemini API configured with key: {gemini_api_key[:4]}...{gemini_api_key[-4:]}"
        )

        # Test the API connection
        try:
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
            model = genai.GenerativeModel(model_name)
            print(f"Successfully initialized Gemini model: {model_name}")
        except Exception as e:
            print(f"Error initializing Gemini model: {e}")
    else:
        print("GEMINI_API_KEY not found in environment variables. Set it in .env file.")

except ImportError:
    print("Gemini API client not found. Installing...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "google-generativeai"]
        )
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        print("Gemini API client installed successfully.")

        # Check if GEMINI_API_KEY is set after installation
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if gemini_api_key:
            # Configure the Gemini API
            genai.configure(api_key=gemini_api_key)
            print(
                f"Gemini API configured with key: {gemini_api_key[:4]}...{gemini_api_key[-4:]}"
            )
        else:
            print(
                "GEMINI_API_KEY not found in environment variables. Set it in .env file."
            )
    except Exception as e:
        print(f"Error installing Gemini API client: {e}")

# Create Flask app
app = Flask(__name__)

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Global variables for logging
log_messages = []


# Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/log")
def get_log():
    global log_messages
    messages = log_messages.copy()
    log_messages.clear()
    return jsonify({"messages": messages})


@app.route("/get-subfolders")
def get_subfolders():
    """Get all subfolders in the input directory."""
    try:
        input_dir = "input"
        # Ensure the input directory exists
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
            return jsonify({"subfolders": []})

        # Get all subfolders
        subfolders = [
            f
            for f in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, f)) and not f.startswith(".")
        ]

        return jsonify({"subfolders": sorted(subfolders)})
    except Exception as e:
        return jsonify({"error": str(e), "subfolders": []})


@app.route("/run", methods=["POST"])
def run_command():
    data = request.json
    command_type = data.get("command")

    if command_type == "pattern-workflow":
        command = [
            "python",
            "-m",
            "pattern.cli",
            "all",
            "--input_dir",
            data.get("inputDir"),
        ]

        # Add video creation if requested
        if data.get("createVideo"):
            command.append("--create_video")
    elif command_type == "pattern-resize":
        command = [
            "python",
            "-m",
            "pattern.cli",
            "resize",
            "--input_dir",
            data.get("inputDir"),
        ]
    elif command_type == "pattern-mockups":
        command = [
            "python",
            "-m",
            "pattern.cli",
            "mockup",
            "--input_dir",
            data.get("inputDir"),
        ]
    elif command_type == "clipart-workflow":
        command = [
            "python",
            "-m",
            "clipart.cli",
            "all",
            "--input_dir",
            data.get("inputDir"),
        ]

        # Add video creation if requested
        if data.get("createVideo"):
            command.append("--create_video")
    elif command_type == "clipart-resize":
        command = [
            "python",
            "-m",
            "clipart.cli",
            "resize",
            "--input_folder",
            data.get("inputDir"),
        ]
    elif command_type == "clipart-mockups":
        command = [
            "python",
            "-m",
            "clipart.cli",
            "mockup",
            "--input_dir",
            data.get("inputDir"),
        ]

        # Add video creation if requested
        if data.get("createVideo"):
            command.append("--create_video")
    elif command_type == "clipart-crop-multi":
        command = [
            "python",
            "-m",
            "clipart.crop_multi",
        ]
    elif command_type == "folder-rename":
        # Use the folder_renamer module directly instead of cli.py
        command = [
            "python",
            "-m",
            "folder_renamer",
            "--input_dir",
            data.get("inputDir"),
        ]

        # Add provider if specified
        if data.get("provider"):
            command.extend(["--provider", data.get("provider")])

        if data.get("maxRetries") is not None:
            command.extend(["--max-retries", str(data.get("maxRetries"))])

        if data.get("model"):
            command.extend(["--model", data.get("model")])
    elif command_type == "etsy-auth":
        command = ["python", "-m", "etsy.cli", "etsy", "auth"]
    elif command_type == "etsy-generate":
        # Prepare command for generating content
        command = [
            "python",
            "-m",
            "etsy.cli",
            "etsy",
            "generate",
            "--folder",
            data.get("folder"),
            "--product_type",
            data.get("productType"),
        ]

        # Check if we have Gemini API key
        gemini_api_key = os.environ.get("GEMINI_API_KEY")

        if not gemini_api_key:
            error_msg = "GEMINI_API_KEY not found in environment variables. Please set it in .env file."
            log_messages.append(error_msg)
            return jsonify({"command": " ".join(command), "error": error_msg}), 400

        # Always use Gemini provider
        log_messages.append("Using Gemini provider")
        command.extend(["--provider", "gemini"])

        # Create a process to capture output
        try:
            log_messages.append(f"Running command: {' '.join(command)}")

            # Run the command directly to capture all output
            try:
                # First, try running with subprocess.check_output to capture all output including errors
                log_messages.append("Executing command with detailed error capture...")
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=os.environ.copy(),  # Ensure environment variables are passed
                )

                # Log stdout
                for line in result.stdout.splitlines():
                    log_messages.append(line.strip())

                # Log stderr (if any)
                if result.stderr:
                    log_messages.append("Error output:")
                    for line in result.stderr.splitlines():
                        log_messages.append(f"ERROR: {line.strip()}")

                # Check return code
                if result.returncode != 0:
                    error_msg = f"Command failed with return code {result.returncode}"
                    log_messages.append(error_msg)
                    if result.stderr:
                        error_msg += f": {result.stderr}"
                    return (
                        jsonify(
                            {
                                "command": " ".join(command),
                                "error": error_msg,
                            }
                        ),
                        400,
                    )

                # Combine stdout and stderr for our output
                # The content is being printed to stderr in the CLI command
                output = result.stdout

                # If stdout is empty but stderr has content, use stderr
                if not output.strip() and result.stderr:
                    # Extract the content from stderr
                    stderr_lines = result.stderr.splitlines()
                    content_lines = []

                    # Look for the content in stderr
                    for i, line in enumerate(stderr_lines):
                        if "Title:" in line and i < len(stderr_lines) - 1:
                            # Found the title, collect all lines until the end
                            content_lines = stderr_lines[i:]
                            break

                    if content_lines:
                        # Join the content lines
                        output = "\n".join(
                            line.replace("ERROR: ", "") for line in content_lines
                        )
                        log_messages.append(
                            "Found content in stderr, using it instead of stdout"
                        )

            except Exception as e:
                error_msg = f"Error executing command: {e}"
                log_messages.append(error_msg)
                return jsonify({"command": " ".join(command), "error": error_msg}), 500

            # Parse the output to extract content
            content = {"title": "", "description": "", "tags": []}

            # Add debug logging for the output
            log_messages.append("Raw output from command:")
            log_messages.append(output)

            # Add more detailed debugging for tags
            tags_start = output.find("Tags:")
            if tags_start >= 0:
                tags_text = output[
                    tags_start : tags_start + 100
                ]  # Show first 100 chars after Tags:
                log_messages.append(
                    f"Tags section starts at position {tags_start}, preview: {tags_text}"
                )

            # Look for title in the output
            title_start = output.find("Title:")
            desc_start = output.find("Description:")

            if title_start >= 0 and desc_start > title_start:
                # Extract everything between Title: and Description:
                title = output[title_start + 6 : desc_start].strip()
                # Remove any ** markers
                title = re.sub(r"^\*\*\s*", "", title)
                content["title"] = title
                log_messages.append(f"Found title with length: {len(title)}")
            else:
                # Try regex as a fallback
                title_match = re.search(
                    r"Title:\s*\*?\*?\s*(.+?)(?:\n|Description:)", output, re.DOTALL
                )
                if title_match:
                    title = title_match.group(1).strip()
                    # Remove any ** markers
                    title = re.sub(r"^\*\*\s*", "", title)
                    content["title"] = title
                    log_messages.append(f"Extracted title via regex: {title}")
                else:
                    # Try another approach - look for the line that starts with "Title:"
                    lines = output.splitlines()
                    for line in lines:
                        if line.strip().startswith("Title:"):
                            title = line.split("Title:", 1)[1].strip()
                            content["title"] = title
                            log_messages.append(f"Found title in line: {title}")
                            break
                    else:
                        log_messages.append("Failed to extract title using all methods")

            # Look for description in the output
            # First, find the start and end positions
            desc_start = output.find("Description:")
            tags_start = output.find("Tags:")

            if desc_start >= 0 and tags_start > desc_start:
                # Extract everything between Description: and Tags:
                full_desc = output[desc_start + 12 : tags_start].strip()
                log_messages.append(
                    f"Found description section with length: {len(full_desc)}"
                )
                content["description"] = full_desc
            else:
                # Try regex as a fallback
                log_messages.append("Trying regex fallback for description")
                desc_match = re.search(r"Description:\s*([\s\S]+?)\s*Tags:", output)
                if desc_match:
                    description = desc_match.group(1).strip()
                    content["description"] = description
                    log_messages.append(
                        f"Extracted description via regex with length: {len(description)}"
                    )
                else:
                    # Try another approach - look for lines after "Description:" until "Tags:"
                    lines = output.splitlines()
                    desc_lines = []
                    in_desc = False

                    for line in lines:
                        if "Description:" in line:
                            in_desc = True
                            # Add the part after "Description:" if on same line
                            if line.strip() != "Description:":
                                desc_lines.append(
                                    line.split("Description:", 1)[1].strip()
                                )
                        elif "Tags:" in line:
                            in_desc = False
                        elif in_desc:
                            desc_lines.append(line.strip())

                    if desc_lines:
                        description = "\n".join(desc_lines)
                        content["description"] = description
                        log_messages.append(
                            f"Extracted description line by line: {len(description)} chars"
                        )
                    else:
                        log_messages.append(
                            "Failed to extract description using all methods"
                        )

            # Look for tags in the output
            tags_start = output.find("Tags:")
            if tags_start >= 0:
                # Extract everything after Tags:
                tags_text = output[tags_start + 5 :].strip()

                # Log the raw tags text for debugging
                log_messages.append(f"Raw tags text: '{tags_text}'")

                # Look for the actual tags pattern
                tags_pattern = re.search(r"([^\d]+?)(?:\d{4}-\d{2}-\d{2}|$)", tags_text)
                if tags_pattern:
                    clean_tags = tags_pattern.group(1).strip()
                    log_messages.append(f"Extracted clean tags: '{clean_tags}'")

                    # Split by comma and clean up
                    content["tags"] = [
                        tag.strip() for tag in clean_tags.split(",") if tag.strip()
                    ]
                    log_messages.append(
                        f"Found {len(content['tags'])} tags: {', '.join(content['tags'])}"
                    )
                else:
                    # Try a simpler approach - just take the first line
                    first_line = tags_text.split("\n")[0].strip()
                    log_messages.append(f"Using first line as tags: '{first_line}'")

                    # Split by comma and clean up
                    content["tags"] = [
                        tag.strip() for tag in first_line.split(",") if tag.strip()
                    ]
                    log_messages.append(
                        f"Found {len(content['tags'])} tags from first line: {', '.join(content['tags'])}"
                    )
            else:
                # Try regex as a fallback
                log_messages.append("Trying regex fallback for tags")
                tags_match = re.search(
                    r"Tags:\s*(.+?)(?:\n\d{4}-\d{2}-\d{2}|$)", output, re.DOTALL
                )
                if tags_match:
                    tags_text = tags_match.group(1).strip()
                    log_messages.append(f"Regex found tags text: '{tags_text}'")

                    # Remove any ** markers
                    tags_text = re.sub(r"^\*\*\s*", "", tags_text)

                    # Take just the first line if there are multiple lines
                    first_line = tags_text.split("\n")[0].strip()
                    log_messages.append(f"Using first line from regex: '{first_line}'")

                    # Split by comma and clean up
                    content["tags"] = [
                        tag.strip() for tag in first_line.split(",") if tag.strip()
                    ]
                    log_messages.append(
                        f"Extracted {len(content['tags'])} tags via regex: {', '.join(content['tags'])}"
                    )
                else:
                    # Try another approach - look for the line that starts with "Tags:"
                    lines = output.splitlines()
                    for line in lines:
                        if line.strip().startswith("Tags:"):
                            tags_text = line.split("Tags:", 1)[1].strip()
                            log_messages.append(
                                f"Found line starting with Tags: '{tags_text}'"
                            )

                            # Split by comma and clean up
                            content["tags"] = [
                                tag.strip()
                                for tag in tags_text.split(",")
                                if tag.strip()
                            ]
                            log_messages.append(
                                f"Found {len(content['tags'])} tags in line: {', '.join(content['tags'])}"
                            )
                            break
                    else:
                        log_messages.append("Failed to extract tags using all methods")

            log_messages.append("Content generation completed successfully.")
            return jsonify({"command": " ".join(command), "content": content})

        except Exception as e:
            log_messages.append(f"Error running command: {e}")
            return jsonify({"command": " ".join(command), "error": str(e)}), 500

    elif command_type == "etsy-create":
        # Validate inputs
        title = data.get("title", "")
        tags = data.get("tags", [])

        # Title validation (max 140 characters)
        if len(title) > 140:
            return (
                jsonify(
                    {
                        "error": f"Title is too long ({len(title)} characters). Etsy allows a maximum of 140 characters."
                    }
                ),
                400,
            )

        # Tags validation (max 13 tags, each max 20 characters)
        if len(tags) > 13:
            return (
                jsonify(
                    {
                        "error": f"Too many tags ({len(tags)}). Etsy allows a maximum of 13 tags."
                    }
                ),
                400,
            )

        # Check individual tag length
        long_tags = [tag for tag in tags if len(tag) > 20]
        if long_tags:
            return (
                jsonify(
                    {
                        "error": f"The following tags are too long (max 20 characters each): {', '.join(long_tags)}"
                    }
                ),
                400,
            )

        # Prepare command
        command = [
            "python",
            "-m",
            "etsy.cli",
            "etsy",
            "create",
            "--folder",
            data.get("folder"),
            "--product_type",
            data.get("productType"),
        ]

        # Add title if provided
        if title:
            command.extend(["--title", title])

        # Add description if provided
        if data.get("description"):
            command.extend(["--description", data.get("description")])

        # Add tags if provided
        if tags and len(tags) > 0:
            command.extend(["--tags", ",".join(tags)])

        if data.get("draft"):
            command.append("--draft")

        # Log the command being executed
        log_messages.append(f"Creating Etsy listing for {data.get('folder')}...")

    elif command_type == "etsy-bulk-prepare":
        # Prepare command for bulk preparation
        command = [
            "python",
            "-m",
            "etsy.cli",
            "etsy",
            "bulk-prepare",
            "--input_dir",
            "input",  # Always use the input directory
            "--product_type",
            data.get("productType"),
            "--output_file",
            "prepared_listings.json",
        ]

        # Add provider if specified
        if data.get("provider"):
            command.extend(["--provider", data.get("provider")])
            log_messages.append(f"Using AI provider: {data.get('provider')}")

        log_messages.append(
            f"Starting bulk preparation of {data.get('productType')} listings from input directory..."
        )

    elif command_type == "etsy-bulk-create":
        # Prepare command for bulk creation
        command = [
            "python",
            "-m",
            "etsy.cli",
            "etsy",
            "bulk-create",
            "--input_dir",
            "input",  # Always use the input directory
            "--product_type",
            data.get("productType"),
        ]

        # Add draft flag if specified
        if data.get("draft"):
            command.append("--draft")

        log_messages.append(
            f"Starting bulk creation of {data.get('productType')} listings from input directory..."
        )

    elif command_type == "etsy-upload-prepared":
        # Get the prepared listings file
        import json
        import os

        prepared_file = data.get("file", "prepared_listings.json")
        if not os.path.exists(prepared_file):
            # Create an empty prepared_listings.json file if it doesn't exist
            try:
                log_messages.append(
                    f"Creating empty prepared listings file: {prepared_file}"
                )
                with open(prepared_file, "w") as f:
                    json.dump([], f)
                log_messages.append(
                    f"Created empty prepared listings file: {prepared_file}"
                )
                # Return a message indicating no listings are available
                return (
                    jsonify(
                        {
                            "error": "No prepared listings available. Please prepare listings first."
                        }
                    ),
                    400,
                )
            except Exception as e:
                log_messages.append(f"Error creating prepared listings file: {e}")
                return (
                    jsonify({"error": f"Error creating prepared listings file: {e}"}),
                    500,
                )

        try:
            with open(prepared_file, "r") as f:
                prepared_listings = json.load(f)

            # Get the listing index to upload
            listing_index = data.get("index", 0)
            if listing_index < 0 or listing_index >= len(prepared_listings):
                return (
                    jsonify({"error": f"Invalid listing index: {listing_index}"}),
                    400,
                )

            # Get the listing data
            listing_data = prepared_listings[listing_index]

            # Prepare command for uploading a single prepared listing
            command = [
                "python",
                "-m",
                "etsy.cli",
                "etsy",
                "create",
                "--folder",
                listing_data["folder_path"],
                "--product_type",
                listing_data["product_type"],
                "--title",
                listing_data["title"],
                "--description",
                listing_data["description"],
                "--tags",
                ",".join(listing_data["tags"]),
            ]

            # Add draft flag if specified
            if data.get("draft"):
                command.append("--draft")

            log_messages.append(
                f"Uploading prepared listing {listing_index + 1}/{len(prepared_listings)}: {listing_data['folder_name']}"
            )

            # Return the total number of listings for progress tracking
            return jsonify(
                {
                    "command": " ".join(command),
                    "total": len(prepared_listings),
                    "current": listing_index + 1,
                    "folder": listing_data["folder_name"],
                    "title": listing_data["title"],
                }
            )

        except Exception as e:
            log_messages.append(f"Error loading prepared listings: {e}")
            return jsonify({"error": f"Error loading prepared listings: {e}"}), 500

    elif command_type == "etsy-get-prepared":
        # Get the prepared listings file
        import json
        import os

        prepared_file = data.get("file", "prepared_listings.json")
        if not os.path.exists(prepared_file):
            # Create an empty prepared_listings.json file if it doesn't exist
            try:
                log_messages.append(
                    f"Creating empty prepared listings file: {prepared_file}"
                )
                with open(prepared_file, "w") as f:
                    json.dump([], f)
                log_messages.append(
                    f"Created empty prepared listings file: {prepared_file}"
                )
            except Exception as e:
                log_messages.append(f"Error creating prepared listings file: {e}")
                return (
                    jsonify({"error": f"Error creating prepared listings file: {e}"}),
                    500,
                )

        try:
            with open(prepared_file, "r") as f:
                prepared_listings = json.load(f)

            # Process the listings to add relative paths for frontend
            for listing in prepared_listings:
                # Add relative paths for mockup images
                if "mockup_images" in listing:
                    listing["mockup_images_rel"] = [
                        path.replace(os.getcwd() + "/", "")
                        for path in listing["mockup_images"]
                    ]

                # Add relative paths for zip files
                if "zip_files" in listing:
                    listing["zip_files_rel"] = [
                        path.replace(os.getcwd() + "/", "")
                        for path in listing["zip_files"]
                    ]

                # Add relative paths for video files
                if "video_files" in listing:
                    listing["video_files_rel"] = [
                        path.replace(os.getcwd() + "/", "")
                        for path in listing["video_files"]
                    ]

            # Return the prepared listings
            return jsonify(
                {"listings": prepared_listings, "count": len(prepared_listings)}
            )

        except Exception as e:
            log_messages.append(f"Error loading prepared listings: {e}")
            return jsonify({"error": f"Error loading prepared listings: {e}"}), 500
    elif command_type == "etsy-update-prepared":
        # Get the prepared listings file
        import json
        import os

        prepared_file = data.get("file", "prepared_listings.json")
        if not os.path.exists(prepared_file):
            # Create an empty prepared_listings.json file if it doesn't exist
            try:
                log_messages.append(
                    f"Creating empty prepared listings file: {prepared_file}"
                )
                with open(prepared_file, "w") as f:
                    json.dump([], f)
                log_messages.append(
                    f"Created empty prepared listings file: {prepared_file}"
                )
                # Return a message indicating no listings are available
                return (
                    jsonify(
                        {
                            "error": "No prepared listings available. Please prepare listings first."
                        }
                    ),
                    400,
                )
            except Exception as e:
                log_messages.append(f"Error creating prepared listings file: {e}")
                return (
                    jsonify({"error": f"Error creating prepared listings file: {e}"}),
                    500,
                )

        try:
            with open(prepared_file, "r") as f:
                prepared_listings = json.load(f)

            # Get the listing index to update
            listing_index = data.get("index", 0)
            if listing_index < 0 or listing_index >= len(prepared_listings):
                return (
                    jsonify({"error": f"Invalid listing index: {listing_index}"}),
                    400,
                )

            # Get the listing data
            listing_data = prepared_listings[listing_index]
            folder_name = listing_data["folder_name"]

            # Update the listing data
            listing_data["title"] = data.get("title", listing_data["title"])
            listing_data["description"] = data.get(
                "description", listing_data["description"]
            )
            listing_data["tags"] = data.get("tags", listing_data["tags"])

            # Save the updated listings
            with open(prepared_file, "w") as f:
                json.dump(prepared_listings, f, indent=2)

            log_messages.append(f"Updated prepared listing: {folder_name}")
            return jsonify({"success": True, "folder_name": folder_name})

        except Exception as e:
            log_messages.append(f"Error updating prepared listing: {e}")
            return jsonify({"error": f"Error updating prepared listing: {e}"}), 500

    elif command_type == "etsy-delete-prepared":
        # Delete the prepared listings file
        import os

        prepared_file = data.get("file", "prepared_listings.json")
        if not os.path.exists(prepared_file):
            return jsonify({"success": True, "message": "File already deleted"})

        try:
            os.remove(prepared_file)
            log_messages.append(f"Deleted prepared listings file: {prepared_file}")
            return jsonify({"success": True, "message": "File deleted successfully"})
        except Exception as e:
            log_messages.append(f"Error deleting prepared listings file: {e}")
            return jsonify({"error": f"Error deleting file: {e}"}), 500

    elif command_type == "etsy-remove-uploaded":
        # Remove a listing from the prepared listings file after it's been uploaded
        import json
        import os

        prepared_file = data.get("file", "prepared_listings.json")
        if not os.path.exists(prepared_file):
            # Create an empty prepared_listings.json file if it doesn't exist
            try:
                log_messages.append(
                    f"Creating empty prepared listings file: {prepared_file}"
                )
                with open(prepared_file, "w") as f:
                    json.dump([], f)
                log_messages.append(
                    f"Created empty prepared listings file: {prepared_file}"
                )
                # Return a message indicating no listings are available
                return (
                    jsonify(
                        {"error": "No prepared listings available. Nothing to remove."}
                    ),
                    400,
                )
            except Exception as e:
                log_messages.append(f"Error creating prepared listings file: {e}")
                return (
                    jsonify({"error": f"Error creating prepared listings file: {e}"}),
                    500,
                )

        try:
            # Get the listing index to remove
            listing_index = data.get("index", 0)

            # Read the current listings
            with open(prepared_file, "r") as f:
                prepared_listings = json.load(f)

            # Validate index
            if listing_index < 0 or listing_index >= len(prepared_listings):
                return (
                    jsonify({"error": f"Invalid listing index: {listing_index}"}),
                    400,
                )

            # Get the listing data for logging
            listing_data = prepared_listings[listing_index]
            folder_name = listing_data["folder_name"]

            # Remove the listing
            prepared_listings.pop(listing_index)

            # Save the updated listings
            with open(prepared_file, "w") as f:
                json.dump(prepared_listings, f, indent=2)

            # Ensure the file is written to disk
            import time

            time.sleep(0.5)  # Small delay to ensure file is written

            log_messages.append(
                f"Removed uploaded listing from prepared listings: {folder_name}"
            )
            return jsonify(
                {
                    "success": True,
                    "message": f"Removed listing: {folder_name}",
                    "remaining": len(prepared_listings),
                }
            )

        except Exception as e:
            log_messages.append(f"Error removing listing: {e}")
            return jsonify({"error": f"Error removing listing: {e}"}), 500
    else:
        return jsonify({"error": "Invalid command"}), 400

    # Run the command in a separate thread
    threading.Thread(target=run_command_thread, args=(command,)).start()

    return jsonify({"command": " ".join(command)})


def run_command_thread(command):
    """Run a command in a separate thread and capture output."""
    global log_messages

    try:
        log_messages.append(f"Running command: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            log_messages.append(line.strip())

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            log_messages.append(f"Command failed with return code {return_code}")
        else:
            log_messages.append("Command completed successfully.")
    except Exception as e:
        log_messages.append(f"Error running command: {e}")


def open_browser():
    """Open browser after a short delay."""
    import time

    time.sleep(1.5)
    webbrowser.open("http://localhost:8095")


if __name__ == "__main__":
    # Open browser
    threading.Thread(target=open_browser).start()

    # Start Flask app
    app.run(debug=False, port=8095)
