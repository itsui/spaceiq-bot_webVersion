@echo off
REM Clear SpaceIQ authentication profiles for testing

echo ================================================
echo Clearing SpaceIQ Authentication Profiles
echo ================================================
echo.

set "PROFILES_DIR=playwright\.auth\profiles"

if exist "%PROFILES_DIR%" (
    echo Found profiles directory: %PROFILES_DIR%
    echo.
    echo Removing all user profiles...
    rmdir /s /q "%PROFILES_DIR%"
    echo.
    echo [SUCCESS] All authentication profiles cleared!
    echo.
    echo You can now test the login flow from scratch.
) else (
    echo [INFO] No profiles directory found - nothing to clear.
)

echo.
echo ================================================
pause
