@echo off
REM Build Desk Position Cache
REM This tool maps all desk positions for 10x faster booking

echo.
echo ========================================
echo   Build Desk Position Cache
echo ========================================
echo.
echo This will:
echo - Open browser (visible)
echo - Find a weekend date with many available desks
echo - Click all blue circles to map positions
echo - Save to config/desk_positions.json
echo.
echo This takes ~2 minutes (one-time setup)
echo After this, booking will be 10x faster!
echo.
echo ========================================
echo.

python map_desk_positions.py

echo.
echo ========================================
echo.
echo Done! Position cache is ready.
echo Now run: run_headless_booking.bat
echo.
echo ========================================
echo.
pause
