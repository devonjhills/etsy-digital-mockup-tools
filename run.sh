#!/bin/bash
# Quick launcher script - automatically activates venv and runs the app

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the application
echo "Starting Mockup Tools..."
python main.py "$@"