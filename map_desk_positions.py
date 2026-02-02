"""
Desk Position Mapper Tool

Maps all desk positions on the floor by clicking blue circles on a weekend date
when many desks are available. Saves the mapping to a cache file for fast lookups.

Usage:
    python map_desk_positions.py [--user-id USER_ID]

    --user-id: User ID from database (default: 1)

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
import argparse

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from src.utils.file_logger import setup_file_logger
from src.utils.console_logger import start_console_logging, stop_console_logging
from config import Config


async def find_next_weekend_date():
    """Find the next Sunday (preferred) or Saturday with available desks."""
    today = datetime.now().date()

    # Look ahead 1-29 days (tomorrow through 29 days from now)
    # Start from 1 (tomorrow) because we can only book FUTURE dates, not today
    # End at 30 (exclusive) to cover 1-29 days ahead (SpaceIQ 29-day booking limit)

    # First, try to find a Sunday (weekday = 6)
    for days_ahead in range(1, 30):
        check_date = today + timedelta(days=days_ahead)

        # Sunday = 6 (preferred - more available desks)
        if check_date.weekday() == 6:
            return check_date

    # If no Sunday found, try Saturday
    for days_ahead in range(1, 30):
        check_date = today + timedelta(days=days_ahead)

        # Saturday = 5
        if check_date.weekday() == 5:
            return check_date

    return None


async def map_desk_positions(user_id: int = 1, web_mode: bool = False, progress_callback=None):
    """
    Map all desk positions by clicking all blue circles on a weekend date.

    Args:
        user_id: User ID to load session from database (default: 1)
        web_mode: If True, raise exception on session expiry instead of waiting for manual login
        progress_callback: Optional callback function to report progress updates

    Returns:
        Dictionary with 'total_desks', 'permanent_desks', and 'success' keys
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
    print(f"User ID: {user_id}\n")

    # Helper function to report progress
    def report_progress(message):
        """Send progress updates to callback and console"""
        if progress_callback:
            progress_callback(message)
        logger.info(message)

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
    print("\nLoading session from database...\n")

    # Load session from database (requires Flask app context)
    session_data = None
    try:
        from app import app
        from models import SpaceIQSession
        from src.utils.auth_encryption import decrypt_data

        with app.app_context():
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()
            if not spaceiq_session or not spaceiq_session.session_data or not spaceiq_session.is_valid:
                print("\n" + "=" * 70)
                print("❌ NO VALID SESSION FOUND")
                print("=" * 70)
                print(f"\nNo authentication session found for user {user_id}")
                print("\nPlease authenticate first:")
                print("  1. Go to http://localhost:5000/auth/auto")
                print("  2. Complete SSO + MFA authentication")
                print("  3. Run this tool again")
                print("\n" + "=" * 70 + "\n")
                logger.error(f"No valid session found for user {user_id}")
                stop_console_logging(console_logger)

                # Optionally open browser
                try:
                    import webbrowser
                    print("Opening authentication page in your browser...")
                    webbrowser.open('http://localhost:5000/auth/auto')
                except:
                    pass

                return

            # Decrypt session data
            try:
                decrypted_json = decrypt_data(spaceiq_session.session_data)
                session_data = json.loads(decrypted_json)
            except Exception as decrypt_error:
                print("\n" + "=" * 70)
                print("❌ SESSION DECRYPTION FAILED")
                print("=" * 70)
                print(f"\nFailed to decrypt session for user {user_id}")
                print(f"Error: {decrypt_error}")
                print("\nThis usually means the session was created on a different machine")
                print("or the session data is corrupted.")
                print("\nPlease re-authenticate:")
                print("  1. Go to http://localhost:5000/auth/auto")
                print("  2. Complete SSO + MFA authentication")
                print("  3. Run this tool again")
                print("\n" + "=" * 70 + "\n")
                logger.error(f"Failed to decrypt session for user {user_id}: {decrypt_error}")
                stop_console_logging(console_logger)

                # Optionally open browser
                try:
                    import webbrowser
                    print("Opening authentication page in your browser...")
                    webbrowser.open('http://localhost:5000/auth/auto')
                except:
                    pass

                return

            # Session successfully decrypted
            cookies = session_data.get('cookies', [])
            print(f"✓ Loaded session with {len(cookies)} cookies\n")
            logger.info(f"Loaded session with {len(cookies)} cookies")

    except Exception as e:
        print(f"[ERROR] Failed to load session from database: {e}")
        logger.error(f"Failed to load session: {e}")
        logger.error(traceback.format_exc())
        stop_console_logging(console_logger)
        return

    # Run headless when in web mode
    headless_mode = web_mode
    if not headless_mode:
        print("Starting browser...\n")

    # Initialize browser with pre-loaded session data (avoids database access)
    session_manager = SessionManager(headless=headless_mode, user_id=user_id, session_data=session_data)

    try:
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page, web_mode=web_mode)

        # Navigate to floor view
        report_progress("🔄 Navigating to floor view...")
        await booking_page.navigate_to_floor_view(building, floor)
        report_progress("✓ Navigated to floor view")

        # Click Book Desk
        report_progress("🔄 Clicking 'Book Desk' button...")
        await booking_page.click_book_desk_button()
        report_progress("✓ Book Desk button clicked")

        # Open date picker
        report_progress("🔄 Opening date picker...")
        await booking_page.open_date_picker()
        report_progress("✓ Date picker opened")

        # Select date
        report_progress(f"🔄 Selecting date ({day_name})...")
        await booking_page.select_date_from_calendar(days_ahead=days_ahead)
        report_progress(f"✓ Date selected: {day_name}")

        # Click Update
        report_progress("🔄 Applying date filter...")
        await booking_page.click_update_button()
        report_progress("✓ Date filter applied")

        # Wait for floor map
        report_progress("🔄 Loading floor map...")
        await booking_page.wait_for_floor_map_to_load()
        await asyncio.sleep(7)  # Wait for SVG to fully render
        report_progress("✓ Floor map loaded")

        # Take screenshot
        await booking_page.capture_screenshot("desk_mapping")
        report_progress("📸 Screenshot captured")

        report_progress("🔍 Detecting available desks using computer vision...")

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
            msg = "Screenshot not found"
            report_progress(f"❌ {msg}")
            return

        screenshot_path = str(screenshot_files[0])
        circles = detector.find_blue_circles(screenshot_path, debug=True)

        if not circles:
            msg = "No blue circles detected"
            report_progress(f"❌ {msg}")
            logger.error(msg)
            return

        logger.info(f"Found {len(circles)} blue circles at coordinates: {circles}")
        report_progress(f"✓ Found {len(circles)} available desks to map")
        report_progress(f"🗺️ Starting desk mapping ({len(circles)} desks)...")

        # Click each circle and map position
        desk_positions = {}
        logger.info("Starting to map desk positions by clicking circles")

        for i, (x, y) in enumerate(circles, 1):
            try:
                # Click the circle
                await page.mouse.click(x, y)
                await asyncio.sleep(1.5)

                # Read popup
                popup = page.locator('td:has-text("Hoteling Desk")').first

                try:
                    await popup.wait_for(state='visible', timeout=3000)
                except Exception as popup_error:
                    report_progress(f"⚠️ Circle {i}/{len(circles)} - No popup appeared")
                    logger.warning(f"Circle {i} at ({x}, {y}) - No popup appeared: {popup_error}")
                    continue

                try:
                    popup_text = await popup.text_content()
                except Exception as text_error:
                    report_progress(f"⚠️ Circle {i}/{len(circles)} - Could not read popup")
                    logger.warning(f"Circle {i} at ({x}, {y}) - Could not read popup text: {text_error}")
                    continue

                # Extract desk code
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', popup_text)

                if match:
                    desk_code = match.group(1)
                    desk_positions[desk_code] = {"x": x, "y": y}
                    report_progress(f"✓ Mapped desk {desk_code} ({i}/{len(circles)})")
                    logger.info(f"Circle {i} at ({x}, {y}) - Mapped to desk {desk_code}")
                else:
                    report_progress(f"⚠️ Circle {i}/{len(circles)} - Could not extract desk code")
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

        # Detect permanent desks (desks that don't appear in sidebar or blue circles)
        print("=" * 70)
        print("         Detecting Permanent Desks")
        print("=" * 70 + "\n")

        permanent_desks_detected = []

        # Get all desk prefixes to check (e.g., ["2.24", "2.07", "2.23"])
        desk_prefixes_to_check = set()
        for desk_code in desk_positions.keys():
            prefix = '.'.join(desk_code.split('.')[:2])  # Get "2.24" from "2.24.11"
            desk_prefixes_to_check.add(prefix)

        print(f"Checking desk prefixes: {sorted(desk_prefixes_to_check)}\n")

        for desk_prefix in sorted(desk_prefixes_to_check):
            print(f"Checking {desk_prefix}.* desks...")

            # Get available desks from sidebar
            available_from_sidebar = await booking_page.get_available_desks_from_sidebar(
                desk_prefix=desk_prefix,
                logger=logger,
                locked_desks=[]  # Don't filter locked desks, we want to see all
            )

            # Get desks detected from blue circles
            detected_from_circles = [desk for desk in desk_positions.keys() if desk.startswith(desk_prefix)]

            # All possible desks in this range (1-70)
            all_possible = [f"{desk_prefix}.{i:02d}" for i in range(1, 71)]

            # Permanent desks = all possible - (available in sidebar + detected in circles)
            desks_that_exist = set(available_from_sidebar) | set(detected_from_circles)
            permanent_for_prefix = [desk for desk in all_possible if desk not in desks_that_exist]

            if permanent_for_prefix:
                permanent_desks_detected.extend(permanent_for_prefix)
                print(f"  Found {len(permanent_for_prefix)} permanent desks: {permanent_for_prefix[:5]}{'...' if len(permanent_for_prefix) > 5 else ''}")
                logger.info(f"Permanent desks for {desk_prefix}: {permanent_for_prefix}")
            else:
                print(f"  No permanent desks detected")

        print(f"\n✓ Total permanent desks detected: {len(permanent_desks_detected)}\n")

        # Update user's locked_desks in database
        if permanent_desks_detected:
            print("Updating database with permanent desks...")
            try:
                from app import app
                from models import BotConfig, db

                with app.app_context():
                    bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                    if bot_config:
                        bot_config.set_locked_desks(permanent_desks_detected)
                        db.session.commit()
                        print(f"✓ Updated user {user_id}'s permanent desks in database\n")
                        logger.info(f"Updated locked_desks for user {user_id}: {len(permanent_desks_detected)} desks")
                    else:
                        print(f"⚠️  No bot config found for user {user_id} - permanent desks not saved\n")
                        logger.warning(f"No bot config found for user {user_id}")
            except Exception as e:
                print(f"⚠️  Failed to update database: {e}\n")
                logger.error(f"Failed to update locked_desks: {e}")

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

        # Return results for web UI
        return {
            'success': True,
            'total_desks': len(desk_positions),
            'permanent_desks': len(permanent_desks_detected),
            'console_log': str(console_log_file),
            'detail_log': str(log_file)
        }

    except Exception as e:
        error_msg = f"Mapping failed: {e}"
        print(f"\n[ERROR] {error_msg}")
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        traceback.print_exc()

        # Re-raise exception in web mode so it can be handled by the caller
        if web_mode:
            await session_manager.close()
            stop_console_logging(console_logger)
            raise

    finally:
        await session_manager.close()
        stop_console_logging(console_logger)
        print(f"\n[INFO] Logs saved to:")
        print(f"  Console: {console_log_file}")
        print(f"  Details: {log_file}\n")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Map desk positions for SpaceIQ bot')
    parser.add_argument('--user-id', type=int, default=1,
                        help='User ID to load session from database (default: 1)')

    args = parser.parse_args()

    print("\n🗺️  Starting Desk Position Mapper...\n")
    asyncio.run(map_desk_positions(user_id=args.user_id))
