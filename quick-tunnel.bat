@echo off
REM Quick Cloudflare Tunnel Script for Windows
REM This creates a temporary tunnel without requiring a domain

echo ===================================
echo SpaceIQ Bot - Quick Tunnel Setup
echo ===================================
echo.
echo This will create a temporary Cloudflare tunnel URL.
echo No domain or account setup required!
echo.
echo Make sure:
echo  1. cloudflared is installed (winget install Cloudflare.cloudflared)
echo  2. Your Flask app is running on http://localhost:5000
echo  3. FLASK_ENV=production and FLASK_DEBUG=0 are set in .env
echo.
pause
echo.
echo Starting tunnel...
echo.

cloudflared tunnel --url http://localhost:5000

echo.
echo Tunnel closed.
pause
