@echo off
REM Desk Position Mapper - Remap Seat Coordinates
REM This tool builds a cache of desk positions for faster bookings

echo.
echo ========================================================================
echo                    Desk Position Mapper Tool
echo ========================================================================
echo.
echo This will remap all seat coordinates by clicking blue circles on the
echo floor map and saving their positions to config/desk_positions.json
echo.
echo Make sure you have authenticated via the web interface first!
echo.
pause

REM Default to user_id=1 (you can change this if needed)
python map_desk_positions.py --user-id 1

echo.
echo ========================================================================
echo                         Process Complete
echo ========================================================================
echo.
pause
