"""
Test Position Cache and Existing Bookings Features

This script tests:
1. Position cache loading and lookup
2. Existing bookings fetch from "My Bookings" modal

Usage:
    python test_new_features.py
"""

import asyncio
import json
from pathlib import Path
from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager


async def test_position_cache():
    """Test 1: Position Cache"""
    print("\n" + "=" * 70)
    print("         TEST 1: POSITION CACHE")
    print("=" * 70 + "\n")

    cache_file = Path("config/desk_positions.json")

    if not cache_file.exists():
        print("❌ FAIL: Cache file does not exist")
        print(f"   Expected location: {cache_file}")
        print(f"   Run: python map_desk_positions.py")
        return False

    print(f"✓ Cache file exists: {cache_file}")

    # Load cache
    with open(cache_file, 'r') as f:
        cache_data = json.load(f)

    total_desks = cache_data.get("total_desks", 0)
    viewport = cache_data.get("viewport", {})
    last_updated = cache_data.get("last_updated", "Unknown")
    desk_positions = cache_data.get("desk_positions", {})

    print(f"✓ Total desks cached: {total_desks}")
    print(f"✓ Viewport: {viewport['width']}x{viewport['height']}")
    print(f"✓ Last updated: {last_updated}")

    # Show some sample desks
    print(f"\nSample cached desk positions:")
    sample_desks = list(desk_positions.items())[:5]
    for desk_code, coords in sample_desks:
        print(f"  • {desk_code} → ({coords['x']}, {coords['y']})")

    if total_desks > 50:
        print(f"\n✅ PASS: Cache looks good! ({total_desks} desks)")
        return True
    else:
        print(f"\n⚠️  WARNING: Only {total_desks} desks cached (expected 50+)")
        print("   Consider rebuilding cache on a weekend date")
        return True


async def test_existing_bookings():
    """Test 2: Existing Bookings Check"""
    print("\n" + "=" * 70)
    print("         TEST 2: EXISTING BOOKINGS CHECK")
    print("=" * 70 + "\n")

    print("Opening browser to check existing bookings...")
    print("(This will open the 'My Bookings' modal)\n")

    session_manager = SessionManager(headless=False)

    try:
        # Initialize browser
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page)

        # Navigate to floor view
        print("[1/2] Navigating to floor view...")
        await booking_page.navigate_to_floor_view("LC", "2")
        print("      ✓ Navigated\n")

        # Get existing bookings
        print("[2/2] Fetching existing bookings...")
        existing_bookings = await booking_page.get_existing_bookings()

        if existing_bookings:
            print(f"\n✅ PASS: Found {len(existing_bookings)} existing booking(s):")
            for i, date in enumerate(existing_bookings, 1):
                print(f"  {i}. {date}")
        else:
            print("\n✅ PASS: No existing bookings found")
            print("  (This is normal if you haven't booked any desks yet)")

        print("\n✓ Existing bookings check is working!")

        await asyncio.sleep(3)  # Let you see the result

        return True

    except Exception as e:
        print(f"\n❌ FAIL: Error checking existing bookings: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await session_manager.close()


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("         TESTING SPACEIQ BOT FEATURES")
    print("=" * 70)

    # Test 1: Position Cache
    cache_ok = await test_position_cache()

    # Test 2: Existing Bookings
    bookings_ok = await test_existing_bookings()

    # Summary
    print("\n" + "=" * 70)
    print("         TEST SUMMARY")
    print("=" * 70)
    print(f"\n1. Position Cache:       {'✅ PASS' if cache_ok else '❌ FAIL'}")
    print(f"2. Existing Bookings:    {'✅ PASS' if bookings_ok else '❌ FAIL'}")

    if cache_ok and bookings_ok:
        print("\n🎉 All tests passed! Your bot is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("\n🧪 Starting feature tests...\n")
    asyncio.run(main())
