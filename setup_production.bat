@echo off
REM Production Setup Script for Windows
REM This script prepares your environment for remote testing

echo ===============================================
echo SpaceIQ Bot - Production Setup (Windows)
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.13 or higher
    pause
    exit /b 1
)

echo [1/6] Checking Python version...
python --version

echo.
echo [2/6] Installing/upgrading dependencies...
python -m pip install --upgrade pip
pip install -r requirements_production.txt

echo.
echo [3/6] Checking environment configuration...
if not exist .env (
    echo [WARNING] .env file not found!
    echo Copying from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Edit .env file and set:
    echo    - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
    echo    - FLASK_ENV=production
    echo    - FLASK_DEBUG=0
    echo    - SUPABASE_URL and SUPABASE_ANON_KEY
    echo.
    pause
)

echo.
echo [4/6] Generating secure SECRET_KEY...
python -c "import secrets; print('Suggested SECRET_KEY:\n' + secrets.token_hex(32))"
echo.
echo Copy this key to your .env file!
echo.

echo [5/6] Checking database...
if not exist spaceiq_multiuser.db (
    echo Database not found, will be created on first run
) else (
    echo Database found: spaceiq_multiuser.db
)

echo.
echo [6/6] Checking Cloudflare CLI...
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] cloudflared is not installed
    echo Install with: winget install Cloudflare.cloudflared
    echo Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
) else (
    cloudflared --version
)

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Next steps:
echo  1. Edit .env file with production settings
echo  2. Generate and set SECRET_KEY in .env
echo  3. Install cloudflared if not already installed
echo  4. Run: python app.py (to start the Flask app)
echo  5. Run: quick-tunnel.bat (to create public URL)
echo.
pause
