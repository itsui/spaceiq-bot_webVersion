#!/bin/bash
# Start SpaceIQ Bot in Production Mode (Unix)

echo "================================================"
echo "Starting SpaceIQ Bot in Production Mode"
echo "================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[ERROR] .env file not found!"
    echo "Please run ./setup_production.sh first"
    exit 1
fi

# Set production environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

echo "Environment: production"
echo "Debug: disabled"
echo ""
echo "Starting Flask app on http://0.0.0.0:5000"
echo ""
echo "Keep this terminal open while the bot is running"
echo "Press Ctrl+C to stop the server"
echo ""
echo "================================================"
echo ""

python3 app.py
