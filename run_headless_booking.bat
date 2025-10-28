@echo off
REM Run SpaceIQ Booking in Headless Mode (Background)
REM
REM Features:
REM   - Runs in background (no browser window)
REM   - Checks existing bookings and skips them
REM   - Continuous loop - keeps trying unbooked dates forever
REM   - Press Ctrl+C to stop
REM
REM This is the main production mode for automated desk booking

REM Maximize the window and run
if "%1" == "MAXIMIZED" goto RUNMAX
start "SpaceIQ Headless Booking" /MAX cmd /k "%~f0" MAXIMIZED
goto :EOF

:RUNMAX
python D:\SD\spaceIqBotv01\multi_date_book.py --auto --headless --unattended
pause
