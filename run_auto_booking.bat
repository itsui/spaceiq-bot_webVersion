@echo off
REM SpaceIQ Auto Booking - Batch File
REM Automatically generates and books Wed/Thu dates for next 4 weeks+1
REM Use this for scheduled/unattended runs (no prompts)
REM POLLING MODE: Keeps trying until seats found (people cancel!)

REM Change to script directory
cd /d "%~dp0"

echo.
echo ======================================================================
echo          SpaceIQ Auto Booking Mode (Polling + Unattended)
echo ======================================================================
echo.
echo This will automatically:
echo   - Generate all Wed/Thu dates for next 29 days
echo   - Try to book from furthest to closest
echo   - KEEP TRYING until at least one seat is booked
echo   - People cancel bookings - bot will catch them!
echo   - Move successful bookings to booked_dates
echo   - Run without prompts (for scheduled tasks)
echo.
echo Press Ctrl+C to stop
echo.
echo ======================================================================
echo.

python multi_date_book.py --auto --unattended --poll

echo.
echo ======================================================================
echo Booking completed. Press any key to close...
pause >nul
