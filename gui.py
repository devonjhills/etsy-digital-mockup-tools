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

# Create Flask app
app = Flask(__name__)

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Create HTML template
with open("templates/index.html", "w") as f:
    f.write(
        """
<!DOCTYPE html>
<html>
<head>
    <title>Mockup Tools & Etsy Integration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f1f1f1;
            margin-right: 5px;
            border-radius: 5px 5px 0 0;
            border: none;
        }
        .tab.active {
            background-color: #4CAF50;
            color: white;
        }
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 0 0 5px 5px;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        .log-area {
            margin-top: 20px;
            padding: 10px;
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            height: 200px;
            overflow-y: auto;
            font-family: monospace;
        }
        .section {
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .actions {
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mockup Tools & Etsy Integration</h1>

        <div class="tabs">
            <button class="tab active" id="pattern-tab">Pattern</button>
            <button class="tab" id="clipart-tab">Clipart</button>
            <button class="tab" id="etsy-tab">Etsy</button>
        </div>

        <div id="pattern" class="tab-content active">
            <h2>Pattern Tools</h2>

            <div class="section">
                <h3>Input Directory</h3>
                <div class="form-group">
                    <label for="pattern-input-dir">Input Directory:</label>
                    <input type="text" id="pattern-input-dir" name="pattern-input-dir" value="input">
                </div>

                <div class="actions">
                    <button onclick="runPatternWorkflow()">Run Complete Workflow</button>
                    <button onclick="runPatternResize()">Resize Only</button>
                    <button onclick="runPatternMockups()">Create Mockups Only</button>
                </div>
            </div>
        </div>

        <div id="clipart" class="tab-content">
            <h2>Clipart Tools</h2>

            <div class="section">
                <h3>Input Directory</h3>
                <div class="form-group">
                    <label for="clipart-input-dir">Input Directory:</label>
                    <input type="text" id="clipart-input-dir" name="clipart-input-dir" value="input">
                </div>

                <div class="actions">
                    <button onclick="runClipartWorkflow()">Run Complete Workflow</button>
                    <button onclick="runClipartResize()">Resize Only</button>
                    <button onclick="runClipartMockups()">Create Mockups Only</button>
                </div>
            </div>
        </div>

        <div id="etsy" class="tab-content">
            <h2>Etsy Integration</h2>

            <div class="section">
                <h3>Authentication</h3>
                <button id="auth-button" onclick="authenticateEtsy()">Authenticate with Etsy</button>
                <div id="auth-status" style="color: green; margin-top: 10px;"></div>
            </div>

            <div class="section">
                <h3>Create Single Listing</h3>
                <div class="form-group">
                    <label for="etsy-subfolder">Select Subfolder from 'input':</label>
                    <select id="etsy-subfolder" name="etsy-subfolder">
                        <option value="">-- Select a subfolder --</option>
                        <!-- Will be populated dynamically -->
                    </select>
                    <button onclick="refreshSubfolders()" style="margin-top: 5px;">Refresh Subfolders</button>
                </div>

                <div class="form-group">
                    <label for="etsy-product-type">Product Type:</label>
                    <select id="etsy-product-type" name="etsy-product-type">
                        <option value="pattern">Pattern</option>
                        <option value="clipart">Clipart</option>
                        <option value="wall_art">Wall Art</option>
                        <option value="brush_strokes">Brush Strokes</option>
                    </select>
                </div>

                <div class="form-group">
                    <input type="checkbox" id="etsy-draft" name="etsy-draft" checked>
                    <label for="etsy-draft" style="display: inline;">Create as Draft</label>
                </div>

                <div class="actions">
                    <button onclick="createEtsyListing()">Create Listing</button>
                </div>
            </div>
        </div>

        <div class="section">
            <h3>Log</h3>
            <div class="log-area" id="log"></div>
            <button onclick="clearLog()" style="margin-top: 10px;">Clear Log</button>
        </div>
    </div>

    <script>
        // Add event listeners to tab buttons
        document.addEventListener('DOMContentLoaded', function() {
            // Pattern tab
            document.getElementById('pattern-tab').addEventListener('click', function() {
                showTab('pattern');
            });

            // Clipart tab
            document.getElementById('clipart-tab').addEventListener('click', function() {
                showTab('clipart');
            });

            // Etsy tab
            document.getElementById('etsy-tab').addEventListener('click', function() {
                showTab('etsy');
                // Refresh subfolders when switching to Etsy tab
                refreshSubfolders();
            });

            // Check for authentication status
            checkLogForAuthStatus();

            // Initial refresh of subfolders
            refreshSubfolders();
        });

        // Function to show a tab
        function showTab(tabId) {
            console.log('Showing tab:', tabId);

            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });

            // Show selected tab content
            document.getElementById(tabId).classList.add('active');

            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // Activate the correct tab button
            document.getElementById(tabId + '-tab').classList.add('active');
        }

        // Log message
        function log(message) {
            const logArea = document.getElementById('log');
            logArea.innerHTML += message + '<br>';
            logArea.scrollTop = logArea.scrollHeight;
        }

        // Clear log
        function clearLog() {
            document.getElementById('log').innerHTML = '';
        }

        // Check for new log messages
        function checkLog() {
            fetch('/log')
                .then(response => response.json())
                .then(data => {
                    if (data.messages && data.messages.length > 0) {
                        data.messages.forEach(message => {
                            log(message);
                        });
                    }

                    // Check again in 1 second
                    setTimeout(checkLog, 1000);
                })
                .catch(error => {
                    console.error('Error checking log:', error);
                    // Try again in 5 seconds
                    setTimeout(checkLog, 5000);
                });
        }

        // Start checking for log messages
        checkLog();

        // Check for authentication status in log messages
        function checkLogForAuthStatus() {
            const logArea = document.getElementById('log');
            const logText = logArea.innerHTML;
            const authStatusDiv = document.getElementById('auth-status');
            const authButton = document.getElementById('auth-button');

            // Check if log contains authentication success messages
            if (logText.includes('Already authenticated with Etsy') ||
                logText.includes('Authentication successful')) {
                // Show success message and disable button
                authStatusDiv.innerHTML = '✓ Already authenticated with Etsy';
                authButton.disabled = true;
            } else {
                // Clear success message and enable button
                authStatusDiv.innerHTML = '';
                authButton.disabled = false;
            }
        }

        // Set up a MutationObserver to watch for changes to the log
        const logArea = document.getElementById('log');
        const observer = new MutationObserver(function(mutations) {
            checkLogForAuthStatus();
        });
        observer.observe(logArea, { childList: true });

        // Pattern actions
        function runPatternWorkflow() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'pattern-workflow',
                    inputDir: document.getElementById('pattern-input-dir').value,
                    createVideo: true
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        function runPatternResize() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'pattern-resize',
                    inputDir: document.getElementById('pattern-input-dir').value
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        function runPatternMockups() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'pattern-mockups',
                    inputDir: document.getElementById('pattern-input-dir').value
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        // Clipart actions
        function runClipartWorkflow() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'clipart-workflow',
                    inputDir: document.getElementById('clipart-input-dir').value,
                    createVideo: true
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        function runClipartResize() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'clipart-resize',
                    inputDir: document.getElementById('clipart-input-dir').value
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        function runClipartMockups() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'clipart-mockups',
                    inputDir: document.getElementById('clipart-input-dir').value
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }

        // Etsy actions
        function authenticateEtsy() {
            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'etsy-auth'
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
                // Check auth status after a delay to allow the command to complete
                setTimeout(checkLogForAuthStatus, 3000);
            });
        }

        // Function to refresh the list of subfolders in the input directory
        function refreshSubfolders() {
            fetch('/get-subfolders')
                .then(response => response.json())
                .then(data => {
                    const select = document.getElementById('etsy-subfolder');

                    // Save the current selection if any
                    const currentSelection = select.value;

                    // Clear all options except the first one
                    while (select.options.length > 1) {
                        select.remove(1);
                    }

                    // Add new options
                    data.subfolders.forEach(subfolder => {
                        const option = document.createElement('option');
                        option.value = subfolder;
                        option.text = subfolder;
                        select.add(option);
                    });

                    // Restore selection if it still exists
                    if (data.subfolders.includes(currentSelection)) {
                        select.value = currentSelection;
                    }

                    log('Refreshed subfolders list: ' + data.subfolders.length + ' folders found');
                })
                .catch(error => {
                    console.error('Error refreshing subfolders:', error);
                    log('Error refreshing subfolders: ' + error);
                });
        }

        function createEtsyListing() {
            const subfolder = document.getElementById('etsy-subfolder').value;
            const productType = document.getElementById('etsy-product-type').value;
            const draft = document.getElementById('etsy-draft').checked;

            if (!subfolder) {
                alert('Please select a subfolder from the input directory.');
                return;
            }

            // Construct the full folder path
            const folder = 'input/' + subfolder;

            fetch('/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command: 'etsy-create',
                    folder: folder,
                    productType: productType,
                    draft: draft
                }),
            })
            .then(response => response.json())
            .then(data => {
                log('Command submitted: ' + data.command);
            });
        }
    </script>
</body>
</html>
    """
    )

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
