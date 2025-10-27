"""
Multi-Date Booking Runner

Reads dates from config/booking_config.json and tries to book all of them.
Successfully booked dates are automatically removed from the config file.

Usage:
    python multi_date_book.py                              # Manual mode: uses dates from config
    python multi_date_book.py --auto                       # Auto mode: generates Wed/Thu dates
    python multi_date_book.py --auto --headless            # PRODUCTION MODE: headless + continuous loop + skip booked
    python multi_date_book.py --auto --unattended          # Auto mode: no prompts (for scheduled runs)
    python multi_date_book.py --loop                       # Continuous loop mode (non-headless)
    python multi_date_book.py --poll                       # Polling mode (try until one succeeds)

Note: Headless mode automatically enables continuous loop and checks existing bookings.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
from src.workflows.multi_date_booking import run_multi_date_booking


def generate_wednesday_thursday_dates(weeks_ahead: int = 4, extra_days: int = 1) -> list[str]:
    """
    Generate all Wednesday and Thursday dates from (today + weeks_ahead*7 + extra_days) down to today.

    Args:
        weeks_ahead: Number of weeks to look ahead (default: 4)
        extra_days: Extra days beyond weeks (default: 1, so 4 weeks + 1 day = 29 days)

    Returns:
        List of date strings in YYYY-MM-DD format, sorted from furthest to closest

    Example:
        If today is Thursday Oct 24, 2024:
        - Furthest date: Oct 24 + 29 days = Nov 22, 2024 (Saturday)
        - Generates all Wed/Thu between today and Nov 22
        - Returns: ["2024-11-21", "2024-11-20", "2024-11-14", "2024-11-13", ...]
    """
    today = datetime.now().date()
    furthest_date = today + timedelta(weeks=weeks_ahead, days=extra_days)

    dates = []
    current_date = today

    # Generate all dates from today to furthest_date
    while current_date <= furthest_date:
        # Check if it's Wednesday (2) or Thursday (3)
        if current_date.weekday() in [2, 3]:
            dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    # Sort from furthest to closest (reverse chronological)
    dates.sort(reverse=True)

    return dates


def update_config_with_auto_dates(dates: list[str]):
    """
    Update booking_config.json with auto-generated dates for reference.

    NOTE: Config is now used for record-keeping only!
    The bot ALWAYS calculates dates fresh from calendar and tries ALL Wed/Thu dates
    within the 29-day window, regardless of config status.

    This prevents false positives from skipping dates that weren't actually booked.

    Args:
        dates: List of date strings for reference
    """
    # Verbose output suppressed - dates are shown by pretty_output module
    pass


async def main():
    """
    Run multi-date booking workflow.

    This script will:
    1. Read dates from config/booking_config.json (or generate if --auto)
    2. Try to book a desk for each date (furthest first)
    3. Remove successfully booked dates from config
    4. Continue until all dates are processed
    """

    # Check for flags
    auto_mode = "--auto" in sys.argv or "-auto" in sys.argv
    unattended = "--unattended" in sys.argv or "-unattended" in sys.argv
    polling_mode = "--poll" in sys.argv or "-poll" in sys.argv
    continuous_loop = "--loop" in sys.argv or "-loop" in sys.argv
    headless = "--headless" in sys.argv or "-headless" in sys.argv

    if auto_mode:
        # Verbose startup output suppressed - using clean pretty output
        # Generate dates silently
        dates = generate_wednesday_thursday_dates(weeks_ahead=4, extra_days=1)
        update_config_with_auto_dates(dates)

        if not unattended:
            input("\nPress Enter to start booking (or Ctrl+C to cancel)...")
    # else:
        # Manual mode tips suppressed - pretty output shows everything needed

    # Mode banners are now shown by the pretty output module
    # All verbose startup output suppressed

    results = await run_multi_date_booking(
        refresh_interval=30,  # Wait 30s between retries
        max_attempts_per_date=10,  # Try each date up to 10 times
        polling_mode=polling_mode,  # Keep trying until seats found
        headless=headless,  # Run without browser window
        continuous_loop=continuous_loop  # Keep trying forever
    )

    # Exit with appropriate code (summary already shown by pretty output)
    if results and all(results.values()):
        exit(0)
    elif results:
        exit(1)
    else:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
