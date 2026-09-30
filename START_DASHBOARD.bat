@echo off
title Outreach Engine - Control Center
echo ============================================================
echo         Starting Outreach Engine Dashboard...
echo ============================================================
echo.

:: Use the directory where this .bat file lives (works for any user, any path)
cd /d "%~dp0"

:: Check .env exists
if not exist ".env" (
    echo [!] No .env file found. Running setup first...
    call SETUP.bat
)

:: Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found. Running setup first...
    call SETUP.bat
)

:: Kill any process already using port 8000 so there are no conflicts
echo [*] Freeing port 8000 if in use...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 2^>nul') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo [*] Activating Python environment...
call .\venv\Scripts\activate.bat

echo [*] Opening Dashboard at http://127.0.0.1:8000 in 3 seconds...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000

echo [*] Starting server... (Press Ctrl+C here to stop it)
echo.
python server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] The server stopped with an error. See the message above.
    echo     Most likely cause: .env file is missing GEMINI_API_KEY.
    pause
)
