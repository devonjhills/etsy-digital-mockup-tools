@echo off
REM Quick launcher script for Windows - automatically activates venv and runs the app

REM Navigate to script directory
cd /d "%~dp0"

REM Activate virtual environment
if not exist "venv" (
    echo Setting up virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Run the application
echo Starting Mockup Tools...
python main.py %*