"""
Quick Test Script for SpaceIQ Bot

Performs a dry-run test to validate each step without completing the booking.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from config import Config
from src.auth.session_manager import SessionManager
from src.pages.spaceiq_booking_page import SpaceIQBookingPage


async def test_each_step():
    """Test each step of the workflow individually"""

    print("\n" + "=" * 70)
    print("SpaceIQ Bot - Step-by-Step Test")
    print("=" * 70)
    print("\nThis will test each step individually without completing booking.")
    print("Watch the browser window to see each action.\n")
    print("=" * 70 + "\n")

    if not Config.AUTH_STATE_FILE.exists():
        print("❌ Authentication file not found!")
        print("Run: python src/auth/capture_session.py")
        return

    try:
        session_manager = SessionManager()
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page)

        # Test 1: Navigation
        print("\n" + "-" * 70)
        print("TEST 1: Navigation to floor view")
        print("-" * 70)
        await booking_page.navigate_to_floor_view("LC", "2")
        await asyncio.sleep(2)
        print("✅ Navigation successful")

        # Test 2: Book Desk button
        print("\n" + "-" * 70)
        print("TEST 2: Click 'Book Desk' button")
        print("-" * 70)
        input("Press Enter to test clicking 'Book Desk' button...")
        try:
            await booking_page.click_book_desk_button()
            print("✅ 'Book Desk' button clicked")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Failed to click 'Book Desk': {e}")
            await booking_page.capture_screenshot("test_book_desk_failed")

        # Test 3: Date picker
        print("\n" + "-" * 70)
        print("TEST 3: Open date picker")
        print("-" * 70)
        input("Press Enter to test opening date picker...")
        try:
            await booking_page.open_date_picker()
            print("✅ Date picker opened")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Failed to open date picker: {e}")
            await booking_page.capture_screenshot("test_date_picker_failed")

        # Test 4: Select date
        print("\n" + "-" * 70)
        print("TEST 4: Select date from calendar")
        print("-" * 70)
        input("Press Enter to test selecting tomorrow's date...")
        try:
            await booking_page.select_date_from_calendar(days_ahead=1)
            print("✅ Date selected")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Failed to select date: {e}")
            await booking_page.capture_screenshot("test_date_select_failed")

        # Test 5: Update button
        print("\n" + "-" * 70)
        print("TEST 5: Click 'Update' button")
        print("-" * 70)
        input("Press Enter to test clicking 'Update'...")
        try:
            await booking_page.click_update_button()
            print("✅ 'Update' button clicked")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Failed to click 'Update': {e}")
            await booking_page.capture_screenshot("test_update_failed")

        # Test 6: Floor map load
        print("\n" + "-" * 70)
        print("TEST 6: Wait for floor map to load")
        print("-" * 70)
        try:
            await booking_page.wait_for_floor_map_to_load()
            print("✅ Floor map loaded")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Floor map didn't load: {e}")
            await booking_page.capture_screenshot("test_map_failed")

        # Test 7: Click desk (without completing)
        print("\n" + "-" * 70)
        print("TEST 7: Click available desk on map")
        print("-" * 70)
        print("⚠️  This will attempt to click a desk but NOT complete booking")
        input("Press Enter to test desk selection...")
        try:
            await booking_page.click_available_desk_on_map()
            print("✅ Desk clicked")
            await asyncio.sleep(2)

            # Check if popup appeared
            popup_appeared = await booking_page.verify_desk_popup_appeared()
            if popup_appeared:
                print("✅ Desk info popup appeared")
                desk_info = await booking_page.get_desk_info_from_popup()
                if desk_info:
                    print(f"   Desk: {desk_info.get('desk_name', 'Unknown')}")
            else:
                print("⚠️  Desk popup didn't appear")

        except Exception as e:
            print(f"❌ Failed to click desk: {e}")
            await booking_page.capture_screenshot("test_desk_click_failed")

        # Summary
        print("\n" + "=" * 70)
        print("Test Complete!")
        print("=" * 70)
        print("\n⚠️  NOTE: Booking was NOT completed (didn't click 'Book Now')")
        print("\nCheck screenshots in screenshots/ folder for any failures.")
        print("\nIf all tests passed, run: python main_spaceiq.py")
        print("=" * 70 + "\n")

        input("Press Enter to close browser...")

        await session_manager.close()

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n💡 This is a step-by-step test that won't complete the booking.")
    print("You'll be prompted before each step.\n")

    asyncio.run(test_each_step())
