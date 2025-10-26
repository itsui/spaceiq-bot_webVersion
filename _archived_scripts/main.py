"""
SpaceIQ Bot - Main Entry Point

Phase 1: DOM-based automation with Playwright
Demonstrates the complete booking workflow.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.workflows.desk_booking import DeskBookingWorkflow
from src.utils.helpers import format_date, validate_booking_params
from src.utils.logger import log_workflow_start, log_workflow_end
import time


async def main():
    """
    Main execution function.

    This is a template that demonstrates how to use the bot.
    Customize the booking parameters as needed.
    """

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "SpaceIQ Booking Bot" + " " * 29 + "║")
    print("║" + " " * 22 + "Phase 1: DOM-Based" + " " * 28 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("Please complete these steps:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env and set your SPACEIQ_URL")
        print("3. Run: python src/auth/capture_session.py")
        print("4. Then run this script again\n")
        return

    # ============================================================================
    # CUSTOMIZE YOUR BOOKING PARAMETERS HERE
    # ============================================================================

    # Example 1: Book for tomorrow
    booking_params = {
        "location": "Main Office",  # ← Change this to your location
        "date": format_date(days_ahead=1),  # Tomorrow
    }

    # Example 2: Book for a specific date
    # booking_params = {
    #     "location": "New York Office",
    #     "date": "2025-10-30",
    # }

    # Example 3: Book with preferences (Phase 2 feature - not yet implemented)
    # booking_params = {
    #     "location": "San Francisco Office",
    #     "date": format_date(days_ahead=2),
    #     "space_preferences": {
    #         "floor": "5",
    #         "features": ["window", "standing desk"]
    #     }
    # }

    # ============================================================================

    # Validate parameters
    try:
        validate_booking_params(
            location=booking_params["location"],
            date=booking_params["date"]
        )
    except ValueError as e:
        print(f"\n❌ Invalid booking parameters: {e}\n")
        return

    # Log workflow start
    log_workflow_start("Desk Booking", booking_params)

    # Execute workflow
    start_time = time.time()

    workflow = DeskBookingWorkflow()
    success = await workflow.book_desk(**booking_params)

    end_time = time.time()
    duration = end_time - start_time

    # Log workflow end
    log_workflow_end("Desk Booking", success, duration)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    """
    Entry point when running script directly.

    Usage:
        python main.py
    """

    # Check if auth file exists
    if not Config.AUTH_STATE_FILE.exists():
        print("\n" + "=" * 70)
        print("⚠️  AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("\nNo authenticated session found.")
        print("\nPlease run the session capture script first:")
        print("\n    python src/auth/capture_session.py")
        print("\nThis is a one-time setup to capture your login session.")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Run the bot
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
