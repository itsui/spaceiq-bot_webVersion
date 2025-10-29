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
from src.utils.console_logger import start_console_logging, stop_console_logging
from src.utils.screenshot_cleanup import cleanup_old_screenshots
from src.utils.log_cleanup import cleanup_old_logs
from src.utils.rich_ui import ui, DateStatus
from src.utils.sound_notification import play_booking_success_alert


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

    def __init__(self, refresh_interval: int = 30, max_attempts_per_date: int = 10, polling_mode: bool = False, headless: bool = False, continuous_loop: bool = False):
        self.config_path = Path(__file__).parent.parent.parent / "config" / "booking_config.json"
        self.refresh_interval = refresh_interval
        self.max_attempts_per_date = max_attempts_per_date
        self.polling_mode = polling_mode
        self.headless = headless

        # Headless mode should always loop continuously (production mode)
        # This ensures it checks existing bookings and keeps trying unbooked dates
        if headless and not continuous_loop:
            continuous_loop = True

        self.continuous_loop = continuous_loop
        self.session_manager = SessionManager(headless=headless)

        # Setup file logging
        self.logger, self.log_file = setup_file_logger()
        self.logger.info("=" * 70)
        self.logger.info("Multi-Date Booking Workflow Initialized")
        self.logger.info("=" * 70)

        # Start console logging (captures ALL print statements)
        self.console_log_file, self.console_logger = start_console_logging()

        # Cleanup old files (screenshots are large, logs are small and useful for debugging)
        cleanup_old_screenshots(keep_sessions=2, logger=self.logger)
        cleanup_old_logs(keep_sessions=10, logger=self.logger)

    def get_progressive_wait_time(self, round_num: int, config: Dict[str, Any] = None) -> int:
        """
        Calculate wait time based on round number with progressive backoff.

        Reads wait times from config file's wait_times section.
        Default strategy if config missing:
        - Rounds 1-5: 1 minute (60 seconds) - aggressive checking
        - Rounds 6-15: 5 minutes (300 seconds) - moderate checking
        - Rounds 16+: 15 minutes (900 seconds) - conservative checking

        Args:
            round_num: Current round number (1-indexed)
            config: Configuration dictionary (loaded from booking_config.json)

        Returns:
            Wait time in seconds
        """
        # Load config if not provided
        if config is None:
            config = self.load_config()

        # Get wait times from config with fallback defaults
        wait_times = config.get("wait_times", {})
        rounds_1_to_5 = wait_times.get("rounds_1_to_5", {}).get("seconds", 60)
        rounds_6_to_15 = wait_times.get("rounds_6_to_15", {}).get("seconds", 300)
        rounds_16_plus = wait_times.get("rounds_16_plus", {}).get("seconds", 900)

        if round_num <= 5:
            wait_time = rounds_1_to_5
            self.logger.info(f"Round {round_num}: Using {wait_time}s wait (aggressive checking)")
            return wait_time
        elif round_num <= 15:
            wait_time = rounds_6_to_15
            self.logger.info(f"Round {round_num}: Using {wait_time}s wait (moderate checking)")
            return wait_time
        else:
            wait_time = rounds_16_plus
            self.logger.info(f"Round {round_num}: Using {wait_time}s wait (conservative checking)")
            return wait_time

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

        # Get booking days from config (default to Wed=2, Thu=3)
        booking_days_config = config.get("booking_days", {})
        weekdays_to_book = booking_days_config.get("weekdays", [2, 3])

        dates_to_try = []
        current_date = today

        while current_date <= furthest_date:
            # Check if this weekday should be booked (from config)
            if current_date.weekday() in weekdays_to_book:
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

        # Show initial header and info (before dashboard starts)
        ui.print_header()
        ui.print_info(f"Target: {len(dates_to_try)} date(s) • Desk: {desk_prefix}.* • Refresh: {self.refresh_interval}s")

        # Show mode banners
        if self.headless:
            ui.print_mode_banner("headless")  # Headless now implies continuous loop
        elif self.continuous_loop:
            ui.print_mode_banner("loop")
        elif self.polling_mode:
            ui.print_mode_banner("poll")

        results = {}

        # Initialize the dashboard with dates
        ui.initialize_dates(dates_to_try)

        try:
            # Validate session first (especially important for headless mode)
            if self.headless:
                # print("[INFO] Headless mode requested - validating session first...")
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

            # Navigate to SpaceIQ once (needed for checking existing bookings)
            await booking_page.navigate_to_floor_view(building, floor)

            # Start the live dashboard
            import time
            await asyncio.sleep(2)  # Let user see the initial info
            dashboard = ui.start_live_dashboard()

            # Polling loop: keep trying until at least one date is booked (if polling_mode enabled)
            # Or loop indefinitely (if continuous_loop enabled)
            round_num = 1
            while True:
                ui.current_round = round_num
                # Check existing bookings at start of each round (skip already booked dates)
                # Always check on first round, and every round in continuous loop mode
                existing_bookings = []
                if round_num == 1 or self.continuous_loop:
                    ui.set_operation("Checking existing bookings...", "Fetching calendar data")
                    try:
                        existing_bookings = await booking_page.get_existing_bookings(logger=self.logger)
                        ui.set_operation("")

                        # Update dashboard with existing bookings
                        for date in existing_bookings:
                            if date in ui.date_statuses:
                                ui.set_date_status(date, DateStatus.ALREADY_BOOKED)

                        self.logger.info(f"Found {len(existing_bookings)} existing bookings")
                    except Exception as e:
                        ui.set_operation("")
                        self.logger.warning(f"Failed to fetch existing bookings: {e}")

                # ALWAYS recalculate dates from calendar (don't trust config)
                # This ensures we verify every date every round
                today_now = datetime.now().date()
                furthest_date_now = today_now + timedelta(weeks=4, days=1)

                dates_to_try_now = []
                current_date_check = today_now

                while current_date_check <= furthest_date_now:
                    # Use weekdays_to_book from config (defined earlier in generate_dates_to_try)
                    if current_date_check.weekday() in weekdays_to_book:
                        if current_date_check >= today_now:
                            date_str = current_date_check.strftime("%Y-%m-%d")
                            # Skip if already booked
                            if date_str not in existing_bookings:
                                # Special check for today: only book if before cutoff time
                                if current_date_check == today_now:
                                    from config import Config
                                    current_time = datetime.now()
                                    cutoff_time = current_time.replace(
                                        hour=Config.BOOKING_TODAY_CUTOFF_HOUR,
                                        minute=Config.BOOKING_TODAY_CUTOFF_MINUTE,
                                        second=0,
                                        microsecond=0
                                    )
                                    if current_time >= cutoff_time:
                                        # Too late to book today, skip it
                                        self.logger.info(f"Skipping today ({date_str}) - after cutoff time {Config.BOOKING_TODAY_CUTOFF_HOUR:02d}:{Config.BOOKING_TODAY_CUTOFF_MINUTE:02d}")
                                        current_date_check += timedelta(days=1)
                                        continue
                                dates_to_try_now.append(date_str)
                    current_date_check += timedelta(days=1)

                dates_to_try_now.sort(reverse=True)

                if not dates_to_try_now:
                    if existing_bookings:
                        if self.continuous_loop:
                            wait_time = self.get_progressive_wait_time(round_num)
                            ui.set_operation("All dates already booked", "Waiting for cancellations...")
                            ui.start_countdown(wait_time, "Waiting for next round")

                            # Countdown loop
                            for _ in range(wait_time):
                                await asyncio.sleep(1)
                                ui.update_countdown()

                            ui.stop_countdown()
                            round_num += 1
                            continue
                    ui.set_operation("Complete", "No more dates to try")
                    break

                round_results = {}

                # Try each date once, move to next if no seats available
                for idx, date_str in enumerate(dates_to_try_now, 1):
                    # Mark as trying
                    attempt_num = ui.date_attempts.get(date_str, 0) + 1
                    ui.set_date_status(date_str, DateStatus.TRYING, attempt=attempt_num)
                    ui.set_operation(f"Booking {date_str}", f"Date {idx}/{len(dates_to_try_now)} - Attempt #{attempt_num}")
                    ui.log_activity(f"Starting booking for {date_str} (attempt {attempt_num})")

                    # Parse date
                    target_date = datetime.strptime(date_str, '%Y-%m-%d')
                    days_ahead = (target_date.date() - datetime.now().date()).days

                    # Try booking this date (single attempt to check availability)
                    success, desk_code = await self._try_booking_date(
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
                        ui.set_date_status(date_str, DateStatus.SUCCESS, desk=desk_code)
                        ui.log_activity(f"SUCCESS: Booked {date_str} - Desk {desk_code}")
                        self.logger.info(f"Successfully booked {date_str} ({desk_code})")

                        # Update config for record-keeping (but we'll still try this date again next round to verify)
                        self.remove_date_from_config(date_str)
                    else:
                        # Could be: no seats available, already booked, or date disabled
                        ui.set_date_status(date_str, DateStatus.SKIPPED)
                        ui.log_activity(f"SKIPPED: {date_str} - No available desks")
                        self.logger.info(f"No available desks for {date_str}")

                # Check if we should continue polling
                any_booked = any(round_results.values())

                if not self.polling_mode and not self.continuous_loop:
                    # Single pass mode - exit after one round
                    break

                if self.continuous_loop:
                    # Continuous loop mode - keep trying all dates forever
                    if any_booked:
                        ui.set_operation("Booking successful!", "Continuing to next round...")
                        await asyncio.sleep(2)
                    else:
                        wait_time = self.get_progressive_wait_time(round_num)
                        ui.set_operation("Waiting for next round", "No seats available")
                        ui.start_countdown(wait_time, "Waiting for next round")

                        # Countdown loop
                        for _ in range(wait_time):
                            await asyncio.sleep(1)
                            ui.update_countdown()

                        ui.stop_countdown()
                    round_num += 1
                    continue

                if any_booked:
                    # At least one date was booked (polling mode)
                    # Continue to next round to verify all dates again
                    ui.set_operation("Booking successful!", "Verifying all dates...")
                    await asyncio.sleep(2)
                    round_num += 1
                    continue

                # No dates booked this round - wait and try again (polling mode)
                wait_time = self.get_progressive_wait_time(round_num)
                ui.set_operation("Waiting for next round", "No seats available")
                ui.start_countdown(wait_time, "Waiting for next round")

                # Countdown loop
                for _ in range(wait_time):
                    await asyncio.sleep(1)
                    ui.update_countdown()

                ui.stop_countdown()
                round_num += 1

            # Stop dashboard and show final summary
            ui.stop_live_dashboard()
            ui.print_summary_table(results, existing_bookings if (self.continuous_loop or self.polling_mode) else None)

            return results

        except Exception as e:
            ui.stop_live_dashboard()
            print(f"\n[ERROR] Error during multi-date booking: {e}")
            import traceback
            traceback.print_exc()
            return results

        finally:
            ui.stop_live_dashboard()
            await self.session_manager.close()

            # Stop console logging
            stop_console_logging(self.console_logger)

    async def _try_booking_date(
        self,
        booking_page: SpaceIQBookingPage,
        page,
        date_str: str,
        days_ahead: int,
        building: str,
        floor: str,
        desk_prefix: str
    ) -> tuple[bool, str]:
        """
        Try booking a specific date.

        Strategy:
        1. Check if desks available for this date
        2. If NO desks → return False immediately (skip to next date)
        3. If desks found → try to book with retries (for click failures)

        Returns:
            Tuple of (success: bool, desk_code: str or None)
        """

        try:
            # Steps 1-6: Navigation (consolidated into single progress line)
            ui.log_activity(f"  Loading floor map for {date_str}...")
            await booking_page.navigate_to_floor_view(building, floor)
            await booking_page.click_book_desk_button()
            await booking_page.open_date_picker()

            try:
                await booking_page.select_date_from_calendar(days_ahead=days_ahead)
            except Exception as e:
                if "disabled" in str(e).lower() or "beyond booking window" in str(e).lower():
                    ui.log_activity(f"  {date_str} is beyond booking window")
                    self.logger.info(f"Date {date_str} is disabled - beyond booking window")
                    return False, None
                else:
                    raise  # Re-raise if it's a different error

            await booking_page.click_update_button()
            await booking_page.wait_for_floor_map_to_load()
            ui.log_activity(f"  Waiting for SVG to render...")
            await asyncio.sleep(7)  # Wait for SVG to render
            await booking_page.capture_screenshot("floor_map_loaded")

            # Step 7: Check available desks
            ui.log_activity(f"  Checking available {desk_prefix}.* desks...")
            available_desks = await booking_page.get_available_desks_from_sidebar(
                desk_prefix=desk_prefix,
                logger=self.logger
            )

            if not available_desks:
                ui.log_activity(f"  No {desk_prefix}.* desks available")
                self.logger.info(f"No {desk_prefix}.* desks available for {date_str}")
                return False, None  # Skip to next date immediately

            ui.log_activity(f"  Found {len(available_desks)} desk(s): {', '.join(available_desks[:3])}")
            self.logger.info(f"Available desks (unsorted): {available_desks}")

            # Sort by priority (if configured)
            config = self.load_config()
            priority_config = config.get("desk_preferences", {}).get("priority_ranges", [])

            if priority_config:
                from src.utils.desk_priority import sort_desks_by_priority

                sorted_desks = sort_desks_by_priority(available_desks, priority_config)
                # pout.info(f"  Priority: {sorted_desks[0]} (highest)")
                self.logger.info(f"Available desks (sorted by priority): {sorted_desks}")
                available_desks = sorted_desks
            else:
                self.logger.info("No priority configuration found - using unsorted order")

            # Step 8: Use CV to find and click desk
            ui.log_activity(f"  Using CV to find desk on map...")
            found_desk = await booking_page.find_and_click_available_desks(
                available_desks=available_desks,
                logger=self.logger
            )

            if not found_desk:
                ui.log_activity(f"  ERROR: Could not locate desk on map")
                self.logger.error(f"Could not locate desk on map for {date_str}")
                return False, None

            ui.log_activity(f"  Clicked desk {found_desk}, submitting booking...")

            # Step 9: Book the desk
            await booking_page.click_book_now_in_popup()
            await asyncio.sleep(2)
            success = await booking_page.verify_booking_success()

            if success:
                ui.log_activity(f"  Booking verified successfully!")
                await booking_page.capture_screenshot(f"booking_success_{date_str}")

                # Play success sound notification (especially useful in headless mode)
                play_booking_success_alert()

                return True, found_desk
            else:
                ui.log_activity(f"  ERROR: Booking verification failed")
                self.logger.error(f"Booking verification failed for {date_str}")
                return False, None

        except Exception as e:
            ui.log_activity(f"  ERROR: {str(e)[:50]}")
            self.logger.error(f"Failed to book {date_str}: {e}")
            return False, None


async def run_multi_date_booking(
    refresh_interval: int = 30,
    max_attempts_per_date: int = 10,
    polling_mode: bool = False,
    headless: bool = False,
    continuous_loop: bool = False
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
        continuous_loop: If True, keeps trying all dates indefinitely (default: False)

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
        headless=headless,
        continuous_loop=continuous_loop
    )
    return await workflow.run()
