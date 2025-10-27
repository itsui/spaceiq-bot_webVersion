"""
Log File Cleanup Utility

Automatically cleans up old log files, keeping only the most recent sessions.
"""

import re
from pathlib import Path
from typing import Set
import logging


def cleanup_old_logs(logs_dir: Path = None, keep_sessions: int = 2, logger=None):
    """
    Clean up old log files, keeping only the most recent sessions.

    Args:
        logs_dir: Directory containing logs (default: ./logs)
        keep_sessions: Number of recent sessions to keep (default: 2)
        logger: Optional logger instance
    """
    if logs_dir is None:
        logs_dir = Path("logs")

    if not logs_dir.exists():
        return

    # Pattern to extract session timestamp from filename
    # Examples: booking_20251026_214544.log, console_20251026_214544.log
    timestamp_pattern = re.compile(r'(\d{8}_\d{6})')

    # Find all log files with timestamps
    log_files = []

    for file in logs_dir.glob("*.log"):
        # Extract timestamp
        match = timestamp_pattern.search(file.name)
        if match:
            timestamp = match.group(1)
            log_files.append((timestamp, file))

    if not log_files:
        msg = "No log files to clean up"
        # Verbose output suppressed
        # print(f"[CLEANUP] {msg}")
        if logger:
            logger.info(msg)
        return

    # Group log files by session timestamp
    sessions = {}
    for timestamp, file in log_files:
        if timestamp not in sessions:
            sessions[timestamp] = []
        sessions[timestamp].append(file)

    # Sort sessions by timestamp (most recent first)
    sorted_sessions = sorted(sessions.keys(), reverse=True)

    # Keep only the most recent N sessions
    sessions_to_keep = set(sorted_sessions[:keep_sessions])
    sessions_to_delete = set(sorted_sessions[keep_sessions:])

    if not sessions_to_delete:
        msg = f"All log files are from recent sessions (keeping {len(sessions_to_keep)} session(s))"
        # Verbose output suppressed
        # print(f"[CLEANUP] {msg}")
        if logger:
            logger.info(msg)
        return

    # Delete old log files
    deleted_count = 0
    for session_timestamp in sessions_to_delete:
        for file in sessions[session_timestamp]:
            try:
                file.unlink()
                deleted_count += 1
            except Exception as e:
                msg = f"Failed to delete {file.name}: {e}"
                # Verbose output suppressed
                # print(f"[CLEANUP] {msg}")
                if logger:
                    logger.warning(msg)

    # Summary
    kept_count = sum(len(sessions[ts]) for ts in sessions_to_keep)
    msg = f"Deleted {deleted_count} old log file(s) from {len(sessions_to_delete)} session(s), kept {kept_count} from {len(sessions_to_keep)} recent session(s)"
    # Verbose output suppressed
    # print(f"[CLEANUP] {msg}")
    if logger:
        logger.info(msg)

    # Log details
    if logger:
        logger.info(f"Log sessions kept: {sorted(sessions_to_keep, reverse=True)}")
        logger.info(f"Log sessions deleted: {sorted(sessions_to_delete, reverse=True)}")


if __name__ == "__main__":
    # Test cleanup
    print("Log File Cleanup Utility")
    print("=" * 70)
    cleanup_old_logs(keep_sessions=2)
    print("=" * 70)
