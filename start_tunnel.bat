@echo off
REM Start Cloudflare Tunnel for SpaceIQ Bot
REM This connects your local server to your domain

echo ================================================
echo Starting Cloudflare Tunnel for SpaceIQ Bot
echo ================================================
echo.
echo Domain: felipevargas.xyz
echo Tunnel: spaceiq-bot
echo.
echo Make sure your Flask app is running first!
echo (Run start_app_production.bat in another window)
echo.
echo Press Ctrl+C to stop the tunnel
echo ================================================
echo.

cloudflared tunnel --config cloudflare-tunnel.yml run spaceiq-bot

echo.
echo Tunnel stopped.
pause
