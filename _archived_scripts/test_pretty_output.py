"""
Demo of the new pretty terminal output
"""

import time
import asyncio
from src.utils.pretty_output import PrettyOutput as pout

def demo():
    """Show off the new pretty output"""

    # Header
    pout.header("SpaceIQ Multi-Date Booking Bot")

    # Info
    pout.info("Target: 8 date(s) • Desk: 2.24.* • Refresh: 30s")

    # Mode banners
    pout.mode_banner("loop")

    # Existing bookings check
    print()
    pout.progress_inline("Checking existing bookings...")
    time.sleep(1)
    pout.clear_line()
    pout.success("Found 5 existing booking(s) - will skip these dates")

    # Round header
    pout.round_header(1, 3, 5)

    # Date 1 - Success
    pout.date_header("2025-11-27", 1, 3)
    pout.progress_inline("  Loading 2025-11-27 floor map...")
    time.sleep(0.5)
    pout.clear_line()
    pout.progress_inline("  Checking available desks...")
    time.sleep(0.5)
    pout.clear_line()
    pout.info("  Found 3 desk(s): 2.24.35, 2.24.28, 2.24.23")
    pout.info("  Priority: 2.24.35 (highest)")
    pout.progress_inline("  Detecting and clicking desk...")
    time.sleep(0.5)
    pout.clear_line()
    pout.progress_inline("  Booking 2.24.35...")
    time.sleep(0.5)
    pout.clear_line()
    pout.booking_result("2025-11-27", True, "2.24.35")

    # Date 2 - No seats
    pout.date_header("2025-11-21", 2, 3)
    pout.progress_inline("  Loading 2025-11-21 floor map...")
    time.sleep(0.5)
    pout.clear_line()
    pout.progress_inline("  Checking available desks...")
    time.sleep(0.5)
    pout.clear_line()
    pout.info("  No 2.24.* desks available")
    pout.booking_result("2025-11-21", False)

    # Date 3 - No seats
    pout.date_header("2025-11-14", 3, 3)
    pout.progress_inline("  Loading 2025-11-14 floor map...")
    time.sleep(0.5)
    pout.clear_line()
    pout.progress_inline("  Checking available desks...")
    time.sleep(0.5)
    pout.clear_line()
    pout.info("  No 2.24.* desks available")
    pout.booking_result("2025-11-14", False)

    # Waiting
    pout.waiting(30, "No available seats for any date")

    # Summary
    results = {
        "2025-11-27": True,
        "2025-11-21": False,
        "2025-11-14": False
    }
    existing = [
        "2025-10-29", "2025-11-05", "2025-11-12",
        "2025-11-19", "2025-11-20"
    ]
    pout.summary_table(results, existing)

    print("\n" + "="*70)
    print("This is how the new output will look!")
    print("="*70 + "\n")

if __name__ == "__main__":
    demo()
