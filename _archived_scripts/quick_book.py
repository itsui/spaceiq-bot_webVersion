"""
Quick Booking Script - All-in-One

Automatically warms session and runs multi-date booking in one command.
Perfect for quick manual runs or scheduled tasks.

Usage:
    python quick_book.py                    # Warm session + book dates from config
    python quick_book.py --auto             # Warm session + auto-generate Wed/Thu dates
    python quick_book.py --auto --poll      # Warm session + keep trying until booked
    python quick_book.py --skip-warm        # Skip session warming (use existing session)

How it works:
    1. Warms the session (if not skipped):
       - Opens browser automatically
       - Checks login status
       - Waits for manual SSO login if needed
       - Saves session for booking
    2. Runs multi-date booking:
       - Uses warmed session
       - Books all configured dates
       - Saves results
"""

import asyncio
import sys
from pathlib import Path


async def run_quick_booking():
    """Run session warming followed by booking"""

    skip_warm = "--skip-warm" in sys.argv

    print("\n" + "=" * 70)
    print("         Quick Booking - All-in-One")
    print("=" * 70)

    if not skip_warm:
        print("\nSTEP 1: Warming Session")
        print("=" * 70)

        # Import and run session warmer
        from auto_warm_session import auto_warm_session

        success = await auto_warm_session(headless=False)

        if not success:
            print("\n[ERROR] Session warming failed. Cannot proceed with booking.")
            return False

        print("\n[SUCCESS] Session warmed successfully!")
        print("\nSTEP 2: Running Booking Bot")
        print("=" * 70 + "\n")

        # Small delay before booking
        await asyncio.sleep(2)
    else:
        print("\n[INFO] Skipping session warming (using existing session)")
        print("\nSTEP 1: Running Booking Bot")
        print("=" * 70 + "\n")

    # Import and run booking
    from src.workflows.multi_date_booking import run_multi_date_booking

    # Determine modes
    polling_mode = "--poll" in sys.argv or "-poll" in sys.argv
    headless = "--headless" in sys.argv or "-headless" in sys.argv

    if headless:
        print("\n[INFO] Headless mode enabled (no browser window)")

    # Run booking
    results = await run_multi_date_booking(
        refresh_interval=30,
        max_attempts_per_date=10,
        polling_mode=polling_mode,
        headless=headless
    )

    # Show final summary
    print("\n" + "=" * 70)
    print("         QUICK BOOKING COMPLETE")
    print("=" * 70)

    if results:
        booked_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        print(f"\nBooked: {booked_count}/{total_count} dates")

        if booked_count == total_count:
            print("[SUCCESS] All dates booked!")
            return True
        elif booked_count > 0:
            print("[PARTIAL] Some dates booked")
            return True
        else:
            print("[FAILED] No dates booked")
            return False
    else:
        print("[FAILED] No results")
        return False


async def main():
    """Main entry point"""
    try:
        success = await run_quick_booking()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Booking cancelled by user (Ctrl+C)")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
