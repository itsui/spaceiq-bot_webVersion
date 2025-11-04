#!/usr/bin/env python
"""
Initialize the database for SpaceIQ Multi-User Platform
Run this if you get database errors
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import app, db
from models import User, SpaceIQSession, BotConfig, BotInstance, BookingHistory, VNCSession

def init_database():
    """Initialize all database tables"""
    print("=" * 60)
    print("SpaceIQ Multi-User Platform - Database Initialization")
    print("=" * 60)
    print()

    with app.app_context():
        try:
            # Create tables (doesn't drop existing ones)
            print("Creating missing tables...")
            db.create_all()
            print("[OK] Tables ready")
            print()

            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print("Database tables:")
            for table in tables:
                print(f"  [OK] {table}")
            print()

            print("=" * 60)
            print("Database initialization complete!")
            print("=" * 60)
            print()
            print("You can now start the application:")
            print("  python app.py")
            print()

            return True

        except Exception as e:
            print(f"ERROR: Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
