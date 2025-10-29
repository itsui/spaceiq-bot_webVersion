"""
Console Logger - Captures all print() output to log file

This ensures EVERYTHING printed to console is also saved to the log file.
ANSI escape codes are stripped from file output to reduce log size.
"""

import sys
import re
from pathlib import Path
from datetime import datetime


class ConsoleLogger:
    """
    Tee-style logger that writes to both console and file.
    Captures all print() statements automatically.
    ANSI escape codes are stripped from file output to prevent gigabyte-sized logs.
    """

    # Regex to match ANSI escape sequences
    ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*[mGKHJhlABCDsu]|\x1b\][^\x07]*\x07|\x1b\].*?\x1b\\|\x1b\[[0-9]*[ABCD]|\x1b\[[\?]?[0-9]*[lh]')

    def __init__(self, log_file: Path, strip_ansi: bool = True):
        self.terminal = sys.stdout
        self.log_file = log_file
        self.file = open(log_file, 'a', encoding='utf-8')
        self.strip_ansi = strip_ansi

    def write(self, message):
        """Write to both terminal and file (file gets cleaned version)"""
        # Always write to terminal as-is (preserves colors)
        self.terminal.write(message)

        # Strip ANSI codes from file output to reduce size
        if self.strip_ansi:
            message = self.ANSI_ESCAPE_PATTERN.sub('', message)

        self.file.write(message)
        self.file.flush()  # Ensure it's written immediately

    def flush(self):
        """Flush both streams"""
        self.terminal.flush()
        self.file.flush()

    def close(self):
        """Close the file handle"""
        self.file.close()


def start_console_logging():
    """
    Start logging all console output to file.

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
        f.write("=" * 70 + "\n\n")

    # Redirect stdout to our logger
    console_logger = ConsoleLogger(log_file, strip_ansi=Config.STRIP_ANSI_FROM_LOGS)
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
