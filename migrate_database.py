#!/usr/bin/env python
"""
Database Migration Manager for SpaceIQ Multi-User Platform
Safely migrates databases while preserving all user data
"""

import sqlite3
import json
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration_manager')

class DatabaseMigrationManager:
    """Handles database migrations safely with backups"""

    def __init__(self, db_path: str = "instance/spaceiq_multiuser.db"):
        self.db_path = Path(db_path)
        self.migrations_table = "schema_migrations"

    def ensure_database_exists(self):
        """Ensure database directory and file exist"""
        # Ensure instance directory exists
        self.db_path.parent.mkdir(exist_ok=True)

        # Create database if it doesn't exist
        if not self.db_path.exists():
            logger.info(f"Creating new database at {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            conn.close()

    def create_migrations_table(self):
        """Create table to track applied migrations"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def backup_database(self) -> Path:
        """Create a backup of the current database"""
        if not self.db_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}{self.db_path.suffix}"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"[SUCCESS] Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"[ERROR] Failed to backup database: {e}")
            raise

    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT migration_name FROM {self.migrations_table} ORDER BY applied_at")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Migrations table doesn't exist
            return []
        finally:
            conn.close()

    def mark_migration_applied(self, migration_name: str, checksum: str = None):
        """Mark a migration as applied"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {self.migrations_table} (migration_name, checksum)
                VALUES (?, ?)
            """, (migration_name, checksum))
            conn.commit()
            logger.info(f"[SUCCESS] Migration {migration_name} marked as applied")
        finally:
            conn.close()

    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        if not self.db_path.exists():
            return False

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_table_columns(self, table_name: str) -> List[str]:
        """Get list of columns for a table"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        finally:
            conn.close()

    def run_migration(self, migration_name: str, migration_func):
        """Run a single migration safely"""
        logger.info(f"🔄 Running migration: {migration_name}")

        # Check if already applied
        if migration_name in self.get_applied_migrations():
            logger.info(f"⏭️  Migration {migration_name} already applied, skipping")
            return True

        # Create backup
        backup_path = self.backup_database()

        try:
            # Run migration
            migration_func()

            # Mark as applied
            self.mark_migration_applied(migration_name)

            logger.info(f"✅ Migration {migration_name} completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Migration {migration_name} failed: {e}")

            # Restore from backup if it exists
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, self.db_path)
                    logger.info(f"🔄 Database restored from backup due to migration failure")
                except Exception as restore_error:
                    logger.error(f"❌ Failed to restore backup: {restore_error}")

            return False

# Define all migrations
def migration_001_create_basic_tables(conn: sqlite3.Connection):
    """Create basic tables for fresh installation"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE,
            password_hash VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spaceiq_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_data TEXT,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            building VARCHAR(10),
            floor VARCHAR(10),
            desk_preferences TEXT,
            dates_to_try TEXT,
            booking_days TEXT,
            wait_times TEXT,
            browser_restart TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_instances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            status VARCHAR(20),
            started_at DATETIME,
            stopped_at DATETIME,
            current_round INTEGER,
            successful_bookings INTEGER DEFAULT 0,
            failed_attempts INTEGER DEFAULT 0,
            pid INTEGER,
            error_message TEXT,
            recent_logs TEXT,
            current_activity VARCHAR(200),
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS booking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE,
            desk_number VARCHAR(20),
            time TIME,
            status VARCHAR(20),
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vnc_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vnc_port INTEGER,
            password VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)

    conn.commit()

def migration_002_add_blacklist_dates(conn: sqlite3.Connection):
    """Add blacklist_dates column to bot_configs"""
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(bot_configs)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'blacklist_dates' not in columns:
        cursor.execute("""
            ALTER TABLE bot_configs
            ADD COLUMN blacklist_dates TEXT NOT NULL DEFAULT '[]'
        """)
        conn.commit()
        logger.info("✅ Added blacklist_dates column to bot_configs")
    else:
        logger.info("ℹ️ blacklist_dates column already exists")

def migration_003_add_indexes(conn: sqlite3.Connection):
    """Add performance indexes"""
    cursor = conn.cursor()

    # User indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")

    # Bot instance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_instances_user ON bot_instances(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_instances_status ON bot_instances(status)")

    # Booking history indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_booking_history_user ON booking_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_booking_history_date ON booking_history(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_booking_history_status ON booking_history(status)")

    # Session indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spaceiq_sessions_user ON spaceiq_sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spaceiq_sessions_expires ON spaceiq_sessions(expires_at)")

    conn.commit()
    logger.info("✅ Added performance indexes")

# Migration registry
MIGRATIONS = [
    ("001_create_basic_tables", migration_001_create_basic_tables),
    ("002_add_blacklist_dates", migration_002_add_blacklist_dates),
    ("003_add_indexes", migration_003_add_indexes),
]

def run_all_migrations(db_path: str = "instance/spaceiq_multiuser.db") -> bool:
    """Run all pending migrations"""
    manager = DatabaseMigrationManager(db_path)

    try:
        # Ensure database exists
        manager.ensure_database_exists()

        # Create migrations table
        manager.create_migrations_table()

        # Get applied migrations
        applied = manager.get_applied_migrations()
        logger.info(f"📋 Already applied migrations: {applied}")

        # Run pending migrations
        success_count = 0
        total_count = 0

        for migration_name, migration_func in MIGRATIONS:
            total_count += 1
            if migration_name not in applied:
                if manager.run_migration(migration_name, lambda: migration_func(sqlite3.connect(manager.db_path))):
                    success_count += 1
                else:
                    logger.error(f"❌ Migration {migration_name} failed - stopping")
                    return False
            else:
                success_count += 1  # Already applied counts as success

        logger.info(f"🎉 Migration complete! {success_count}/{total_count} migrations successful")
        return True

    except Exception as e:
        logger.error(f"❌ Migration process failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("SpaceIQ Multi-User Platform - Database Migration Manager")
    print("=" * 80)
    print()

    success = run_all_migrations()

    print()
    print("=" * 80)
    if success:
        print("[SUCCESS] All migrations completed successfully!")
        print()
        print("Next steps:")
        print("   1. Restart the Flask app (python app.py)")
        print("   2. Your user data and configurations are preserved")
        print("   3. New features are now available")
    else:
        print("[ERROR] Migration failed!")
        print("   Check the logs above for details")
        print("   Your original database has been restored from backup")
    print("=" * 80)