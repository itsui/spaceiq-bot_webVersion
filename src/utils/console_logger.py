"""
Console Logger - Captures all print() output to log file with size limiting

This ensures EVERYTHING printed to console is also saved to the log file.
ANSI escape codes are stripped from file output to reduce log size.
File size is limited to prevent multi-GB logs during long runs.
"""

import sys
import re
from pathlib import Path
from datetime import datetime


class ConsoleLogger:
    """
    Tee-style logger that writes to both console and file.
    Captures all print() statements automatically.
    ANSI escape codes are stripped from file output.
    Implements circular buffer to limit file size.
    """

    # Regex to match ANSI escape sequences
    ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*[mGKHJhlABCDsu]|\x1b\][^\x07]*\x07|\x1b\].*?\x1b\|\x1b\[[0-9]*[ABCD]|\x1b\[[\?]?[0-9]*[lh]')

    def __init__(self, log_file: Path, strip_ansi: bool = True, max_size_mb: int = 100):
        self.terminal = sys.stdout
        self.log_file = log_file
        self.file = open(log_file, 'a', encoding='utf-8')
        self.strip_ansi = strip_ansi
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.check_counter = 0
        self.last_message = ""  # Track last message to filter duplicates
        self.duplicate_count = 0

    def write(self, message):
        """Write to both terminal and file (file gets cleaned version)"""
        # Always write to terminal as-is (preserves colors)
        self.terminal.write(message)

        # Strip ANSI codes from file output to reduce size
        if self.strip_ansi:
            clean_message = self.ANSI_ESCAPE_PATTERN.sub('', message)
        else:
            clean_message = message

        # Immediate filter for huge timeout errors (line by line)
        if any(keyword in clean_message.lower() for keyword in [
            'locator.click: timeout', 'waiting for locator', 'attempting click action',
            'retrying click action', 'call log', 'timeout 3000ms exceeded'
        ]):
            # Skip these lines entirely, but preserve existing booking messages
            if 'existing booking found' not in clean_message.lower():
                self.file.flush()
                return

        # Filter out duplicate and useless messages to reduce log spam
        message_stripped = clean_message.strip()

        if not message_stripped:
            # Empty lines or newlines, just write them
            self.file.write(clean_message)
        elif message_stripped == self.last_message:
            # Exact duplicate, skip it
            self.duplicate_count += 1
            # Only write every 20th duplicate to file to reduce spam even more
            if self.duplicate_count % 20 == 0:
                self.file.write(clean_message)
            else:
                # Don't write to file but still flush terminal
                self.file.flush()
                return
        elif self._is_useless_message(message_stripped):
            # Skip useless messages entirely
            return
        else:
            # New message, reset duplicate counter
            self.last_message = message_stripped
            self.duplicate_count = 0
            self.file.write(clean_message)

        # Check file size every 100 writes (performance optimization)
        self.check_counter += 1
        if self.check_counter >= 100:
            self.check_counter = 0
            self._check_and_rotate_if_needed()
        else:
            # Still flush regularly for real-time logging
            self.file.flush()

    def _is_useless_message(self, message: str) -> bool:
        """Check if a message is useless and should be filtered out"""
        # Only filter true startup messages and huge errors, keep operational messages
        useless_patterns = [
            "Bot starting...",
            "Starting bot for building",
            "Starting bot - Building",
            "Running booking workflow - Starting automated booking process",
            "Starting Multi-Date Booking",
            "Using user-specific screenshots directory",
            "Cleaned up old screenshots",
            "Ready to book",
            "Updated",
            "dates in database for user",
            "Found dates to try",
            "Validating session for headless mode",
            # Keep operational messages like:
            # - "Navigating to SpaceIQ"
            # - "Starting Round X"
            # - "Checking existing bookings"
            # - "Attempting booking for"
            # - "Loading floor map"
            # - "Checking available desks"
            # - "Found X available desks"
            # - "No available desks"
            # Only filter huge errors:
            "Locator.click: Timeout",  # Skip huge timeout errors
            "timeout 3000ms exceeded",  # Skip timeout messages
            "Call log",  # Skip detailed call logs
            "waiting for locator",  # Skip locator waiting messages
            "attempting click action",  # Skip click attempts
            "retrying click action",  # Skip retry attempts
        ]

        # But preserve important messages
        preserve_patterns = [
            "existing booking found",
            "successfully booked",
            "booking verified",
            "no available desks",
            "found available desks",
            "attempting booking for",
            "loading floor map",
            "starting round"
        ]

        message_lower = message.lower()

        # Preserve important messages
        if any(pattern in message_lower for pattern in preserve_patterns):
            return False

        return any(pattern.lower() in message_lower for pattern in useless_patterns)

    def _check_and_rotate_if_needed(self):
        """Check file size and rotate if needed"""
        try:
            self.file.flush()
            current_size = self.log_file.stat().st_size

            # If file exceeds max size, truncate it by keeping only last portion
            if current_size > self.max_size_bytes:
                # Close current file
                self.file.close()

                # Read last 70% of file (keep recent logs)
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(int(current_size * 0.3))  # Skip first 30%
                    f.readline()  # Skip partial line
                    content = f.read()

                # Rewrite file with only recent content
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"\n{'='*70}\n")
                    f.write(f"LOG ROTATED - File exceeded {self.max_size_bytes // 1024 // 1024}MB\n")
                    f.write(f"Keeping last 70% of content\n")
                    f.write(f"{'='*70}\n\n")
                    f.write(content)

                # Reopen file for appending
                self.file = open(self.log_file, 'a', encoding='utf-8')

        except Exception as e:
            # If rotation fails, just continue logging
            pass

    def flush(self):
        """Flush both streams"""
        self.terminal.flush()
        self.file.flush()

    def close(self):
        """Close the file handle"""
        self.file.close()


def start_console_logging():
    """
    Start logging all console output to file with size limiting.

    Returns:
        Tuple of (log_file_path, console_logger_instance) or (None, None) if disabled
    """
    from config import Config

    # Check if console logging is enabled
    if not Config.ENABLE_CONSOLE_LOGGING:
        return None, None

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"console_{timestamp}.log"

    # Write header
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write(f"SpaceIQ Booking Bot - Console Log\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"ANSI codes stripped: {Config.STRIP_ANSI_FROM_LOGS}\n")
        f.write(f"Max log size: {getattr(Config, 'MAX_CONSOLE_LOG_SIZE_MB', 100)}MB (auto-rotates)\n")
        f.write("=" * 70 + "\n\n")

    # Get max size from config (default 100MB)
    max_size_mb = getattr(Config, 'MAX_CONSOLE_LOG_SIZE_MB', 100)

    # Redirect stdout to our logger
    console_logger = ConsoleLogger(log_file, strip_ansi=Config.STRIP_ANSI_FROM_LOGS, max_size_mb=max_size_mb)
    sys.stdout = console_logger

    # Verbose output suppressed - logging happens silently
    # print(f"\n[LOGGING] All output is being saved to: {log_file}\n")

    return log_file, console_logger


def stop_console_logging(console_logger):
    """
    Stop console logging and restore normal output.

    Args:
        console_logger: The ConsoleLogger instance to stop
    """
    if console_logger:
        # Restore original stdout
        sys.stdout = console_logger.terminal
        console_logger.close()
        print("[LOGGING] Console logging stopped")
