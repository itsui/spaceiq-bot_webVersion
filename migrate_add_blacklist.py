"""
Database Migration: Add blacklist_dates column to bot_configs table

Run this script once to add the new blacklist_dates feature to existing databases.
"""

import sqlite3
from pathlib import Path

def migrate():
    """Add blacklist_dates column to bot_configs table"""

    # Try multiple locations (prioritize instance folder - that's where Flask usually puts it)
    possible_paths = [
        Path('instance/spaceiq_multiuser.db'),
        Path('spaceiq_multiuser.db'),
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print(f"❌ Database not found in:")
        for path in possible_paths:
            print(f"   - {path}")
        print("   No migration needed (fresh install will have the column)")
        return

    print(f"📁 Found database: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(bot_configs)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'blacklist_dates' in columns:
            print("✅ Migration already applied - blacklist_dates column exists")
            conn.close()
            return

        print("📝 Adding blacklist_dates column to bot_configs table...")

        # Add the column with default value
        cursor.execute("""
            ALTER TABLE bot_configs
            ADD COLUMN blacklist_dates TEXT NOT NULL DEFAULT '[]'
        """)

        conn.commit()

        # Verify
        cursor.execute("PRAGMA table_info(bot_configs)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'blacklist_dates' in columns:
            print("✅ Migration successful!")
            print(f"   Added blacklist_dates column to bot_configs table")
            print(f"   All existing users now have empty blacklist: []")
        else:
            print("❌ Migration verification failed")

        conn.close()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    return True

if __name__ == "__main__":
    print("=" * 70)
    print("Database Migration: Add Blacklist Dates Feature")
    print("=" * 70)
    print()

    success = migrate()

    print()
    print("=" * 70)
    if success:
        print("✅ Migration complete! You can now:")
        print("   1. Restart the Flask app (stop and restart start.bat)")
        print("   2. Go to Configuration page")
        print("   3. Add blacklist dates for holidays/vacations")
        print("   4. Dates will auto-calculate excluding blacklisted dates")
    else:
        print("⚠️  Migration not needed or failed")
        print("   If this is a fresh install, the column already exists")
    print("=" * 70)
