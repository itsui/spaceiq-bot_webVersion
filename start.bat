@echo off
echo Starting SpaceIQ Multi-User Platform...
echo.

REM Check if flask_login is installed
python -c "import flask_login" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements_multiuser.txt
)

REM Check if database exists and has tables
python -c "import sqlite3; conn = sqlite3.connect('spaceiq_multiuser.db'); cursor = conn.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); tables = cursor.fetchall(); conn.close(); exit(0 if len(tables) > 0 else 1)" 2>nul
if errorlevel 1 (
    echo Initializing database...
    python init_database.py
)

echo.
python app.py
pause
