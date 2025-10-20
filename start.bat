@echo off
REM Clinical Genius - Flask Application Startup Script
REM This script starts the Flask web application on port 4000

echo ================================================
echo Clinical Genius - CRM Analytics Prompt Execution
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found. Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully.
    echo.
)

REM Check if Node.js is installed (required for Salesforce authentication)
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js is not installed or not in PATH
    echo Node.js is required for Salesforce JWT authentication
    echo Please install Node.js from https://nodejs.org/
    pause
)

REM Check if jsforce is installed
if not exist "node_modules\jsforce\" (
    echo Installing Node.js dependencies...
    call npm install jsforce
    if errorlevel 1 (
        echo WARNING: Failed to install jsforce
        echo Salesforce authentication may not work
    )
)

echo.
echo Starting Flask application on http://localhost:4000
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

REM Start Flask application
python app.py

REM Deactivate virtual environment on exit
call venv\Scripts\deactivate.bat
