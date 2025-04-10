#!/usr/bin/env python3
"""
Simple web-based GUI for the mockup tools and Etsy integration.
Uses Flask to create a simple web interface.
"""
import os
import subprocess
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify
from utils.env_loader import load_env_from_file

# Load environment variables from .env file
load_env_from_file()

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
        command = ["python", "cli.py", "etsy", "auth"]
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
            "cli.py",
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
