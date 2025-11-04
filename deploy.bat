@echo off
REM Production deployment script for SpaceIQ Bot Platform (Windows)

echo 🚀 Deploying SpaceIQ Multi-User Bot Platform to Production...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install production dependencies
echo Installing production dependencies...
pip install -r requirements_web.txt
pip install waitress

REM Create logs directory
if not exist "logs" mkdir logs

REM Set production environment variables
set FLASK_ENV=production
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set SECRET_KEY=%%i

echo 🔧 Starting production server with Waitress...
echo Server will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Start with Waitress (Windows-friendly production server)
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app