@echo off
REM Run SpaceIQ Booking in Headless Mode (Background)
REM No browser window will appear - perfect for running while working

echo ========================================
echo  SpaceIQ Headless Booking
echo ========================================
echo.
echo Running in HEADLESS mode (no browser window)
echo This will book desks in the background.
echo.
echo NOTE: Make sure your session is valid!
echo If session expired, run: auto_warm_session.py first
echo.

python multi_date_book.py --auto --headless

echo.
echo Booking complete!
pause
