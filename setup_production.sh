#!/bin/bash
# Production Setup Script for Linux/Mac
# This script prepares your environment for remote testing

echo "==============================================="
echo "SpaceIQ Bot - Production Setup (Unix)"
echo "==============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.13 or higher"
    exit 1
fi

echo "[1/6] Checking Python version..."
python3 --version

echo ""
echo "[2/6] Installing/upgrading dependencies..."
python3 -m pip install --upgrade pip
pip3 install -r requirements_production.txt

echo ""
echo "[3/6] Checking environment configuration..."
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found!"
    echo "Copying from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and set:"
    echo "   - SECRET_KEY (generate with: python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "   - FLASK_ENV=production"
    echo "   - FLASK_DEBUG=0"
    echo "   - SUPABASE_URL and SUPABASE_ANON_KEY"
    echo ""
    read -p "Press Enter to continue..."
fi

echo ""
echo "[4/6] Generating secure SECRET_KEY..."
python3 -c "import secrets; print('Suggested SECRET_KEY:\n' + secrets.token_hex(32))"
echo ""
echo "Copy this key to your .env file!"
echo ""

echo "[5/6] Checking database..."
if [ ! -f spaceiq_multiuser.db ]; then
    echo "Database not found, will be created on first run"
else
    echo "Database found: spaceiq_multiuser.db"
fi

echo ""
echo "[6/6] Checking Cloudflare CLI..."
if ! command -v cloudflared &> /dev/null; then
    echo "[WARNING] cloudflared is not installed"
    echo "Install with:"
    echo "  - Mac: brew install cloudflared"
    echo "  - Linux: See https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/"
else
    cloudflared --version
fi

echo ""
echo "==============================================="
echo "Setup Complete!"
echo "==============================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with production settings"
echo "  2. Generate and set SECRET_KEY in .env"
echo "  3. Install cloudflared if not already installed"
echo "  4. Run: python3 app.py (to start the Flask app)"
echo "  5. Run: ./quick-tunnel.sh (to create public URL)"
echo ""
