"""
Live Logger for UI Dashboard
Saves only the logs that are displayed in the Live Logs section

Features:
- Message cleanup and deduplication
- Automatic log rotation by count and size
- Secure file operations with path validation
- Robust error handling with fallback mechanisms
"""

import logging
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

class LiveLogger:
    """Logger specifically for UI Live Logs display"""

    # Configuration constants
    MAX_LOG_ENTRIES = 500  # Maximum number of log entries before rotation
    MAX_FILE_SIZE_MB = 5   # Maximum log file size in MB before rotation
    MAX_MESSAGE_LENGTH = 1000  # Maximum message length to prevent abuse
    MAX_RETRIES = 3  # Number of retries for file operations
    BACKUP_LOGS_TO_KEEP = 3  # Number of backup log files to keep

    def __init__(self, user_id: int):
        # Validate user_id
        if not isinstance(user_id, int) or user_id < 1:
            raise ValueError(f"Invalid user_id: {user_id}. Must be a positive integer.")

        self.user_id = user_id
        self.log_dir = Path("logs")

        # Create logs directory securely
        try:
            self.log_dir.mkdir(exist_ok=True, mode=0o755)
        except Exception as e:
            # Fallback to current directory if logs directory cannot be created
            print(f"Warning: Could not create logs directory, using current directory: {e}")
            self.log_dir = Path(".")

        # Validate and create user-specific live log file path
        # Prevent path traversal attacks
        safe_user_id = str(user_id).replace('..', '').replace('/', '').replace('\\', '')
        self.log_file = self.log_dir / f"live_logs_{safe_user_id}.json"
        self.text_log_file = self.log_dir / f"live_logs_{safe_user_id}.txt"

        # Initialize log file if it doesn't exist
        if not self.log_file.exists():
            self._initialize_log_file()

    def _initialize_log_file(self):
        """Initialize the live log file with empty structure"""
        initial_data = {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "logs": []
        }

        self._write_json_with_retry(self.log_file, initial_data)

    def _write_json_with_retry(self, file_path: Path, data: dict, retries: int = None):
        """Write JSON data with retry logic and atomic writes"""
        if retries is None:
            retries = self.MAX_RETRIES

        temp_file = file_path.with_suffix('.tmp')

        for attempt in range(retries):
            try:
                # Write to temporary file first (atomic write pattern)
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Atomically rename temp file to target file
                temp_file.replace(file_path)
                return
            except Exception as e:
                if attempt == retries - 1:
                    print(f"Failed to write {file_path} after {retries} attempts: {e}")
                    # Try to clean up temp file
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except:
                        pass
                    raise
                # Wait a bit before retrying (exponential backoff)
                import time
                time.sleep(0.1 * (2 ** attempt))

    def _load_logs(self) -> list:
        """Load existing logs from file with error handling"""
        for attempt in range(self.MAX_RETRIES):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logs = data.get('logs', [])

                    # Validate log structure
                    if not isinstance(logs, list):
                        print(f"Warning: Invalid log structure, resetting logs")
                        return []

                    return logs
            except FileNotFoundError:
                # File doesn't exist yet, return empty list
                return []
            except json.JSONDecodeError as e:
                print(f"Warning: Corrupted log file (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    # Try to backup corrupted file
                    self._backup_corrupted_file()
                    return []
            except Exception as e:
                print(f"Error loading logs (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    return []

        return []

    def _backup_corrupted_file(self):
        """Backup corrupted log file for debugging"""
        try:
            if self.log_file.exists():
                backup_name = f"{self.log_file.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = self.log_file.parent / backup_name
                shutil.copy2(self.log_file, backup_path)
                print(f"Backed up corrupted log file to: {backup_path}")
        except Exception as e:
            print(f"Failed to backup corrupted file: {e}")

    def _save_logs(self, logs: list):
        """Save logs to file with rotation and error handling"""
        try:
            # Check if log rotation is needed
            self._rotate_logs_if_needed()

            # Prepare data
            data = {
                "user_id": self.user_id,
                "updated_at": datetime.now().isoformat(),
                "logs": logs
            }

            # Write with retry logic
            self._write_json_with_retry(self.log_file, data)

        except Exception as e:
            print(f"Failed to save live logs for user {self.user_id}: {e}")
            # Don't raise exception - logging should not crash the application

    def _rotate_logs_if_needed(self):
        """Rotate logs if file size exceeds threshold"""
        try:
            if not self.log_file.exists():
                return

            file_size_mb = self.log_file.stat().st_size / (1024 * 1024)

            if file_size_mb > self.MAX_FILE_SIZE_MB:
                # Create backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"{self.log_file.stem}_backup_{timestamp}.json"
                backup_path = self.log_file.parent / backup_name

                # Copy current log to backup
                shutil.copy2(self.log_file, backup_path)
                print(f"Rotated log file to: {backup_path}")

                # Clean up old backups
                self._cleanup_old_backups()

                # Initialize new log file
                self._initialize_log_file()

        except Exception as e:
            print(f"Error during log rotation: {e}")

    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the most recent ones"""
        try:
            pattern = f"live_logs_{self.user_id}_backup_*.json"
            backups = sorted(self.log_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            # Remove backups beyond the limit
            for old_backup in backups[self.BACKUP_LOGS_TO_KEEP:]:
                try:
                    old_backup.unlink()
                    print(f"Removed old backup: {old_backup.name}")
                except Exception as e:
                    print(f"Failed to remove old backup {old_backup}: {e}")

        except Exception as e:
            print(f"Error cleaning up old backups: {e}")

    def add_log(self, message: str, level: str = "info", **metadata):
        """
        Add a log entry with input validation and sanitization

        Args:
            message: Log message
            level: Log level (info, success, warning, error)
            **metadata: Additional metadata (round, desk, date, etc.)
        """
        try:
            # Validate and sanitize inputs
            message = self._sanitize_message(message)
            level = self._validate_level(level)

            # Validate metadata
            metadata = self._sanitize_metadata(metadata)

            # Filter out huge timeout errors immediately
            if 'timeout' in message.lower() and 'locator.click' in message.lower():
                return  # Skip these huge useless error messages entirely

            # Check if this is an important booking status message that the dashboard needs
            # If so, preserve it exactly as-is
            message_lower = message.lower()
            is_booking_status_message = any(keyword in message_lower for keyword in [
                'successfully booked', 'booking verified', 'no available desks', 'already booked',
                'success: booked', 'booking failed', 'booking verification failed',
                'existing booking found', 'already booked'
            ])

            # Also check if this is an important operational message the user needs to see
            is_operational_message = any(keyword in message_lower for keyword in [
                'starting round', 'checking existing bookings', 'navigating to spaceiq',
                'attempting booking for', 'loading floor map', 'checking available',
                'found', 'available desks', 'no available desks', 'booking verified',
                'successfully booked', 'existing booking found'
            ])

            # Filter out huge timeout errors immediately
            if 'timeout' in message_lower and ('locator.click' in message_lower or 'exceeded' in message_lower):
                return  # Skip these huge useless error messages entirely

            # Only filter the initial startup sequence, not ongoing operations
            startup_keywords = [
                'bot starting', 'starting bot for building', 'starting bot - building',
                'running booking workflow - starting automated booking process', 'starting multi-date booking',
                'using user-specific screenshots', 'cleaned up old screenshots', 'ready to book'
            ]
            if any(keyword in message_lower for keyword in startup_keywords):
                return  # Skip only true startup messages

            # Process booking status messages and operational messages
            if is_booking_status_message:
                # Keep booking status messages as-is for dashboard
                pass
            elif is_operational_message:
                # Keep operational messages but clean them up slightly
                pass
            else:
                # For other messages, clean up long error messages
                if level == 'error' and len(message) > 150:
                    # Truncate long error messages
                    if 'Traceback' in message:
                        message = message.split('Traceback')[0].strip()
                    message = message[:120] + "..." if len(message) > 120 else message

                # Remove redundant information
                message = self._clean_message(message)

                # Skip message if it was filtered out as useless
                if message is None:
                    return

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "level": level,
                "metadata": metadata
            }

            # Load existing logs
            logs = self._load_logs()

            # Check if this is a duplicate or near-duplicate of recent logs
            if logs:
                # Check last 3 logs for duplicates (to catch slightly different timing)
                for recent_log in logs[-3:]:
                    if (recent_log['message'] == message and
                        recent_log['level'] == level):
                        # Check if metadata is essentially the same (ignore timestamp differences)
                        recent_metadata = recent_log.get('metadata', {})
                        if self._metadata_equivalent(recent_metadata, metadata):
                            # Skip duplicate
                            return

            # Add new log
            logs.append(log_entry)

            # Keep only last MAX_LOG_ENTRIES to prevent file from growing too large
            if len(logs) > self.MAX_LOG_ENTRIES:
                logs = logs[-self.MAX_LOG_ENTRIES:]

            # Save back to file
            self._save_logs(logs)

            # Also save to a readable text file for debugging
            self._save_text_log(log_entry)

        except Exception as e:
            # Log errors should never crash the application
            print(f"Error adding log entry for user {self.user_id}: {e}")
            # Try to write a simple error log as fallback
            try:
                self._emergency_log(message, level, e)
            except:
                pass  # Give up silently if even emergency logging fails

    def _sanitize_message(self, message: str) -> str:
        """Sanitize log message to prevent injection attacks and truncate if too long"""
        if not isinstance(message, str):
            message = str(message)

        # Truncate if too long
        if len(message) > self.MAX_MESSAGE_LENGTH:
            message = message[:self.MAX_MESSAGE_LENGTH] + "... (truncated)"

        # Remove null bytes and other potentially problematic characters
        message = message.replace('\x00', '').replace('\r', ' ').strip()

        return message

    def _validate_level(self, level: str) -> str:
        """Validate and sanitize log level"""
        valid_levels = ['info', 'success', 'warning', 'error', 'debug']

        if not isinstance(level, str):
            return 'info'

        level = level.lower().strip()

        if level not in valid_levels:
            return 'info'

        return level

    def _sanitize_metadata(self, metadata: dict) -> dict:
        """Sanitize metadata to prevent injection and limit size"""
        if not isinstance(metadata, dict):
            return {}

        sanitized = {}

        # Limit number of metadata fields
        MAX_METADATA_FIELDS = 20

        for key, value in list(metadata.items())[:MAX_METADATA_FIELDS]:
            # Sanitize key
            if not isinstance(key, str):
                continue

            key = str(key).replace('\x00', '').strip()

            if len(key) > 100:  # Limit key length
                continue

            # Sanitize value
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, str):
                    value = value.replace('\x00', '').strip()
                    if len(value) > 500:  # Limit value length
                        value = value[:500] + "..."
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            # Ignore complex objects

        return sanitized

    def _emergency_log(self, message: str, level: str, error: Exception):
        """Emergency logging when normal logging fails"""
        try:
            emergency_file = self.log_dir / f"emergency_log_{self.user_id}.txt"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(emergency_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] EMERGENCY LOG - Normal logging failed: {error}\n")
                f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
        except:
            pass  # If even this fails, we give up

    def _clean_message(self, message: str) -> str:
        """Clean up redundant and verbose messages"""
        # Remove ALL emojis and special prefixes
        emoji_prefixes = ["🔧 ", "ℹ️ ", "✅ ", "❌ ", "⚠️ ", "🤖 ", "🔄 ", "📊 ", "🎯 ", "🔍 ", "✓ ", "⏳ ", "🌐 "]
        for emoji in emoji_prefixes:
            message = message.replace(emoji, "")

        # Remove common verbose prefixes
        prefixes_to_remove = [
            "INFO: ",
            "ERROR: ",
            "WARNING: ",
            "SUCCESS: ",
            "DEBUG: ",
            "BookingBot: ",
            "SpaceIQ Bot: ",
            "[BOT] ",
            "[SYSTEM] ",
            "[INFO] ",
            "[ERROR] ",
            "[WARNING] ",
            "[SUCCESS] ",
        ]

        for prefix in prefixes_to_remove:
            if message.startswith(prefix):
                message = message[len(prefix):]

        # Filter out completely redundant or useless messages
        # But IMPORTANT: preserve booking success/failure messages for dashboard status
        useless_messages = [
            "Bot starting...",
            "Running booking workflow - Starting automated booking process",
            "Starting Multi-Date Booking (Web Mode)",
            "Running booking workflow",
            "Starting bot - Building LC, Floor 2",
            "Bot starting",
            "Starting bot",
            "Starting bot for building",
            "Using user-specific screenshots directory",
            "Cleaned up old screenshots",
            "Ready to book",
        ]

        # Don't filter out messages that contain booking results (needed for dashboard)
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in [
            'booked', 'booking verified', 'successfully booked', 'booking success',
            'booking failed', 'no available desks', 'already booked', 'existing booking found'
        ]):
            # This might be an important status message, don't filter it out
            pass
        elif any(useless in message for useless in useless_messages):
            return None  # Signal to skip this message entirely

        # Shorten common verbose messages
        # IMPORTANT: Don't change booking success/failure messages that dashboard needs
        replacements = {
            "Checking desk availability - Scanning for available desks": "Scanning desks",
            "Found booking entries in sidebar": "Found bookings",
            "Found booked desks": "Found booked desks",
            "Loaded locked desks from config": "Loaded locked desks",
            "Starting booking process for": "Booking for",
            # Keep booking success messages intact for dashboard recognition
            # "Successfully booked desk": "Booked desk",  # Don't change this
            # "Failed to book desk": "Booking failed",    # Don't change this
            # "No available desks found": "No desks available",  # Don't change this
            "Session validation successful": "Session valid",
            "Session validation failed": "Session invalid",
            "Waiting for page to load": "Loading page",
            "Clicking book button": "Confirming booking",
            "Navigating to booking page": "Opening booking page",
            "Extracting available desks": "Finding available desks",
            "Filtering out locked desks": "Removing locked desks",
            "Attempting to book desk": "Trying desk",
            "Checking existing bookings...": "Checking existing bookings",
            "Error fetching existing bookings: Locator.click: Timeout 3000ms exceeded": "Timeout checking existing bookings",
            "Loading floor map for": "Loading floor map",
            "Booking desk for - Checking availability and attempting to book": "Booking desk",
            "Loading floor map - Date:": "Loading floor map for",
            "Checking desk availability - Scanning for available desks": "Scanning desks",
            "Processing dates:": "Processing",
            "Progress:": "Progress",
            "Dates to try this round:": "Dates to try",
        }

        # Clean up specific patterns
        import re
        # Remove round numbers and progress details that are already shown elsewhere
        message = re.sub(r'\(Progress: \d+/\d+\)', '', message)
        message = re.sub(r'Loading floor map - Date: \d{4}-\d{2}-\d{2}', lambda m: f"Loading floor map for {m.group().split()[-1]}", message)
        message = re.sub(r'Booking desk for \d{4}-\d{2}-\d{2} - Checking availability and attempting to book \(Progress: \d+/\d+\)',
                         lambda m: f"Booking {m.group().split()[3]}", message)

        for pattern, replacement in replacements.items():
            if pattern in message:
                message = message.replace(pattern, replacement)
                break

        # Clean up whitespace
        message = ' '.join(message.split())

        # Skip very short or empty messages
        if len(message) < 3:
            return None

        return message

    def _metadata_equivalent(self, metadata1: dict, metadata2: dict) -> bool:
        """Check if two metadata dictionaries are essentially equivalent"""
        # Remove timestamp and other dynamic fields for comparison
        static_fields = ['desk', 'date', 'round', 'action', 'user_id', 'bot_id']

        for field in static_fields:
            if metadata1.get(field) != metadata2.get(field):
                return False

        return True

    def _save_text_log(self, log_entry):
        """Save log entry to readable text file with size limits"""
        try:
            # Check if text log file needs rotation
            if self.text_log_file.exists():
                file_size_mb = self.text_log_file.stat().st_size / (1024 * 1024)
                if file_size_mb > self.MAX_FILE_SIZE_MB:
                    # Rotate text log file
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_name = f"{self.text_log_file.stem}_backup_{timestamp}.txt"
                    backup_path = self.text_log_file.parent / backup_name
                    shutil.move(str(self.text_log_file), str(backup_path))
                    print(f"Rotated text log file to: {backup_path}")

            timestamp = datetime.fromisoformat(log_entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            level = log_entry['level'].upper()
            message = log_entry['message']

            with open(self.text_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")

        except Exception as e:
            print(f"Failed to save text log for user {self.user_id}: {e}")

    def get_recent_logs(self, limit: int = 100) -> list:
        """
        Get recent log entries

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of recent log entries
        """
        logs = self._load_logs()
        return logs[-limit:] if logs else []

    def clear_logs(self):
        """Clear all logs"""
        self._initialize_log_file()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the logs"""
        logs = self._load_logs()

        if not logs:
            return {
                "total_logs": 0,
                "levels": {},
                "latest_log": None
            }

        # Count by level
        level_counts = {}
        for log in logs:
            level = log.get('level', 'info')
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "total_logs": len(logs),
            "levels": level_counts,
            "latest_log": logs[-1] if logs else None,
            "oldest_log": logs[0] if logs else None
        }


# Global dictionary to hold live loggers for each user
_live_loggers: Dict[int, LiveLogger] = {}

def get_live_logger(user_id: int) -> LiveLogger:
    """Get or create a live logger for a user"""
    global _live_loggers

    if user_id not in _live_loggers:
        _live_loggers[user_id] = LiveLogger(user_id)

    return _live_loggers[user_id]


def cleanup_old_live_logs():
    """Clean up live logs for inactive users"""
    try:
        import glob

        # Find all live log files
        live_log_files = glob.glob("logs/live_logs_*.json")

        for log_file in live_log_files:
            file_path = Path(log_file)

            # Check if file is older than 7 days
            if file_path.stat().st_mtime < (datetime.now().timestamp() - 7 * 24 * 3600):
                try:
                    file_path.unlink()
                    print(f"Cleaned up old live log file: {file_path}")
                except Exception as e:
                    print(f"Failed to clean up {file_path}: {e}")

    except Exception as e:
        print(f"Error during live log cleanup: {e}")