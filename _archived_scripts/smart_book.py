"""
Smart Booking - Main Entry Point

Runs the intelligent booking workflow that tries multiple dates
and filters by desk prefix, stopping on first success.

Configuration: Edit booking_config.json
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.workflows.smart_booking import SmartBookingWorkflow


async def main():
    """Main execution function for smart booking"""

    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 18 + "SpaceIQ Smart Booking Bot" + " " * 25 + "║")
    print("║" + " " * 15 + "Multi-Date with Desk Filtering" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        return

    # Check auth file
    if not Config.AUTH_STATE_FILE.exists():
        print("\n" + "=" * 70)
        print("⚠️  AUTHENTICATION REQUIRED")
        print("=" * 70)
        print("\nPlease run: python src/auth/capture_session.py")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Check config file
    config_file = Path("booking_config.json")
    if not config_file.exists():
        print("\n" + "=" * 70)
        print("⚠️  CONFIGURATION FILE NOT FOUND")
        print("=" * 70)
        print("\nNo booking_config.json found!")
        print("\nA default configuration file has been created.")
        print("Please edit booking_config.json with:")
        print("  • Dates you want to book (YYYY-MM-DD format)")
        print("  • Desk prefix (e.g., '2.24' for desks starting with 2.24)")
        print("\nThen run this script again.")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Run smart booking
    try:
        workflow = SmartBookingWorkflow()
        results = await workflow.run()

        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)

    except FileNotFoundError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    """
    Entry point when running script directly.

    Usage:
        1. Edit booking_config.json with your dates and desk preferences
        2. Run: python smart_book.py
    """

    print("\n💡 Make sure you've edited booking_config.json first!")
    print("   Set your dates and desk prefix preferences.\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot interrupted by user (Ctrl+C)")
        sys.exit(1)
