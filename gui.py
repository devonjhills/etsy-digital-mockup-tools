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
            "cli.py",
            "pattern",
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
            "cli.py",
            "pattern",
            "resize",
            "--input_dir",
            data.get("inputDir"),
        ]
    elif command_type == "pattern-mockups":
        command = [
            "python",
            "cli.py",
            "pattern",
            "mockup",
            "--input_dir",
            data.get("inputDir"),
        ]
    elif command_type == "clipart-workflow":
        command = [
            "python",
            "cli.py",
            "clipart",
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
            "cli.py",
            "clipart",
            "resize",
            "--input_folder",
            data.get("inputDir"),
        ]
    elif command_type == "clipart-mockups":
        command = [
            "python",
            "cli.py",
            "clipart",
            "mockup",
            "--input_dir",
            data.get("inputDir"),
        ]
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

        # Check if GEMINI_API_KEY is set
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            error_msg = "GEMINI_API_KEY not found in environment variables. Please set it in .env file."
            log_messages.append(error_msg)
            return jsonify({"command": " ".join(command), "error": error_msg}), 400

        # Ensure the Gemini API is properly configured
        try:
            import google.generativeai as genai

            genai.configure(api_key=gemini_api_key)
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
            log_messages.append(f"Using Gemini model: {model_name}")
        except Exception as e:
            error_msg = f"Error configuring Gemini API: {e}"
            log_messages.append(error_msg)
            return jsonify({"command": " ".join(command), "error": error_msg}), 500

        # Create a process to capture output
        try:
            log_messages.append(f"Running command: {' '.join(command)}")
            log_messages.append(
                f"Using Gemini model: {os.environ.get('GEMINI_MODEL', 'gemini-2.5-pro-exp-03-25')}"
            )

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
