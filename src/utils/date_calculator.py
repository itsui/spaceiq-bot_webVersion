"""
Date Auto-Calculation Utility

Automatically calculates booking dates based on:
- Selected weekdays (e.g., Tuesday, Wednesday)
- 29-day booking window
- Blacklist dates (holidays, vacations)
- Preserves manually added dates
"""

from datetime import datetime, timedelta, date
from typing import List, Set


def parse_blacklist_dates(blacklist: List[str]) -> Set[str]:
    """
    Parse blacklist dates, supporting both individual dates and ranges.

    Args:
        blacklist: List of dates like ["2025-12-25", "2025-01-01:2025-01-07"]

    Returns:
        Set of blacklisted date strings in YYYY-MM-DD format
    """
    blacklisted = set()

    for entry in blacklist:
        if ':' in entry:
            # Range: "2025-01-01:2025-01-07"
            try:
                start_str, end_str = entry.split(':')
                start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d').date()

                # Add all dates in range
                current = start_date
                while current <= end_date:
                    blacklisted.add(current.strftime('%Y-%m-%d'))
                    current += timedelta(days=1)
            except Exception as e:
                print(f"Warning: Invalid date range '{entry}': {e}")
        else:
            # Individual date
            try:
                parsed = datetime.strptime(entry.strip(), '%Y-%m-%d')
                blacklisted.add(parsed.strftime('%Y-%m-%d'))
            except Exception as e:
                print(f"Warning: Invalid date '{entry}': {e}")

    return blacklisted


def calculate_booking_dates(
    weekdays: List[int],
    blacklist_dates: List[str] = None,
    existing_dates: List[str] = None,
    today: date = None
) -> List[str]:
    """
    Calculate booking dates for the next 29 days based on weekdays.

    Args:
        weekdays: List of weekday integers (0=Monday, 1=Tuesday, ..., 6=Sunday)
        blacklist_dates: List of dates to exclude (supports ranges like "2025-01-01:2025-01-07")
        existing_dates: List of manually added dates to preserve
        today: Starting date (defaults to today)

    Returns:
        List of date strings in YYYY-MM-DD format, sorted descending (newest first)
    """
    if today is None:
        today = datetime.now().date()

    if blacklist_dates is None:
        blacklist_dates = []

    if existing_dates is None:
        existing_dates = []

    # Parse blacklist (supports ranges)
    blacklisted = parse_blacklist_dates(blacklist_dates)

    # Calculate auto-generated dates for next 29 days
    auto_dates = set()
    furthest_date = today + timedelta(days=29)

    current = today
    while current <= furthest_date:
        # Check if day matches selected weekdays
        if current.weekday() in weekdays:
            date_str = current.strftime('%Y-%m-%d')

            # Skip if blacklisted
            if date_str not in blacklisted:
                auto_dates.add(date_str)

        current += timedelta(days=1)

    # Separate existing dates into auto-generated and manual
    manual_dates = set()
    for date_str in existing_dates:
        try:
            existing_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # If date is NOT in auto_dates and is in the future, it's manually added
            if date_str not in auto_dates and existing_date >= today:
                # Keep manual dates UNLESS they're blacklisted
                if date_str not in blacklisted:
                    manual_dates.add(date_str)
        except Exception:
            # Invalid date format, skip
            continue

    # Combine auto-generated and manual dates
    all_dates = auto_dates | manual_dates

    # Sort descending (newest first, as per original behavior)
    sorted_dates = sorted(all_dates, reverse=True)

    return sorted_dates


def update_user_dates(bot_config, preserve_manual: bool = True):
    """
    Update a user's dates based on their config.

    Args:
        bot_config: BotConfig instance
        preserve_manual: If True, preserves manually added dates

    Returns:
        List of updated dates
    """
    # Get current configuration
    booking_days = bot_config.get_booking_days()
    weekdays = booking_days.get('weekdays', [2, 3])  # Default: Wed, Thu

    blacklist = bot_config.get_blacklist_dates()

    existing_dates = bot_config.get_dates_to_try() if preserve_manual else []

    # Calculate new dates
    new_dates = calculate_booking_dates(
        weekdays=weekdays,
        blacklist_dates=blacklist,
        existing_dates=existing_dates
    )

    # Update config
    bot_config.set_dates_to_try(new_dates)

    return new_dates


if __name__ == "__main__":
    # Test the utility
    print("Date Calculator Test\n" + "=" * 70)

    # Test 1: Basic calculation
    dates = calculate_booking_dates(
        weekdays=[1, 2],  # Tuesday, Wednesday
        blacklist_dates=[],
        existing_dates=[]
    )
    print(f"\nTest 1: Next 29 days (Tue+Wed)")
    print(f"Generated {len(dates)} dates")
    print(f"Sample: {dates[:5]}")

    # Test 2: With blacklist range
    dates = calculate_booking_dates(
        weekdays=[1, 2],
        blacklist_dates=["2025-12-24:2025-12-31"],  # Christmas week
        existing_dates=[]
    )
    print(f"\nTest 2: With blacklist range (Christmas week)")
    print(f"Generated {len(dates)} dates (excluding Dec 24-31)")

    # Test 3: Preserve manual dates
    manual = ["2025-11-15", "2025-11-22"]  # Friday dates (not in weekdays)
    dates = calculate_booking_dates(
        weekdays=[1, 2],  # Only Tue+Wed
        blacklist_dates=[],
        existing_dates=manual
    )
    print(f"\nTest 3: Preserve manual dates")
    print(f"Manual dates preserved: {[d for d in dates if d in manual]}")

    # Test 4: Blacklist affects manual dates
    dates = calculate_booking_dates(
        weekdays=[1, 2],
        blacklist_dates=["2025-11-15"],  # Blacklist one manual date
        existing_dates=["2025-11-15", "2025-11-22"]
    )
    print(f"\nTest 4: Blacklist removes manual dates")
    print(f"2025-11-15 in results: {'2025-11-15' in dates}")
    print(f"2025-11-22 in results: {'2025-11-22' in dates}")

    print("\n" + "=" * 70)
