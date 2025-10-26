@echo off
REM SpaceIQ Session Warmer - Batch File
REM Opens SpaceIQ and checks if you're logged in

REM Change to script directory
cd /d "%~dp0"

echo.
echo ======================================================================
echo          SpaceIQ Session Warmer
echo ======================================================================
echo.
echo This will:
echo   - Open SpaceIQ in the browser
echo   - Check if you're still logged in
echo   - Wait for you to login if session expired
echo   - Keep session fresh for scheduled booking
echo.
echo Recommended: Run this on Tue/Wed evening (8 PM)
echo             Before the midnight booking runs
echo.
echo ======================================================================
echo.

python warm_session.py

echo.
echo ======================================================================
echo Press any key to close...
pause >nul
