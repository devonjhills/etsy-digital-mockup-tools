#!/bin/bash
# Automatic virtual environment activation script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing requirements..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "Virtual environment activated!"
echo "Python path: $(which python)"
echo "Available commands:"
echo "  python main.py              # Start GUI"
echo "  python main.py list-types   # List product types"
echo "  python main.py --help       # Show all options"
echo ""
echo "To deactivate later, run: deactivate"