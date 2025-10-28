@echo off
REM SpaceIQ Booking Bot - Main Menu

REM Change to script directory
cd /d "%~dp0"

REM Maximize window if not already maximized
if "%1" == "MAXIMIZED" goto MENU
start "SpaceIQ Booking Bot" /MAX cmd /k "%~f0" MAXIMIZED
goto :EOF

:MENU
cls
echo.
echo ======================================================================
echo          SpaceIQ Booking Bot - Main Menu
echo ======================================================================
echo.
echo Please select an option:
echo.
echo   1. Auto Booking (Generate Wed/Thu dates for next 4 weeks)
echo   2. Manual Booking (Use dates from config file)
echo   3. Session Warmer (Check/refresh login)
echo   4. Exit
echo.
echo ======================================================================
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto AUTO
if "%choice%"=="2" goto MANUAL
if "%choice%"=="3" goto WARMER
if "%choice%"=="4" goto EXIT
echo Invalid choice. Please try again.
timeout /t 2 >nul
goto MENU

:AUTO
cls
echo.
echo ======================================================================
echo          Auto Booking Mode
echo ======================================================================
echo.
python multi_date_book.py --auto --unattended
echo.
echo ======================================================================
echo.
pause
goto MENU

:MANUAL
cls
echo.
echo ======================================================================
echo          Manual Booking Mode
echo ======================================================================
echo.
python multi_date_book.py
echo.
echo ======================================================================
echo.
pause
goto MENU

:WARMER
cls
echo.
echo ======================================================================
echo          Session Warmer
echo ======================================================================
echo.
python auto_warm_session.py
echo.
echo ======================================================================
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
timeout /t 1 >nul
exit
