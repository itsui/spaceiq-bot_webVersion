@echo off
REM Run SpaceIQ Booking in Headless Mode (Background)
REM No browser window will appear - perfect for running while working
REM Fully automatic - no prompts

echo ========================================
echo  SpaceIQ Headless Booking (Auto)
echo ========================================
echo.
echo Running in HEADLESS mode (no browser window)
echo This will book desks in the background.
echo Fully automatic - no confirmation needed.
echo.
echo NOTE: Make sure your session is valid!
echo If session expired, run: auto_warm_session.py first
echo.

python multi_date_book.py --auto --headless --unattended

echo.
echo Booking complete!
pause
