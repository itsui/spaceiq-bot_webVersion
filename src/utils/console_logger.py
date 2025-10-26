"""
Console Logger - Captures all print() output to log file

This ensures EVERYTHING printed to console is also saved to the log file.
"""

import sys
from pathlib import Path
from datetime import datetime


class ConsoleLogger:
    """
    Tee-style logger that writes to both console and file.
    Captures all print() statements automatically.
    """

    def __init__(self, log_file: Path):
        self.terminal = sys.stdout
        self.log_file = log_file
        self.file = open(log_file, 'a', encoding='utf-8')

    def write(self, message):
        """Write to both terminal and file"""
        self.terminal.write(message)
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
        Tuple of (log_file_path, console_logger_instance)
    """
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
        f.write("=" * 70 + "\n\n")

    # Redirect stdout to our logger
    console_logger = ConsoleLogger(log_file)
    sys.stdout = console_logger

    print(f"\n[LOGGING] All output is being saved to: {log_file}\n")

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
