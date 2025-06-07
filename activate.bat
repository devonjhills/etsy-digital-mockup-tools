@echo off
REM Automatic virtual environment activation script for Windows

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    echo Installing requirements...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Virtual environment activated!
echo Python path: %~dp0venv\Scripts\python.exe
echo Available commands:
echo   python main.py              # Start GUI
echo   python main.py list-types   # List product types  
echo   python main.py --help       # Show all options
echo.
echo To deactivate later, run: deactivate