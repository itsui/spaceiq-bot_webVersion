"""
Desk Position Mapper Tool

Maps all desk positions on the floor by clicking blue circles on a weekend date
when many desks are available. Saves the mapping to a cache file for fast lookups.

Usage:
    python map_desk_positions.py

This tool will:
1. Navigate to a Saturday/Sunday date with many available desks
2. Detect all blue circles using computer vision
3. Click each circle to read the desk code from popup
4. Save desk_code -> (x, y) mapping to config/desk_positions.json

Run this once to build the cache, then booking will be 10x faster!
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from config import Config


async def find_next_weekend_date():
    """Find the next Saturday or Sunday with available desks."""
    today = datetime.now().date()

    # Look ahead up to 4 weeks
    for days_ahead in range(0, 29):
        check_date = today + timedelta(days=days_ahead)

        # Saturday = 5, Sunday = 6
        if check_date.weekday() in [5, 6]:
            return check_date

    return None


async def map_desk_positions():
    """
    Map all desk positions by clicking all blue circles on a weekend date.
    """
    print("\n" + "=" * 70)
    print("         Desk Position Mapper Tool")
    print("=" * 70)
    print("\nThis tool will build a cache of desk positions for fast booking.")
    print("It will click all blue circles to identify desk locations.\n")

    # Find next weekend date
    target_date = await find_next_weekend_date()

    if not target_date:
        print("[ERROR] Could not find a weekend date in the next 4 weeks")
        return

    days_ahead = (target_date - datetime.now().date()).days
    date_str = target_date.strftime('%Y-%m-%d')
    day_name = target_date.strftime('%a, %b %d')

    print(f"Target date: {day_name} ({date_str})")
    print(f"Days ahead: {days_ahead}")
    print("=" * 70 + "\n")

    # Load config
    config_path = Path("config/booking_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)

    building = config.get("building", "LC")
    floor = config.get("floor", "2")

    print(f"Building: {building}")
    print(f"Floor: {floor}")
    print("\nStarting browser...\n")

    # Initialize browser
    session_manager = SessionManager(headless=False)  # Visible so you can see progress

    try:
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page)

        # Navigate to floor view
        print("[1/6] Navigating to floor view...")
        await booking_page.navigate_to_floor_view(building, floor)
        print("       ✓ Navigated\n")

        # Click Book Desk
        print("[2/6] Clicking 'Book Desk'...")
        await booking_page.click_book_desk_button()
        print("       ✓ Clicked\n")

        # Open date picker
        print("[3/6] Opening date picker...")
        await booking_page.open_date_picker()
        print("       ✓ Opened\n")

        # Select date
        print(f"[4/6] Selecting date ({day_name})...")
        await booking_page.select_date_from_calendar(days_ahead=days_ahead)
        print("       ✓ Selected\n")

        # Click Update
        print("[5/6] Clicking 'Update'...")
        await booking_page.click_update_button()
        print("       ✓ Updated\n")

        # Wait for floor map
        print("[6/6] Waiting for floor map...")
        await booking_page.wait_for_floor_map_to_load()
        await asyncio.sleep(7)  # Wait for SVG to fully render
        print("       ✓ Floor map loaded\n")

        # Take screenshot
        await booking_page.capture_screenshot("desk_mapping")
        print("📸 Screenshot saved\n")

        print("=" * 70)
        print("         Detecting Blue Circles")
        print("=" * 70 + "\n")

        # Detect blue circles using CV
        from src.utils.desk_detector import DeskDetector
        import os

        detector = DeskDetector()
        screenshot_files = sorted(
            Config.SCREENSHOTS_DIR.glob("desk_mapping_*.png"),
            key=os.path.getmtime,
            reverse=True
        )

        if not screenshot_files:
            print("[ERROR] Screenshot not found")
            return

        screenshot_path = str(screenshot_files[0])
        circles = detector.find_blue_circles(screenshot_path, debug=True)

        if not circles:
            print("[ERROR] No blue circles detected")
            return

        print(f"Found {len(circles)} blue circles\n")
        print("=" * 70)
        print("         Mapping Desk Positions")
        print("=" * 70 + "\n")

        # Click each circle and map position
        desk_positions = {}

        for i, (x, y) in enumerate(circles, 1):
            print(f"[{i}/{len(circles)}] Clicking circle at ({x}, {y})...", end=" ")

            try:
                # Click the circle
                await page.mouse.click(x, y)
                await asyncio.sleep(1.5)

                # Read popup
                popup = page.locator('td:has-text("Hoteling Desk")').first

                try:
                    await popup.wait_for(state='visible', timeout=3000)
                except:
                    print("❌ No popup")
                    continue

                try:
                    popup_text = await popup.text_content()
                except:
                    print("❌ Could not read popup")
                    continue

                # Extract desk code
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', popup_text)

                if match:
                    desk_code = match.group(1)
                    desk_positions[desk_code] = {"x": x, "y": y}
                    print(f"✓ {desk_code}")
                else:
                    print(f"❌ Could not extract desk code from: {popup_text}")

                # Close popup
                await booking_page.close_popup()

                # Wait for popup to be hidden
                try:
                    await popup.wait_for(state='hidden', timeout=2000)
                except:
                    pass

            except Exception as e:
                print(f"❌ Error: {e}")
                continue

        print(f"\n✓ Mapped {len(desk_positions)} unique desk positions\n")

        # Save to cache file
        cache_file = Path("config/desk_positions.json")

        cache_data = {
            "viewport": {"width": 1920, "height": 1080},
            "floor": floor,
            "building": building,
            "desk_positions": desk_positions,
            "last_updated": datetime.now().isoformat(),
            "mapping_date": date_str,
            "total_desks": len(desk_positions)
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        print("=" * 70)
        print("         Mapping Complete!")
        print("=" * 70)
        print(f"\nCache saved to: {cache_file}")
        print(f"Total desks mapped: {len(desk_positions)}")
        print(f"\nDesks found:")

        # Sort and display desks
        sorted_desks = sorted(desk_positions.keys())
        for i, desk in enumerate(sorted_desks, 1):
            pos = desk_positions[desk]
            print(f"  {i:2}. {desk} at ({pos['x']}, {pos['y']})")

        print("\n✓ Position cache is ready!")
        print("  Booking will now be 10x faster! ⚡\n")

    except Exception as e:
        print(f"\n[ERROR] Mapping failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await session_manager.close()


if __name__ == "__main__":
    print("\n🗺️  Starting Desk Position Mapper...\n")
    asyncio.run(map_desk_positions())
