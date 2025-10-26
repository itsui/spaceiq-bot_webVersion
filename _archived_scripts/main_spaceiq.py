"""
SpaceIQ Bot - Main Entry Point (Customized for Your System)

This version uses the customized page objects and workflow based on your
actual SpaceIQ interface.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.workflows.spaceiq_desk_booking import SpaceIQDeskBookingWorkflow
from src.utils.logger import log_workflow_start, log_workflow_end
import time


async def main():
    """
    Main execution function for SpaceIQ desk booking.
    """

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "SpaceIQ Booking Bot" + " " * 29 + "║")
    print("║" + " " * 18 + "Customized for Your System" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("Please complete these steps:")
        print("1. Edit .env and set your SPACEIQ_URL")
        print("2. Run: python src/auth/capture_session.py")
        print("3. Then run this script again\n")
        return

    # Check auth file
    if not Config.AUTH_STATE_FILE.exists():
        print("\n" + "=" * 70)
        print("⚠️  AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("\nNo authenticated session found.")
        print("\nPlease run: python src/auth/capture_session.py")
        print("=" * 70 + "\n")
        sys.exit(1)

    # ============================================================================
    # CONFIGURE YOUR BOOKING HERE
    # ============================================================================

    booking_params = {
        "building": "LC",           # Your building code
        "floor": "2",               # Floor number
        "days_ahead": 1,            # 1 = tomorrow, 0 = today, 2 = day after tomorrow
        "desk_preference": None,    # Optional: specific desk like "2.24.30"
    }

    # Examples of different booking scenarios:

    # Book for tomorrow (default)
    # booking_params = {
    #     "building": "LC",
    #     "floor": "2",
    #     "days_ahead": 1,
    # }

    # Book a specific desk
    # booking_params = {
    #     "building": "LC",
    #     "floor": "2",
    #     "days_ahead": 1,
    #     "desk_preference": "2.24.30",  # Specific desk ID from the map
    # }

    # Book for next week
    # booking_params = {
    #     "building": "LC",
    #     "floor": "2",
    #     "days_ahead": 7,
    # }

    # ============================================================================

    # Log workflow start
    print("\n" + "=" * 70)
    print("Starting Desk Booking")
    print("=" * 70)
    for key, value in booking_params.items():
        if value is not None:
            print(f"   {key}: {value}")
    print("=" * 70 + "\n")

    # Execute workflow
    start_time = time.time()

    workflow = SpaceIQDeskBookingWorkflow()
    success = await workflow.book_desk(**booking_params)

    end_time = time.time()
    duration = end_time - start_time

    # Log workflow end
    log_workflow_end("SpaceIQ Desk Booking", success, duration)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    """
    Entry point when running script directly.

    Usage:
        python main_spaceiq.py
    """

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
