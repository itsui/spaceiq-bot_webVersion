"""
Enhanced logging utility for SpaceIQ Bot

Provides consistent logging format across the application with:
- Error tracking and debugging capabilities
- File and console logging with rotation
- Structured logging for better analysis
- Error context capture for debugging
"""

import logging
import traceback
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
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


# ========== Enhanced Error Logging and Debugging ==========

class ErrorTracker:
    """
    Track and log errors with comprehensive debugging information
    """

    def __init__(self, log_dir: Path = None):
        if log_dir is None:
            log_dir = Path("logs") / "errors"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.error_log_file = self.log_dir / "error_log.jsonl"  # JSON Lines format
        self.critical_log_file = self.log_dir / "critical_errors.txt"

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
        user_id: Optional[int] = None
    ):
        """
        Log an error with full context and stack trace

        Args:
            error: The exception that occurred
            context: Additional context information
            level: Error level (error, warning, critical)
            user_id: Optional user ID for multi-user tracking
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {},
            "user_id": user_id
        }

        # Write to JSON Lines file for structured logging
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_data) + '\n')
        except Exception as e:
            print(f"Failed to write error log: {e}")

        # Write critical errors to separate file for immediate attention
        if level == "critical":
            try:
                with open(self.critical_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"CRITICAL ERROR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*80}\n")
                    f.write(f"Type: {type(error).__name__}\n")
                    f.write(f"Message: {str(error)}\n")
                    if user_id:
                        f.write(f"User ID: {user_id}\n")
                    if context:
                        f.write(f"Context: {json.dumps(context, indent=2)}\n")
                    f.write(f"\nStack Trace:\n{traceback.format_exc()}\n")
            except Exception as e:
                print(f"Failed to write critical error log: {e}")

    def log_booking_error(
        self,
        date: str,
        error: Exception,
        desk: Optional[str] = None,
        user_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """
        Log booking-specific errors with structured context

        Args:
            date: The date being booked
            error: The exception that occurred
            desk: Desk code if applicable
            user_id: User ID
            additional_context: Additional context information
        """
        context = {
            "booking_date": date,
            "desk_code": desk,
            "workflow": "desk_booking",
            **(additional_context or {})
        }

        self.log_error(error, context=context, level="error", user_id=user_id)

    def log_session_error(
        self,
        error: Exception,
        session_file: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """
        Log session-related errors

        Args:
            error: The exception that occurred
            session_file: Path to session file
            user_id: User ID
        """
        context = {
            "workflow": "session_management",
            "session_file": session_file,
        }

        self.log_error(error, context=context, level="error", user_id=user_id)

    def get_recent_errors(self, limit: int = 50) -> list:
        """
        Get recent errors from the log

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error dictionaries
        """
        try:
            if not self.error_log_file.exists():
                return []

            errors = []
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Get last N lines
            for line in lines[-limit:]:
                try:
                    errors.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

            return errors
        except Exception as e:
            print(f"Failed to read error log: {e}")
            return []

    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get statistics about logged errors

        Returns:
            Dictionary with error statistics
        """
        try:
            errors = self.get_recent_errors(limit=1000)

            if not errors:
                return {
                    "total_errors": 0,
                    "by_type": {},
                    "by_level": {},
                    "by_user": {}
                }

            error_types = {}
            error_levels = {}
            error_users = {}

            for error in errors:
                # Count by type
                error_type = error.get('error_type', 'Unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

                # Count by level
                level = error.get('level', 'unknown')
                error_levels[level] = error_levels.get(level, 0) + 1

                # Count by user
                user_id = error.get('user_id')
                if user_id:
                    error_users[user_id] = error_users.get(user_id, 0) + 1

            return {
                "total_errors": len(errors),
                "by_type": error_types,
                "by_level": error_levels,
                "by_user": error_users,
                "latest_error": errors[-1] if errors else None
            }
        except Exception as e:
            print(f"Failed to generate error stats: {e}")
            return {}


# Global error tracker instance
_error_tracker = None

def get_error_tracker() -> ErrorTracker:
    """Get or create the global error tracker"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def log_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error",
    user_id: Optional[int] = None
):
    """
    Convenience function to log an exception using the global error tracker

    Args:
        error: The exception to log
        context: Additional context information
        level: Error level (error, warning, critical)
        user_id: Optional user ID
    """
    tracker = get_error_tracker()
    tracker.log_error(error, context=context, level=level, user_id=user_id)


def log_booking_failure(
    date: str,
    error: Exception,
    desk: Optional[str] = None,
    user_id: Optional[int] = None,
    **kwargs
):
    """
    Convenience function to log booking failures

    Args:
        date: Booking date
        error: The exception that occurred
        desk: Desk code if applicable
        user_id: User ID
        **kwargs: Additional context
    """
    tracker = get_error_tracker()
    tracker.log_booking_error(date, error, desk=desk, user_id=user_id, additional_context=kwargs)
