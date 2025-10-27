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
import sys
import traceback

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from src.utils.file_logger import setup_file_logger
from src.utils.console_logger import start_console_logging, stop_console_logging
from config import Config


async def find_next_weekend_date():
    """Find the next Sunday (preferred) or Saturday with available desks."""
    today = datetime.now().date()

    # Look ahead up to 4 weeks
    # First, try to find a Sunday (weekday = 6)
    for days_ahead in range(0, 29):
        check_date = today + timedelta(days=days_ahead)

        # Sunday = 6 (preferred - more available desks)
        if check_date.weekday() == 6:
            return check_date

    # If no Sunday found, try Saturday
    for days_ahead in range(0, 29):
        check_date = today + timedelta(days=days_ahead)

        # Saturday = 5
        if check_date.weekday() == 5:
            return check_date

    return None


async def map_desk_positions():
    """
    Map all desk positions by clicking all blue circles on a weekend date.
    """
    # Setup logging
    logger, log_file = setup_file_logger()
    console_log_file, console_logger = start_console_logging()

    logger.info("=" * 70)
    logger.info("Desk Position Mapper Tool Started")
    logger.info("=" * 70)

    print("\n" + "=" * 70)
    print("         Desk Position Mapper Tool")
    print("=" * 70)
    print("\nThis tool will build a cache of desk positions for fast booking.")
    print("It will click all blue circles to identify desk locations.")
    print(f"\nLog file: {log_file}")
    print(f"Console log: {console_log_file}\n")

    # Find next weekend date
    target_date = await find_next_weekend_date()

    if not target_date:
        msg = "Could not find a weekend date in the next 4 weeks"
        print(f"[ERROR] {msg}")
        logger.error(msg)
        stop_console_logging(console_logger)
        return

    days_ahead = (target_date - datetime.now().date()).days
    date_str = target_date.strftime('%Y-%m-%d')
    day_name = target_date.strftime('%a, %b %d')

    logger.info(f"Target date: {day_name} ({date_str})")
    logger.info(f"Days ahead: {days_ahead}")

    print(f"Target date: {day_name} ({date_str})")
    print(f"Days ahead: {days_ahead}")
    print("=" * 70 + "\n")

    # Load config
    config_path = Path("config/booking_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)

    building = config.get("building", "LC")
    floor = config.get("floor", "2")

    logger.info(f"Building: {building}, Floor: {floor}")

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
        from src.vision.desk_detector import DeskDetector
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
            msg = "No blue circles detected"
            print(f"[ERROR] {msg}")
            logger.error(msg)
            return

        logger.info(f"Found {len(circles)} blue circles at coordinates: {circles}")

        print(f"Found {len(circles)} blue circles\n")
        print("=" * 70)
        print("         Mapping Desk Positions")
        print("=" * 70 + "\n")

        # Click each circle and map position
        desk_positions = {}
        logger.info("Starting to map desk positions by clicking circles")

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
                except Exception as popup_error:
                    print("❌ No popup")
                    logger.warning(f"Circle {i} at ({x}, {y}) - No popup appeared: {popup_error}")
                    continue

                try:
                    popup_text = await popup.text_content()
                except Exception as text_error:
                    print("❌ Could not read popup")
                    logger.warning(f"Circle {i} at ({x}, {y}) - Could not read popup text: {text_error}")
                    continue

                # Extract desk code
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', popup_text)

                if match:
                    desk_code = match.group(1)
                    desk_positions[desk_code] = {"x": x, "y": y}
                    print(f"✓ {desk_code}")
                    logger.info(f"Circle {i} at ({x}, {y}) - Mapped to desk {desk_code}")
                else:
                    print(f"❌ Could not extract desk code from: {popup_text}")
                    logger.warning(f"Circle {i} at ({x}, {y}) - Could not extract desk code from: {popup_text}")

                # Close popup
                await booking_page.close_popup(logger=logger)

                # Wait for popup to be hidden
                try:
                    await popup.wait_for(state='hidden', timeout=2000)
                except:
                    pass

            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Circle {i} at ({x}, {y}) - Error: {e}")
                logger.error(traceback.format_exc())
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

        logger.info(f"Cache saved to: {cache_file}")
        logger.info(f"Total desks mapped: {len(desk_positions)}")
        logger.info("Position cache is ready!")

        print("\n✓ Position cache is ready!")
        print("  Booking will now be 10x faster! ⚡\n")

    except Exception as e:
        error_msg = f"Mapping failed: {e}"
        print(f"\n[ERROR] {error_msg}")
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        traceback.print_exc()

    finally:
        await session_manager.close()
        stop_console_logging(console_logger)
        print(f"\n[INFO] Logs saved to:")
        print(f"  Console: {console_log_file}")
        print(f"  Details: {log_file}\n")


if __name__ == "__main__":
    print("\n🗺️  Starting Desk Position Mapper...\n")
    asyncio.run(map_desk_positions())
