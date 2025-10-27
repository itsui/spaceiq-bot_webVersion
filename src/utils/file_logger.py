"""
File logging utility for debugging
Logs all actions to a timestamped file
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_file_logger(name: str = "spaceiq_bot") -> logging.Logger:
    """
    Set up a logger that writes to both console and file.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"booking_{timestamp}.log"

    # File handler (detailed)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # NO console handler - all user-facing output goes through pretty_output module
    # Logger writes ONLY to file for debugging

    logger.addHandler(file_handler)

    # Log to file only (not console)
    logger.info(f"Logging to: {log_file}")

    return logger, log_file
