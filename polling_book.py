"""
Polling Booking - Keep Trying Until Desk is Available

For a single date, keeps trying to book a desk with periodic refreshes.
Perfect for when desks are usually occupied and you want to catch one as soon as available.

Configuration: Edit this file or use booking_config.json
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.workflows.polling_booking import PollingBookingWorkflow


async def main():
    """Main execution function for polling booking"""

    print("\n")
    print("=" * 70)
    print("         SpaceIQ Polling Booking Bot")
    print("         Keeps Trying Until Desk Available")
    print("=" * 70)
    print("\n")

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}\n")
        return

    # Check auth file
    if not Config.AUTH_STATE_FILE.exists():
        print("\n" + "=" * 70)
        print("[WARNING] AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("\nPlease run: python src/auth/capture_session.py")
        print("=" * 70 + "\n")
        sys.exit(1)

    # ========================================================================
    # CONFIGURE YOUR POLLING BOOKING HERE
    # ========================================================================

    config = {
        "building": "LC",
        "floor": "2",
        "date_str": "2025-11-12",      # Date to book (YYYY-MM-DD)
        "desk_prefix": "2.24",         # Only book 2.24.* desks
        "refresh_interval": 30,        # Wait 30 seconds between attempts
        "max_attempts": 40             # Try up to 40 times (20 minutes)
    }

    # Examples:

    # Book for specific date, check every 30 seconds for 20 minutes
    # config = {
    #     "date_str": "2025-10-28",
    #     "desk_prefix": "2.24",
    #     "refresh_interval": 30,
    #     "max_attempts": 40
    # }

    # More aggressive: Check every 15 seconds
    # config = {
    #     "date_str": "2025-10-28",
    #     "desk_prefix": "2.24",
    #     "refresh_interval": 15,
    #     "max_attempts": 80  # 20 minutes total
    # }

    # More patient: Check every minute
    # config = {
    #     "date_str": "2025-10-28",
    #     "desk_prefix": "2.24",
    #     "refresh_interval": 60,
    #     "max_attempts": 30  # 30 minutes total
    # }

    # ========================================================================

    # Show configuration
    print("Configuration:")
    print(f"   Date: {config['date_str']}")
    print(f"   Desk prefix: {config['desk_prefix']}.*")
    print(f"   Refresh interval: {config['refresh_interval']}s")
    print(f"   Max attempts: {config['max_attempts']}")

    total_time = (config['refresh_interval'] * config['max_attempts']) // 60
    print(f"   Total time: ~{total_time} minutes")
    print()

    # Confirm (auto-confirm for testing)
    # response = input("Start polling booking? (y/n): ")
    # if response.lower() != 'y':
    #     print("Cancelled.")
    #     sys.exit(0)
    print("Starting polling booking (auto-confirmed for testing)...\n")

    # Run polling booking
    try:
        workflow = PollingBookingWorkflow(**config)
        success = await workflow.run()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """
    Entry point when running script directly.

    Usage:
        1. Edit config in this file (around line 45)
        2. Run: python polling_book.py
        3. Bot will keep trying until desk is available or max attempts reached
    """

    print("\nTip: This will keep trying to book a desk with periodic refreshes.")
    print("     Perfect for popular dates when desks are usually occupied!\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[WARNING] Bot interrupted by user (Ctrl+C)")
        sys.exit(1)
