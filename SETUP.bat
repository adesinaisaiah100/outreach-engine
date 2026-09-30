@echo off
title Outreach Engine - One-Time Setup
echo ============================================================
echo         Outreach Engine - One-Time Setup
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10+ from https://python.org
    echo IMPORTANT: Check the box "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found.
echo.

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

:: Activate and install dependencies
echo [*] Installing dependencies...
call .\venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: Install Playwright browsers
echo [*] Installing Playwright browser driver (one-time download ~150MB)...
playwright install chromium

echo.

:: First-time .env setup
if not exist ".env" (
    echo [*] Creating your personal .env config file...
    copy ".env.example" ".env" >nul
    echo.
    echo ============================================================
    echo  ACTION REQUIRED: Open the .env file and fill in YOUR info:
    echo.
    echo    GEMINI_API_KEY   - Get free at: aistudio.google.com
    echo    SENDER_NAME      - Your first name (e.g. Chidi)
    echo    PRODUCT_NAME     - What you are promoting (e.g. MyApp)
    echo    PRODUCT_INTRO    - One sentence about your product
    echo.
    echo  The .env file is in this folder. Open it with Notepad.
    echo ============================================================
    echo.
    start notepad ".env"
) else (
    echo [OK] .env config file already exists.
)

echo.
echo ============================================================
echo  [SUCCESS] Setup complete!
echo  Next step: Double-click START_DASHBOARD.bat to launch.
echo ============================================================
echo.
pause
