@echo off
TITLE SmartHR AI System - Automated Setup
cd /d "%~dp0"

echo ================================================================
echo           SmartHR AI - Automated Server Setup
echo ================================================================
echo.
echo This script will install all necessary dependencies for SmartHR.
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org before continuing.
    pause
    exit /b
)

:: 2. Create Virtual Environment
echo [1/4] Creating Virtual Environment (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b
)

:: 3. Install Dependencies
echo [2/4] Installing Python Packages (This may take a few minutes)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install git+https://github.com/ageitgey/face_recognition_models
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

:: 4. Initialize Database
echo [3/4] Initializing Database (SQLite)...
if exist "instance\smarthr.db" (
    echo [INFO] Database already exists. Skipping initialization.
) else (
    python init_db.py
)

:: 5. Final Instructions
echo [4/4] Setup Complete!
echo.
echo ================================================================
echo SUCCESS: SmartHR is ready to use.
echo.
echo TO START THE SERVER:
echo Double-click 'Start_SmartHR.bat'
echo ================================================================
echo.
pause
