"""
Multi-Date Booking Workflow

Reads dates from config/booking_config.json and tries to book all of them.
Removes successfully booked dates from the config file.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from src.utils.file_logger import setup_file_logger


class MultiDateBookingWorkflow:
    """
    Tries to book multiple dates from config file.

    Strategy:
    1. Load dates from config/booking_config.json
    2. For each date:
       - Try to book a desk matching prefix
       - If successful, remove date from config
       - If failed, keep trying with refreshes
    3. Continue until all dates are booked
    """

    def __init__(self, refresh_interval: int = 30, max_attempts_per_date: int = 10, polling_mode: bool = False, headless: bool = False):
        self.config_path = Path(__file__).parent.parent.parent / "config" / "booking_config.json"
        self.refresh_interval = refresh_interval
        self.max_attempts_per_date = max_attempts_per_date
        self.polling_mode = polling_mode
        self.headless = headless
        self.session_manager = SessionManager(headless=headless)

        # Setup file logging
        self.logger, self.log_file = setup_file_logger()
        self.logger.info("=" * 70)
        self.logger.info("Multi-Date Booking Workflow Initialized")
        self.logger.info("=" * 70)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self, config: Dict[str, Any]):
        """Save configuration back to JSON file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def remove_date_from_config(self, date_str: str):
        """Move a successfully booked date to the booked_dates list."""
        config = self.load_config()
        if date_str in config.get("dates_to_try", []):
            config["dates_to_try"].remove(date_str)

            # Add to booked_dates history
            if "booked_dates" not in config:
                config["booked_dates"] = []
            config["booked_dates"].append(date_str)

            self.save_config(config)
            msg = f"Moved {date_str} to booked_dates (successfully booked)"
            print(f"\n[INFO] {msg}")
            self.logger.info(msg)

    async def run(self) -> Dict[str, bool]:
        """
        Execute multi-date booking workflow.

        Returns:
            Dictionary mapping date -> success status
        """

        # Load config
        config = self.load_config()
        building = config.get("building", "LC")
        floor = config.get("floor", "2")
        desk_prefix = config.get("desk_preferences", {}).get("prefix", "2.24")

        # ALWAYS calculate dates fresh from calendar (ignore config dates)
        # This ensures we try every date, even if already marked as "booked"
        # Prevents false positives from removing dates prematurely
        today = datetime.now().date()
        furthest_date = today + timedelta(weeks=4, days=1)  # 29 days

        dates_to_try = []
        current_date = today

        while current_date <= furthest_date:
            # Only Wed (2) and Thu (3)
            if current_date.weekday() in [2, 3]:
                # Only include dates that are not in the past
                if current_date >= today:
                    dates_to_try.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        # Sort from furthest to closest (most available first)
        dates_to_try.sort(reverse=True)

        if not dates_to_try:
            print("\n[WARNING] No Wed/Thu dates found in the next 29 days")
            return {}

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("Multi-Date Booking Workflow")
        self.logger.info("=" * 70)
        self.logger.info(f"Building: {building}, Floor: {floor}")
        self.logger.info(f"Desk Prefix: {desk_prefix}.*")
        self.logger.info(f"Dates to book: {dates_to_try}")
        self.logger.info(f"Refresh Interval: {self.refresh_interval}s")
        self.logger.info(f"Max Attempts per Date: {self.max_attempts_per_date}")
        self.logger.info(f"Log File: {self.log_file}")
        self.logger.info("=" * 70)
        self.logger.info("")

        print("\n" + "=" * 70)
        print("         SpaceIQ Multi-Date Booking Bot")
        print("=" * 70)
        print(f"\nDates to book: {', '.join(dates_to_try)}")
        print(f"Desk prefix: {desk_prefix}.*")
        print(f"Max attempts per date: {self.max_attempts_per_date}")
        print(f"Refresh interval: {self.refresh_interval}s")
        print("=" * 70 + "\n")

        results = {}

        try:
            # Validate session first (especially important for headless mode)
            if self.headless:
                print("[INFO] Headless mode requested - validating session first...")
                from src.auth.session_validator import validate_and_refresh_session

                session_valid, use_headless = await validate_and_refresh_session(force_headless=True)

                if not session_valid:
                    print("\n[ERROR] Session validation failed. Cannot continue.")
                    return {}

                # Update headless setting based on validation result
                self.headless = use_headless
                self.session_manager.headless = use_headless

            # Initialize session
            context = await self.session_manager.initialize()
            page = await context.new_page()
            booking_page = SpaceIQBookingPage(page)

            # Polling loop: keep trying until at least one date is booked (if polling_mode enabled)
            round_num = 1
            while True:
                # ALWAYS recalculate dates from calendar (don't trust config)
                # This ensures we verify every date every round
                today_now = datetime.now().date()
                furthest_date_now = today_now + timedelta(weeks=4, days=1)

                dates_to_try_now = []
                current_date_check = today_now

                while current_date_check <= furthest_date_now:
                    if current_date_check.weekday() in [2, 3]:
                        if current_date_check >= today_now:
                            dates_to_try_now.append(current_date_check.strftime("%Y-%m-%d"))
                    current_date_check += timedelta(days=1)

                dates_to_try_now.sort(reverse=True)

                if not dates_to_try_now:
                    print("\n[INFO] No more future Wed/Thu dates to try.")
                    break

                if self.polling_mode and round_num > 1:
                    print("\n" + "=" * 70)
                    print(f"         POLLING ROUND {round_num}")
                    print("=" * 70)
                    print(f"Trying {len(dates_to_try_now)} date(s)...")
                    print(f"Dates: {', '.join(dates_to_try_now)}")
                    print("=" * 70 + "\n")

                round_results = {}

                # Try each date once, move to next if no seats available
                for date_str in dates_to_try_now:
                    print("\n" + "=" * 70)
                    print(f"         TRYING DATE: {date_str}")
                    print("=" * 70 + "\n")

                    # Parse date
                    target_date = datetime.strptime(date_str, '%Y-%m-%d')
                    days_ahead = (target_date.date() - datetime.now().date()).days

                    # Try booking this date (single attempt to check availability)
                    success = await self._try_booking_date(
                        booking_page=booking_page,
                        page=page,
                        date_str=date_str,
                        days_ahead=days_ahead,
                        building=building,
                        floor=floor,
                        desk_prefix=desk_prefix
                    )

                    round_results[date_str] = success
                    results[date_str] = success

                    if success:
                        print(f"\n[SUCCESS] Booked desk for {date_str}!")
                        self.logger.info(f"Successfully booked {date_str}")

                        # Update config for record-keeping (but we'll still try this date again next round to verify)
                        self.remove_date_from_config(date_str)
                    else:
                        # Could be: no seats available, already booked, or date disabled
                        print(f"\n[SKIPPED] {date_str} - No available desks (may already be booked)")
                        self.logger.info(f"No available desks for {date_str}")

                # Check if we should continue polling
                any_booked = any(round_results.values())

                if not self.polling_mode:
                    # Single pass mode - exit after one round
                    break

                if any_booked:
                    # At least one date was booked
                    # Continue to next round to verify all dates again
                    print("\n[INFO] At least one booking successful! Continuing to verify all dates...")
                    round_num += 1
                    continue

                # No dates booked this round - wait and try again
                print("\n" + "=" * 70)
                print(f"         ROUND {round_num} COMPLETE - NO BOOKINGS")
                print("=" * 70)
                print(f"No seats available for any date. Waiting {self.refresh_interval}s...")
                print("People may cancel - checking again soon!")
                print("=" * 70 + "\n")

                await asyncio.sleep(self.refresh_interval)
                round_num += 1

            # Final summary
            print("\n" + "=" * 70)
            print("         BOOKING SUMMARY")
            print("=" * 70)
            booked_count = sum(1 for success in results.values() if success)
            skipped_count = sum(1 for success in results.values() if not success)
            print(f"Total dates processed: {len(results)}")
            print(f"Successfully booked: {booked_count}")
            print(f"Skipped (no seats/disabled): {skipped_count}")
            print("-" * 70)
            for date_str, success in results.items():
                status = "[BOOKED]" if success else "[SKIPPED]"
                print(f"{status} {date_str}")
            print("=" * 70 + "\n")

            return results

        except Exception as e:
            print(f"\n[ERROR] Error during multi-date booking: {e}")
            import traceback
            traceback.print_exc()
            return results

        finally:
            await self.session_manager.close()

    async def _try_booking_date(
        self,
        booking_page: SpaceIQBookingPage,
        page,
        date_str: str,
        days_ahead: int,
        building: str,
        floor: str,
        desk_prefix: str
    ) -> bool:
        """
        Try booking a specific date.

        Strategy:
        1. Check if desks available for this date
        2. If NO desks → return False immediately (skip to next date)
        3. If desks found → try to book with retries (for click failures)

        Returns:
            True if successfully booked, False if no desks available or booking failed
        """

        try:
            # Step 1: Navigate
            print("[1/9] Navigating to floor view...")
            await booking_page.navigate_to_floor_view(building, floor)

            # Step 2: Click Book Desk
            print("[2/9] Clicking 'Book Desk'...")
            await booking_page.click_book_desk_button()

            # Step 3: Open date picker
            print("[3/9] Opening date picker...")
            await booking_page.open_date_picker()

            # Step 4: Select date
            print(f"[4/9] Selecting date ({date_str})...")
            try:
                await booking_page.select_date_from_calendar(days_ahead=days_ahead)
            except Exception as e:
                if "disabled" in str(e).lower() or "beyond booking window" in str(e).lower():
                    print(f"[SKIPPED] Date is beyond booking window (grayed out)")
                    self.logger.info(f"Date {date_str} is disabled - beyond booking window")
                    return False
                else:
                    raise  # Re-raise if it's a different error

            # Step 5: Click Update
            print("[5/9] Clicking 'Update'...")
            await booking_page.click_update_button()

            # Step 6: Wait for floor map
            print("[6/9] Waiting for floor map...")
            await booking_page.wait_for_floor_map_to_load()

            # Wait for SVG elements to render
            await asyncio.sleep(7)

            # Take screenshot for CV detection
            await booking_page.capture_screenshot("floor_map_loaded")

            # Step 7: Get available desks from sidebar
            print(f"[7/9] Finding available {desk_prefix}.* desks...")
            available_desks = await booking_page.get_available_desks_from_sidebar(
                desk_prefix=desk_prefix,
                logger=self.logger
            )

            if not available_desks:
                print(f"[INFO] No available desks found for {date_str}")
                return False  # Skip to next date immediately

            print(f"[INFO] Found {len(available_desks)} available desk(s): {available_desks}")

            # Step 7.5: Sort by priority (if configured)
            config = self.load_config()
            priority_config = config.get("desk_preferences", {}).get("priority_ranges", [])

            if priority_config:
                from src.utils.desk_priority import sort_desks_by_priority, explain_desk_priorities

                # Sort desks by priority
                sorted_desks = sort_desks_by_priority(available_desks, priority_config)

                print(f"[INFO] Sorted desks by priority:")
                priority_explanation = explain_desk_priorities(sorted_desks, priority_config)
                for line in priority_explanation.split('\n'):
                    if line.strip():
                        print(f"       {line}")

                available_desks = sorted_desks

            # Step 8: Use CV to find and click blue circles
            print(f"[8/9] Using computer vision to detect and click available desks...")

            found_desk = await booking_page.find_and_click_available_desks(
                available_desks=available_desks,
                logger=self.logger
            )

            if not found_desk:
                print(f"[FAILED] Could not click any available desks")
                return False

            # Desk was found and clicked, popup is open (verified by find_and_click_available_desks)
            print(f"[SUCCESS] Successfully clicked desk {found_desk}")

            # Step 9: Click Book Now
            print("[9/9] Clicking 'Book Now'...")
            await booking_page.click_book_now_in_popup()

            # Verify success
            await asyncio.sleep(2)
            success = await booking_page.verify_booking_success()

            if success:
                print(f"[SUCCESS] Booked desk {found_desk} for {date_str}!")
                await booking_page.capture_screenshot(f"booking_success_{date_str}")
                return True
            else:
                print(f"[FAILED] Booking verification failed")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to book {date_str}: {e}")
            self.logger.error(f"Failed to book {date_str}: {e}")
            return False


async def run_multi_date_booking(
    refresh_interval: int = 30,
    max_attempts_per_date: int = 10,
    polling_mode: bool = False,
    headless: bool = False
) -> Dict[str, bool]:
    """
    Quick helper to run multi-date booking.

    Reads dates from config/booking_config.json and tries to book all of them.
    Successfully booked dates are removed from the config file.

    Args:
        refresh_interval: Seconds between refresh attempts (default: 30)
        max_attempts_per_date: Maximum attempts per date (default: 10)
        polling_mode: If True, keeps trying all dates until at least one is booked (default: False)
        headless: If True, runs browser in headless mode (default: False)

    Returns:
        Dictionary mapping date -> success status

    Example:
        from src.workflows.multi_date_booking import run_multi_date_booking
        # Single pass
        results = await run_multi_date_booking(refresh_interval=30, max_attempts_per_date=10)
        # Polling mode (keeps trying)
        results = await run_multi_date_booking(refresh_interval=30, polling_mode=True)
    """
    workflow = MultiDateBookingWorkflow(
        refresh_interval=refresh_interval,
        max_attempts_per_date=max_attempts_per_date,
        polling_mode=polling_mode,
        headless=headless
    )
    return await workflow.run()
