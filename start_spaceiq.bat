@echo off
REM SpaceIQ Multi-User Bot Platform - Unified Startup
REM This script starts both the Flask app and Cloudflare tunnel

echo ================================================
echo SpaceIQ Bot Platform - Starting Services
echo ================================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please run setup_production.bat first
    pause
    exit /b 1
)

REM Check if cloudflared is installed
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] cloudflared is not installed!
    echo Install with: winget install Cloudflare.cloudflared
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting Flask web app in new window...
start "SpaceIQ - Flask App" cmd /c "start_app_production.bat"

REM Wait a moment for Flask to initialize
timeout /t 3 /nobreak >nul

echo [2/2] Starting Cloudflare tunnel in new window...
start "SpaceIQ - Cloudflare Tunnel" cmd /c "start_tunnel.bat"

echo.
echo ================================================
echo ✓ Both services started!
echo ================================================
echo.
echo Flask App:        Running in separate window
echo Cloudflare Tunnel: Running in separate window
echo.
echo Your bot is now accessible at:
echo https://felipevargas.xyz
echo.
echo To stop: Close both windows or press Ctrl+C in each
echo ================================================
echo.
pause
