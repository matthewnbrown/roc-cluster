@echo off
echo Installing ROC Cluster Management API on Windows...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Checking version...
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Try minimal requirements first
echo.
echo Installing minimal requirements...
pip install -r requirements-minimal.txt
if errorlevel 1 (
    echo.
    echo Minimal requirements failed. Trying individual packages...
    
    REM Install packages one by one
    pip install fastapi==0.100.1
    pip install uvicorn[standard]==0.22.0
    pip install sqlalchemy==1.4.48
    pip install requests==2.28.2
    pip install beautifulsoup4==4.11.2
    pip install pydantic==1.10.12
    pip install email-validator==1.3.1
    pip install httpx==0.24.1
    pip install python-multipart==0.0.6
    pip install python-dotenv==1.0.0
    
    if errorlevel 1 (
        echo.
        echo Some packages failed to install. You may need to:
        echo 1. Update your Python version
        echo 2. Install Visual Studio Build Tools
        echo 3. Use conda instead of pip
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Installation completed successfully!
echo.
echo To start the API:
echo 1. Activate the virtual environment: .venv\Scripts\activate.bat
echo 2. Run: python start_api.py
echo.
pause
