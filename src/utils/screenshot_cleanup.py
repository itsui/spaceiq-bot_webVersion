"""
Screenshot Cleanup Utility

Automatically cleans up old screenshots, keeping only the current and previous session.
"""

import re
from pathlib import Path
from typing import Set
import logging


def cleanup_old_screenshots(screenshots_dir: Path = None, keep_sessions: int = 2, logger=None):
    """
    Clean up old screenshots, keeping only the most recent sessions.

    Args:
        screenshots_dir: Directory containing screenshots (default: ./screenshots)
        keep_sessions: Number of recent sessions to keep (default: 2)
        logger: Optional logger instance
    """
    if screenshots_dir is None:
        screenshots_dir = Path("screenshots")

    if not screenshots_dir.exists():
        return

    # Pattern to extract session timestamp from filename
    # Examples: floor_map_loaded_20251026_214620.png, booking_success_2025-11-19_20251026_213957.png
    timestamp_pattern = re.compile(r'(\d{8}_\d{6})')

    # Find all automated screenshots (exclude manual screenshots like "Screenshot 2025-10-27...")
    automated_screenshots = []
    manual_screenshots = []

    for file in screenshots_dir.glob("*.png"):
        # Skip manual screenshots (ones that start with "Screenshot ")
        if file.name.startswith("Screenshot "):
            manual_screenshots.append(file)
            continue

        # Extract timestamp from automated screenshots
        match = timestamp_pattern.search(file.name)
        if match:
            timestamp = match.group(1)
            automated_screenshots.append((timestamp, file))

    if not automated_screenshots:
        msg = "No automated screenshots to clean up"
        # Verbose output suppressed
        # print(f"[CLEANUP] {msg}")
        if logger:
            logger.info(msg)
        return

    # Group screenshots by session timestamp
    sessions = {}
    for timestamp, file in automated_screenshots:
        if timestamp not in sessions:
            sessions[timestamp] = []
        sessions[timestamp].append(file)

    # Sort sessions by timestamp (most recent first)
    sorted_sessions = sorted(sessions.keys(), reverse=True)

    # Keep only the most recent N sessions
    sessions_to_keep = set(sorted_sessions[:keep_sessions])
    sessions_to_delete = set(sorted_sessions[keep_sessions:])

    if not sessions_to_delete:
        msg = f"All screenshots are from recent sessions (keeping {len(sessions_to_keep)} session(s))"
        # Verbose output suppressed
        # print(f"[CLEANUP] {msg}")
        if logger:
            logger.info(msg)
        return

    # Delete old screenshots
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
    msg = f"Deleted {deleted_count} old screenshot(s) from {len(sessions_to_delete)} session(s), kept {kept_count} from {len(sessions_to_keep)} recent session(s)"
    # Verbose output suppressed
    # print(f"[CLEANUP] {msg}")
    if logger:
        logger.info(msg)

    # Log details
    if logger:
        logger.info(f"Sessions kept: {sorted(sessions_to_keep, reverse=True)}")
        logger.info(f"Sessions deleted: {sorted(sessions_to_delete, reverse=True)}")
        logger.info(f"Manual screenshots preserved: {len(manual_screenshots)}")


if __name__ == "__main__":
    # Test cleanup
    print("Screenshot Cleanup Utility")
    print("=" * 70)
    cleanup_old_screenshots(keep_sessions=2)
    print("=" * 70)
