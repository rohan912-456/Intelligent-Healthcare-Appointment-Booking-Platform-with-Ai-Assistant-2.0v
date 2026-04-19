@echo off
color 0b
echo ===========================================
echo Clinical Couture - ONE-CLICK SETUP ^& LAUNCHER
echo ===========================================
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Check for .env file
if not exist ".env" (
    if exist ".env.example" (
        echo [*] .env not found. Creating from .env.example...
        copy .env.example .env >nul
    ) else (
        echo [WARNING] .env.example not found. Please create .env manually.
    )
) else (
    echo [*] Existing .env file found.
)

:: Check for virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo [*] Virtual environment not found. Creating one...
    python -m venv venv
)

echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

echo [*] Checking and installing dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo [*] Starting Clinical Couture...
echo ===========================================
echo   App:    http://127.0.0.1:5000
echo   Admin:  http://127.0.0.1:5000/admin
echo   Doctor: http://127.0.0.1:5000/doctor
echo ===========================================
echo.

:: Set environment to development
set FLASK_ENV=development

:: Run the application
python app.py

pause
