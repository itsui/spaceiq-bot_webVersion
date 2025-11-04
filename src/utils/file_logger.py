"""
File logging utility for debugging
Logs all actions to a timestamped file with size rotation
"""

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path


def setup_file_logger(name: str = "spaceiq_bot", max_bytes: int = 50 * 1024 * 1024, backup_count: int = 3):
    """
    Set up a logger that writes to file with automatic size rotation.

    Args:
        name: Logger name
        max_bytes: Maximum log file size before rotation (default: 50MB)
        backup_count: Number of backup files to keep (default: 3)

    Returns:
        Tuple of (logger instance, log file path)
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if logger.handlers:
        # Return existing handler's file path
        for handler in logger.handlers:
            if isinstance(handler, (logging.FileHandler, RotatingFileHandler)):
                return logger, Path(handler.baseFilename)
        return logger, None

    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"booking_{timestamp}.log"

    # Rotating file handler - limits file size
    # When log reaches max_bytes, it rotates to .log.1, .log.2, etc.
    # Only keeps last backup_count files
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,  # 50MB default
        backupCount=backup_count,  # Keep 3 backups (total ~200MB max)
        encoding='utf-8'
    )
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
    logger.info(f"Logging to: {log_file} (max size: {max_bytes // 1024 // 1024}MB, {backup_count} backups)")

    return logger, log_file
