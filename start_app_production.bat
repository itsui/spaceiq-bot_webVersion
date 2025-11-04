@echo off
REM Start SpaceIQ Bot in Production Mode (Windows)

echo ================================================
echo Starting SpaceIQ Bot in Production Mode
echo ================================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please run setup_production.bat first
    pause
    exit /b 1
)

REM Set production environment variables
set FLASK_ENV=production
set FLASK_DEBUG=0

echo Environment: production
echo Debug: disabled
echo.
echo Starting Flask app on http://0.0.0.0:5000
echo.
echo Keep this window open while the bot is running
echo Press Ctrl+C to stop the server
echo.
echo ================================================
echo.

python app.py
