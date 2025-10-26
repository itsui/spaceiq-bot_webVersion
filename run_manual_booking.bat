@echo off
REM SpaceIQ Manual Booking - Batch File
REM Books dates specified in config/booking_config.json

REM Change to script directory
cd /d "%~dp0"

echo.
echo ======================================================================
echo          SpaceIQ Manual Booking Mode
echo ======================================================================
echo.
echo This will book dates from: config\booking_config.json
echo.
echo Make sure you've edited the config file with your desired dates!
echo.
echo ======================================================================
echo.

python multi_date_book.py

echo.
echo ======================================================================
echo Press any key to close...
pause >nul
