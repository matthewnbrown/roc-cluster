# PowerShell installation script for ROC Cluster Management API

Write-Host "Installing ROC Cluster Management API on Windows..." -ForegroundColor Green
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Try minimal requirements first
Write-Host ""
Write-Host "Installing minimal requirements..." -ForegroundColor Yellow
pip install -r requirements-minimal.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Minimal requirements failed. Trying individual packages..." -ForegroundColor Yellow
    
    # Install packages one by one
    $packages = @(
        "fastapi==0.100.1",
        "uvicorn[standard]==0.22.0", 
        "sqlalchemy==1.4.48",
        "requests==2.28.2",
        "beautifulsoup4==4.11.2",
        "pydantic==1.10.12",
        "email-validator==1.3.1",
        "httpx==0.24.1",
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0"
    )
    
    foreach ($package in $packages) {
        Write-Host "Installing $package..." -ForegroundColor Cyan
        pip install $package
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Warning: Failed to install $package" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "Some packages may have failed to install. You may need to:" -ForegroundColor Yellow
    Write-Host "1. Update your Python version" -ForegroundColor White
    Write-Host "2. Install Visual Studio Build Tools" -ForegroundColor White
    Write-Host "3. Use conda instead of pip" -ForegroundColor White
}

Write-Host ""
Write-Host "Installation completed!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the API:" -ForegroundColor Cyan
Write-Host "1. Activate the virtual environment: .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "2. Run: python start_api.py" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
