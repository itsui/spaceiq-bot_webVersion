@echo off
REM ================================================
REM SpaceIQ Bot - Local Mode (No Cloudflare Needed)
REM ================================================
REM This script runs the bot locally on your computer
REM Access it at: http://localhost:5050
REM ================================================

echo.
echo ================================================
echo    SpaceIQ Bot - LOCAL MODE
echo ================================================
echo.

cd /d "%~dp0"

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Set environment for local development (HTTP works)
set FLASK_ENV=development
set FLASK_DEBUG=0
set LOCAL_MODE=true

echo Starting SpaceIQ Bot...
echo.
echo ================================================
echo   Access the bot at: http://localhost:5050
echo ================================================
echo.
echo Keep this window open while using the bot.
echo Press Ctrl+C to stop the server.
echo.

REM Use Flask's built-in server for local use (simpler than waitress)
py -c "from app import app, db; app.app_context().push(); db.create_all(); app.run(host='127.0.0.1', port=5050, debug=False, threaded=True)"

echo.
echo ================================================
echo   Server has stopped.
echo ================================================
pause
