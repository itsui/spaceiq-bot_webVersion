"""
Helper utilities for SpaceIQ Bot

Common functions used across the application.
"""

from datetime import datetime, timedelta
from typing import Optional


def format_date(date_str: Optional[str] = None, days_ahead: int = 0) -> str:
    """
    Format date for SpaceIQ booking.

    Args:
        date_str: Date string in 'YYYY-MM-DD' format. If None, uses today + days_ahead
        days_ahead: Number of days ahead from today (default: 0)

    Returns:
        Formatted date string

    Example:
        format_date()  # Today
        format_date(days_ahead=1)  # Tomorrow
        format_date("2025-10-30")  # Specific date
    """
    if date_str:
        # Validate format
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            raise ValueError("Date must be in 'YYYY-MM-DD' format")

    target_date = datetime.now() + timedelta(days=days_ahead)
    return target_date.strftime('%Y-%m-%d')


def parse_time(time_str: str) -> str:
    """
    Parse and validate time string.

    Args:
        time_str: Time in 'HH:MM' format

    Returns:
        Validated time string

    Example:
        parse_time("14:30")  # Returns "14:30"
    """
    try:
        datetime.strptime(time_str, '%H:%M')
        return time_str
    except ValueError:
        raise ValueError("Time must be in 'HH:MM' format (24-hour)")


def get_business_days_ahead(num_days: int) -> str:
    """
    Get date for N business days ahead (skipping weekends).

    Args:
        num_days: Number of business days ahead

    Returns:
        Date string in 'YYYY-MM-DD' format

    Example:
        get_business_days_ahead(1)  # Next business day
        get_business_days_ahead(5)  # 5 business days ahead
    """
    current_date = datetime.now()
    business_days_added = 0

    while business_days_added < num_days:
        current_date += timedelta(days=1)
        # Check if it's a weekday (Monday=0, Sunday=6)
        if current_date.weekday() < 5:
            business_days_added += 1

    return current_date.strftime('%Y-%m-%d')


def validate_booking_params(location: str, date: str) -> bool:
    """
    Validate booking parameters before execution.

    Args:
        location: Location name
        date: Date string

    Returns:
        True if valid, raises ValueError if invalid
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")

    # Validate date format
    try:
        booking_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Date must be in 'YYYY-MM-DD' format")

    # Check if date is not in the past
    if booking_date.date() < datetime.now().date():
        raise ValueError("Cannot book for a past date")

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for saving screenshots/logs.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem

    Example:
        sanitize_filename("Book Room: 2025/10/30")  # Returns "Book_Room_2025_10_30"
    """
    # Replace invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove multiple underscores
    while '__' in filename:
        filename = filename.replace('__', '_')

    return filename.strip('_')
