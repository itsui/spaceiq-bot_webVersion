#!/bin/bash
# Production deployment script for SpaceIQ Bot Platform

echo "🚀 Deploying SpaceIQ Multi-User Bot Platform to Production..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install production dependencies
echo "Installing production dependencies..."
pip install -r requirements_web.txt
pip install gunicorn

# Create logs directory
mkdir -p logs

# Set production environment variables
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

echo "🔧 Starting production server with Gunicorn..."
echo "Server will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Start with Gunicorn using production config
gunicorn -c gunicorn_config.py app:app