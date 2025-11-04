#!/usr/bin/env python3
"""
Production startup script for SpaceIQ Multi-User Bot Platform
"""

import os
from app import app

# Production configuration
if __name__ == '__main__':
    # Disable debug mode for production
    app.debug = False

    # Use production WSGI server instead of Flask development server
    print("Starting SpaceIQ Bot Platform in production mode...")
    print("WARNING: Use a production WSGI server (Gunicorn/Waitress) for deployment!")
    print()
    print("Recommended commands:")
    print("  Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 app:app")
    print("  Waitress: waitress-serve --host=0.0.0.0 --port=5000 app:app")
    print()

    # Only for testing - NOT for production
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True  # Enable basic threading for testing
    )