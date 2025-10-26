"""
Simple logging utility for SpaceIQ Bot

Provides consistent logging format across the application.
"""

import logging
from datetime import datetime
from pathlib import Path
from config import Config


def setup_logger(name: str = "SpaceIQBot", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Args:
        name: Logger name
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def log_workflow_start(workflow_name: str, params: dict = None):
    """
    Log the start of a workflow with parameters.

    Args:
        workflow_name: Name of the workflow
        params: Dictionary of workflow parameters
    """
    print("\n" + "=" * 70)
    print(f"🚀 Starting: {workflow_name}")
    print("=" * 70)
    if params:
        for key, value in params.items():
            print(f"   {key}: {value}")
    print("=" * 70 + "\n")


def log_workflow_end(workflow_name: str, success: bool, duration: float = None):
    """
    Log the end of a workflow with status.

    Args:
        workflow_name: Name of the workflow
        success: Whether workflow succeeded
        duration: Optional duration in seconds
    """
    symbol = "✅" if success else "❌"
    status = "SUCCESS" if success else "FAILED"

    print("\n" + "=" * 70)
    print(f"{symbol} {workflow_name}: {status}")
    if duration:
        print(f"   Duration: {duration:.2f} seconds")
    print("=" * 70 + "\n")
