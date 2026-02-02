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

        # Setup file logging with size limits from config
        from config import Config
        self.logger, self.log_file = setup_file_logger(
            max_bytes=Config.MAX_BOOKING_LOG_SIZE_MB * 1024 * 1024,
            backup_count=Config.LOG_BACKUP_COUNT
        )
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
            # Validate session first (ONLY if using legacy cookies, NOT persistent profiles)
            if self.headless and self.session_manager.user_id is None:
                # Legacy cookie-based authentication requires validation
                # print("[INFO] Headless mode requested - validating session first...")
                from src.auth.session_validator import validate_and_refresh_session, SessionExpiredException

                try:
                    session_valid, use_headless = await validate_and_refresh_session(
                        force_headless=True,
                        auth_file=self.session_manager.auth_file
                    )

                    if not session_valid:
                        print("\n[ERROR] Session validation failed. Cannot continue.")
                        return {}

                    # Update headless setting based on validation result
                    self.headless = use_headless
                    self.session_manager.headless = use_headless

                except SessionExpiredException as e:
                    error_msg = "Session expired. Please re-authenticate via the web interface."
                    print(f"\n[ERROR] {error_msg}")
                    raise Exception(error_msg) from e
            elif self.session_manager.user_id is not None:
                # Using persistent profile - no need to validate old cookies
                pass

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
            # Read restart interval from config (default 50 rounds)
            restart_interval = config.get("browser_restart", {}).get("restart_every_n_rounds", 50)
            while True:
                ui.current_round = round_num

                # Restart browser periodically to prevent timeout/degradation issues
                # This is especially important for long-running headless sessions
                if round_num > 1 and round_num % restart_interval == 0:
                    ui.set_operation("Restarting browser...", f"Preventing timeout issues (round {round_num})")
                    self.logger.info(f"Round {round_num}: Restarting browser to prevent degradation")

                    try:
                        # Close old browser
                        await page.close()
                        await self.session_manager.close()

                        # Wait a moment
                        await asyncio.sleep(2)

                        # Reinitialize
                        context = await self.session_manager.initialize()
                        page = await context.new_page()
                        booking_page = SpaceIQBookingPage(page)
                        await booking_page.navigate_to_floor_view(building, floor)

                        self.logger.info(f"Browser restarted successfully")
                        ui.log_activity(f"Browser restarted (round {round_num})")
                        await asyncio.sleep(1)
                    except Exception as e:
                        self.logger.error(f"Failed to restart browser: {e}")
                        ui.log_activity(f"ERROR: Browser restart failed - {e}")
                        # Continue anyway, maybe the old browser still works

                # Check existing bookings at start of each round (skip already booked dates)
                # Always check on first round, and every round in continuous loop mode
                existing_bookings = []
                booking_check_failed = False
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
                        error_msg = str(e)
                        self.logger.warning(f"Error fetching existing bookings: {e}")
                        booking_check_failed = True

                        # If we get timeout errors, the browser is likely degraded - restart it
                        if "Timeout" in error_msg or "timeout" in error_msg:
                            ui.set_operation("Browser timeout detected", "Restarting browser...")
                            self.logger.warning(f"Timeout detected during booking check - restarting browser")
                            ui.log_activity(f"WARN: Timeout detected - restarting browser")

                            try:
                                await page.close()
                                await self.session_manager.close()
                                await asyncio.sleep(2)

                                context = await self.session_manager.initialize()
                                page = await context.new_page()
                                booking_page = SpaceIQBookingPage(page)
                                await booking_page.navigate_to_floor_view(building, floor)

                                self.logger.info(f"Browser restarted after timeout")
                                ui.log_activity(f"Browser restarted successfully")

                                # Try fetching bookings again after restart
                                try:
                                    existing_bookings = await booking_page.get_existing_bookings(logger=self.logger)
                                    self.logger.info(f"Found {len(existing_bookings)} existing bookings after restart")
                                    booking_check_failed = False
                                except Exception as e2:
                                    self.logger.warning(f"Still failed after restart: {e2}")
                            except Exception as restart_error:
                                self.logger.error(f"Failed to restart browser: {restart_error}")
                                ui.log_activity(f"ERROR: Browser restart failed")

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
                            # DYNAMIC WAIT TIME: Be more aggressive around midnight when new dates become available!
                            current_time = datetime.now()

                            # Check if we're in the "golden hour" after midnight
                            if current_time.hour == 0:  # Between 12:00 AM and 12:59 AM
                                wait_time = 60  # Check every 1 minute - very aggressive!
                                ui.set_operation("Midnight Special!", "Hunting for new dates that become available at midnight!")
                            elif current_time.hour <= 2:  # Between 1:00 AM and 2:59 AM
                                wait_time = 120  # Check every 2 minutes
                                ui.set_operation("Early Morning", "Checking frequently for new dates...")
                            elif current_time.hour <= 6:  # Between 3:00 AM and 6:59 AM
                                wait_time = 180  # Check every 3 minutes
                                ui.set_operation("Pre-Dawn", "Checking for new dates...")
                            else:
                                # Normal daytime - use progressive wait time
                                wait_time = self.get_progressive_wait_time(round_num)
                                ui.set_operation("All dates already booked", "Waiting for cancellations...")

                            ui.start_countdown(wait_time, "Checking for new dates...")

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

            # Smart wait: Ensure map finishes rendering before proceeding
            from src.vision.desk_detector import DeskDetector
            detector = DeskDetector()
            max_wait_time = 15  # Maximum 15 seconds total
            wait_interval = 3   # Check every 3 seconds
            total_waited = 0
            circles_detected = 0
            prev_circle_count = -1

            while total_waited < max_wait_time:
                await asyncio.sleep(wait_interval)
                total_waited += wait_interval

                # Take a test screenshot to check circle count
                await booking_page.capture_screenshot("floor_map_loaded")
                screenshot_files = sorted(
                    booking_page.screenshots_dir.glob("floor_map_loaded_*.png"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )

                if screenshot_files:
                    circles = detector.find_blue_circles(str(screenshot_files[0]), debug=False)
                    circles_detected = len(circles)

                    # Map is loaded when circle count stabilizes (doesn't change between checks)
                    if prev_circle_count == circles_detected:
                        # Circle count stable - map is ready
                        self.logger.info(f"Map ready: {circles_detected} available desk(s) detected")
                        break
                    else:
                        # Still changing - keep waiting
                        prev_circle_count = circles_detected
                        if total_waited < max_wait_time:
                            self.logger.info(f"Map rendering: {circles_detected} desk(s) visible (waiting for stable count)")

            # Log final circle count without warning (low count is normal on busy days)
            if circles_detected == 0:
                ui.log_activity(f"  No available desks detected on map")
                self.logger.warning(f"Map shows 0 available desks - map may not be loaded or all desks are booked")
            else:
                ui.log_activity(f"  Detected {circles_detected} available desk(s) on map")
                self.logger.info(f"Map shows {circles_detected} available desk(s)")

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

            ui.log_activity(f"  Found {len(available_desks)} desk(s)")
            self.logger.info(f"Available desks: {len(available_desks)}")

            # Sort by priority (if configured)
            config = self.load_config()
            priority_config = config.get("desk_preferences", {}).get("priority_ranges", [])

            if priority_config:
                from src.utils.desk_priority import sort_desks_by_priority

                sorted_desks = sort_desks_by_priority(available_desks, priority_config)
                self.logger.info(f"Desks sorted by priority")
                available_desks = sorted_desks

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
    continuous_loop: bool = False,
    config: Dict = None,
    web_logger = None,
    status_callback = None
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
        config: Optional configuration dictionary (for web mode)
        web_logger: Optional web logger instance (for web mode)
        status_callback: Optional async callback for status updates (for web mode)

    Returns:
        Dictionary mapping date -> success status

    Example:
        from src.workflows.multi_date_booking import run_multi_date_booking
        # Single pass
        results = await run_multi_date_booking(refresh_interval=30, max_attempts_per_date=10)
        # Polling mode (keeps trying)
        results = await run_multi_date_booking(refresh_interval=30, polling_mode=True)
        # Web mode
        results = await run_multi_date_booking(config=config, web_logger=logger, headless=True, continuous_loop=True, status_callback=callback)
    """

    # Import the new unified adapter
    from src.adapters.unified_booking_adapter import run_multi_date_booking as new_run_multi_date_booking

    # Delegate to the new implementation
    return await new_run_multi_date_booking(
        refresh_interval=refresh_interval,
        max_attempts_per_date=max_attempts_per_date,
        polling_mode=polling_mode,
        headless=headless,
        continuous_loop=continuous_loop,
        config=config,
        web_logger=web_logger,
        status_callback=status_callback
    )


def calculate_wait_time_from_config(round_num: int, config: Dict[str, Any]) -> int:
    """
    Calculate wait time based on round number using user's configuration.

    Args:
        round_num: Current round number (1-indexed)
        config: Configuration dictionary with wait_times

    Returns:
        Wait time in seconds
    """
    wait_times = config.get("wait_times", {})

    # Find the matching wait time range
    for key, value in wait_times.items():
        if not key.startswith('rounds_'):
            continue

        # Parse range from key like "rounds_1_to_5" or "rounds_16_plus"
        if '_plus' in key:
            # Format: rounds_X_plus
            start = int(key.split('_')[1])
            if round_num >= start:
                return value.get('seconds', 900)
        elif '_to_' in key:
            # Format: rounds_X_to_Y
            parts = key.split('_')
            start = int(parts[1])
            end = int(parts[3])
            if start <= round_num <= end:
                return value.get('seconds', 60)

    # Fallback defaults if no match found
    if round_num <= 5:
        return 60  # 1 minute
    elif round_num <= 15:
        return 300  # 5 minutes
    else:
        return 900  # 15 minutes


async def run_multi_date_booking_web_mode(
    config: Dict[str, Any],
    web_logger,
    headless: bool = True,
    continuous_loop: bool = True,
    app_context=None,
    user_id: int = None
) -> Dict[str, bool]:
    """
    Run multi-date booking in web mode without Rich UI.

    Args:
        config: Configuration dictionary
        web_logger: Web logger instance for structured logging
        headless: If True, runs browser in headless mode
        continuous_loop: If True, keeps trying all dates indefinitely
        app_context: Flask app context for database access
        user_id: User ID for reloading config dynamically

    Returns:
        Dictionary mapping date -> success status with additional metadata
    """
    from config import Config
    from src.pages.spaceiq_booking_page import SpaceIQBookingPage
    from src.auth.session_manager import SessionManager
    from src.utils.supabase_validator import validate_user_from_auth_file
    from src.utils.screenshot_cleanup import cleanup_old_screenshots
    from pathlib import Path

    web_logger.info("Starting Multi-Date Booking (Web Mode)")

    # ========================================
    # AUTO-REMAP CHECK
    # ========================================
    # Check if desk position cache needs remapping before starting
    from src.utils.desk_position_cache import get_cache
    cache = get_cache()
    
    if cache.needs_remap(max_age_days=7, min_desks=50):
        remap_reason = cache.get_remap_reason(max_age_days=7, min_desks=50)
        web_logger.info(f"🗺️ AUTO-REMAP: {remap_reason}")
        web_logger.info("🔄 Starting automatic desk remapping...")
        
        try:
            from map_desk_positions import map_desk_positions
            
            # Create progress callback to log to web logger
            def remap_progress(message):
                web_logger.info(f"[REMAP] {message}")
            
            # Run remapping
            remap_result = await map_desk_positions(
                user_id=user_id,
                web_mode=True,
                progress_callback=remap_progress
            )
            
            if remap_result and remap_result.get('success'):
                web_logger.info(f"✅ Auto-remap complete! Mapped {remap_result.get('total_desks', 0)} desks")
                # Reload cache after remapping
                cache.load()
            else:
                web_logger.warning("⚠️ Auto-remap completed with issues, continuing anyway...")
                
        except Exception as e:
            web_logger.warning(f"⚠️ Auto-remap failed: {e} - continuing with existing cache")
    else:
        cache_info = cache.get_cache_info()
        web_logger.info(f"✓ Desk cache OK: {cache_info.get('total_desks', 0)} desks, last updated {cache_info.get('last_updated', 'unknown')[:10]}")

    # Get user-specific screenshot directory if provided (for multiuser isolation)
    screenshots_dir = config.get('screenshots_dir')
    if screenshots_dir:
        # Use relative path for security - don't expose full file paths in logs
        screenshots_dir_relative = Path(screenshots_dir).relative_to(Path.cwd())
        web_logger.info(f"Using user-specific screenshots directory: /{screenshots_dir_relative}")
        # Cleanup old screenshots to avoid disk space issues (keep only 1 recent session)
        try:
            cleanup_old_screenshots(screenshots_dir=Path(screenshots_dir), keep_sessions=1)
            web_logger.info("Cleaned up old screenshots")
        except Exception as e:
            web_logger.warning(f"Screenshot cleanup failed: {e}")

    # Check if user has manually set specific dates (use them as-is)
    booking_days_config = config.get("booking_days", {})
    weekdays_to_book = booking_days_config.get("weekdays", [2, 3])
    blacklist_dates = config.get("blacklist_dates", [])
    existing_dates = config.get("dates_to_try", [])
    auto_ignore_uk_holidays = config.get("auto_ignore_uk_holidays", True)

    # Always use the date calculator - it preserves manual dates and adds auto-generated ones
    from src.utils.date_calculator import calculate_booking_dates

    # Calculate dates (preserves manual dates + adds auto-generated based on weekdays)
    final_dates = calculate_booking_dates(
        weekdays=weekdays_to_book,
        blacklist_dates=blacklist_dates,
        existing_dates=existing_dates,
        today=None,  # Uses today
        auto_ignore_uk_holidays=auto_ignore_uk_holidays
    )

    config["dates_to_try"] = final_dates

    web_logger.info(f"Ready to book {len(final_dates)} dates (furthest: {final_dates[0] if final_dates else 'None'})")

    # Save updated dates to database so user can see them in UI
    try:
        # Import here to avoid circular imports
        from models import db, BotConfig, User
        from flask import current_app

        # Get user_id from config's auth_file path (don't expose full path in logs)
        auth_file = config.get('auth_file', '')
        if 'spaceiq_session_' in auth_file:
            # Extract user_id from filename without logging full path
            filename = Path(auth_file).name
            # Handle new format: spaceiq_session_RANDOM_userID.json
            # Extract ID from _userID suffix
            import re
            user_match = re.search(r'_user(\d+)\.json', filename)
            if user_match:
                user_id = int(user_match.group(1))
            else:
                # Fallback for old format: spaceiq_session_ID.json
                user_id = int(filename.split('spaceiq_session_')[1].split('.json')[0])

            # Update in database
            if app_context:
                app_context.push()  # Push the app context
                try:
                    bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                    if bot_config:
                        final_dates = config.get("dates_to_try", [])
                        bot_config.set_dates_to_try(final_dates)
                        db.session.commit()
                finally:
                    app_context.pop()  # Pop the app context
            else:
                web_logger.warning("No app context provided - skipping database update")
    except Exception as e:
        web_logger.warning(f"Could not update dates in database: {e}")

    # Extract configuration
    building = config.get("building", "LC")
    floor = config.get("floor", "2")
    desk_prefix = config.get("desk_preferences", {}).get("prefix", "2.24")
    booking_days_config = config.get("booking_days", {})
    weekdays_to_book = booking_days_config.get("weekdays", [2, 3])  # Wed=2, Thu=3


    # Calculate dates from calendar
    today = datetime.now().date()
    furthest_date = today + timedelta(weeks=4, days=1)  # 29 days

    dates_to_try = []
    current_date = today

    while current_date <= furthest_date:
        if current_date.weekday() in weekdays_to_book:
            if current_date >= today:
                dates_to_try.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    dates_to_try.sort(reverse=True)

    if not dates_to_try:
        web_logger.warning("No eligible dates found in the next 29 days")
        return {"success": False, "message": "No eligible dates found"}

    web_logger.info(f"Found {len(dates_to_try)} dates to try")

    results = {}
    # Use persistent profile if user_id provided (RECOMMENDED - cookies persist!)
    session_manager = SessionManager(
        headless=headless,
        auth_file=config.get('auth_file'),
        user_id=user_id  # Pass user_id for persistent profile
    )

    try:
        # Validate session for headless mode (ONLY if using legacy cookies, NOT persistent profiles)
        if headless and user_id is None:
            # Legacy cookie-based authentication requires validation
            web_logger.info("Validating session for headless mode...")
            from src.auth.session_validator import validate_and_refresh_session, SessionExpiredException

            try:
                session_valid, use_headless = await validate_and_refresh_session(
                    force_headless=True,
                    auth_file=session_manager.auth_file
                )
                if not session_valid:
                    web_logger.error("Session validation failed")
                    return {"error": "Session validation failed", "success": False}

                headless = use_headless
                session_manager.headless = use_headless

            except SessionExpiredException as e:
                error_msg = "Session expired. Please re-authenticate via the web interface."
                web_logger.error(error_msg)
                raise Exception(error_msg) from e
        elif user_id is not None:
            # Using persistent profile - no need to validate old cookies
            pass

        # Initialize session
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page, screenshots_dir=screenshots_dir, web_mode=True)

        # Navigate to SpaceIQ
        web_logger.info("Navigating to SpaceIQ...")
        await booking_page.navigate_to_floor_view(building, floor)

        round_num = 1
        restart_interval = config.get("browser_restart", {}).get("restart_every_n_rounds", 50)

        while True:
            web_logger.info(f"Starting Round {round_num}")
            current_round_results = {}

            # Reload config from database at start of each round (to pick up user changes)
            if app_context and user_id and round_num > 1:
                try:
                    with app_context:
                        from models import BotConfig, db
                        bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                        if bot_config:
                            # Update config from database (excluding dates which are recalculated fresh each round)
                            config['blacklist_dates'] = bot_config.get_blacklist_dates()
                            config['booking_days'] = bot_config.get_booking_days()
                            config['wait_times'] = bot_config.get_wait_times()
                except Exception as e:
                    web_logger.warning(f"Failed to reload config: {e}")

            # Restart browser periodically
            if round_num > 1 and round_num % restart_interval == 0:
                web_logger.info(f"Restarting browser (round {round_num})...")
                try:
                    await page.close()
                    await session_manager.close()
                    await asyncio.sleep(2)

                    context = await session_manager.initialize()
                    page = await context.new_page()
                    booking_page = SpaceIQBookingPage(page, screenshots_dir=screenshots_dir, web_mode=True)
                    await booking_page.navigate_to_floor_view(building, floor)

                    web_logger.info("Browser restarted successfully")
                except Exception as e:
                    web_logger.error(f"Browser restart failed: {e}")

            # Check existing bookings
            existing_bookings = []
            try:
                web_logger.info("Checking existing bookings...")
                existing_bookings = await booking_page.get_existing_bookings(logger=web_logger)
                web_logger.info(f"Found {len(existing_bookings)} existing bookings")
            except Exception as e:
                web_logger.warning(f"Error checking existing bookings: {e}")

            # CRITICAL: Always recalculate dates first BEFORE checking if we have dates to try
            # This ensures we pick up new dates as days pass (e.g., at midnight when new Wed/Thu become available)
            today_now = datetime.now().date()
            current_time = datetime.now()

            # RECALCULATE fresh dates from calendar for the next 29 days from TODAY
            # This prevents the "All dates already booked" deadlock when new dates should become available
            booking_days_config = config.get("booking_days", {})
            weekdays_to_book = booking_days_config.get("weekdays", [2, 3])  # Wed=2, Thu=3
            blacklist_dates = config.get("blacklist_dates", [])
            auto_ignore_uk_holidays = config.get("auto_ignore_uk_holidays", True)

            # Load existing dates from database to preserve manually added dates
            existing_dates_to_preserve = []
            if app_context and user_id:
                try:
                    with app_context:
                        from models import BotConfig
                        bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                        if bot_config:
                            existing_dates_to_preserve = bot_config.get_dates_to_try()
                except Exception as e:
                    web_logger.warning(f"Failed to load existing dates from database: {e}")

            # Use the date calculator to get fresh dates (preserves manual dates)
            from src.utils.date_calculator import calculate_booking_dates
            recalculated_dates = calculate_booking_dates(
                weekdays=weekdays_to_book,
                blacklist_dates=blacklist_dates,
                existing_dates=existing_dates_to_preserve,  # Preserve manual dates
                today=None,  # Uses current date
                auto_ignore_uk_holidays=auto_ignore_uk_holidays
            )

            date_word = "date" if len(recalculated_dates) == 1 else "dates"
            if recalculated_dates:
                web_logger.info(f"Found {len(recalculated_dates)} {date_word} to book (up to {recalculated_dates[0]})")
            else:
                web_logger.info(f"No dates to book at this time")

            # Now filter the recalculated dates based on existing bookings and timing
            dates_to_try_now = []
            for date_str in recalculated_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                    # Skip if date is in the past
                    if date_obj < today_now:
                        continue

                    # Skip if already booked
                    if date_str in existing_bookings:
                        continue

                    # Check cutoff time for today
                    if date_obj == today_now:
                        cutoff_time = current_time.replace(
                            hour=Config.BOOKING_TODAY_CUTOFF_HOUR,
                            minute=Config.BOOKING_TODAY_CUTOFF_MINUTE,
                            second=0,
                            microsecond=0
                        )
                        if current_time >= cutoff_time:
                            web_logger.info(f"Skipping today ({date_str}) - after cutoff time")
                            continue

                    dates_to_try_now.append(date_str)
                except ValueError:
                    web_logger.warning(f"Invalid date format: {date_str}")
                    continue

            # Dates are already sorted (furthest first), so maintain that order
            # Only log when we have dates to attempt (avoid "Attempting 0 dates" message)
            if dates_to_try_now:
                date_word = "date" if len(dates_to_try_now) == 1 else "dates"
                web_logger.info(f"Attempting {len(dates_to_try_now)} {date_word} this round")

            # Update config and database with the fresh recalculated dates
            config['dates_to_try'] = recalculated_dates
            try:
                if app_context and user_id:
                    with app_context:
                        from models import BotConfig, db
                        bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                        if bot_config:
                            bot_config.set_dates_to_try(recalculated_dates)
                            db.session.commit()
            except Exception as e:
                web_logger.warning(f"Failed to update dates in database: {e}")

            if not dates_to_try_now:
                if continuous_loop:
                    # ========================================
                    # LIGHTWEIGHT MODE - All dates are booked!
                    # ========================================
                    # - Recalculate dates every hour during the day
                    # - Aggressive checks around midnight for new dates
                    # - Check for config changes every minute
                    # - Keep SpaceIQ session alive periodically
                    # - No CV or heavy tasks
                    
                    current_time = datetime.now()
                    
                    # Track when we last pinged SpaceIQ to keep session alive
                    if not hasattr(run_multi_date_booking_web_mode, '_last_keepalive'):
                        run_multi_date_booking_web_mode._last_keepalive = current_time
                    
                    # Track config modification time to detect changes
                    if not hasattr(run_multi_date_booking_web_mode, '_last_config_check'):
                        run_multi_date_booking_web_mode._last_config_check = None
                    
                    # Determine wait time based on time of day
                    if current_time.hour == 0 and current_time.minute < 10:  # 12:00 AM - 12:10 AM
                        wait_time = 60  # Check every 1 minute - new dates become available!
                        web_logger.info(f"🌙 MIDNIGHT MODE: All {len(existing_bookings)} dates booked! Checking for new dates in {wait_time}s...")
                    else:
                        # Normal time - check every 1 hour
                        wait_time = 3600  # 1 hour
                        web_logger.info(f"✅ All {len(existing_bookings)} dates booked! Next check in {wait_time // 60}m...")
                    
                    # Keep SpaceIQ session alive with periodic lightweight pings (every 30 minutes)
                    time_since_keepalive = (current_time - run_multi_date_booking_web_mode._last_keepalive).total_seconds()
                    if time_since_keepalive >= 1800:  # 30 minutes
                        try:
                            web_logger.info("🔄 Keeping SpaceIQ session alive...")
                            # Lightweight ping - just navigate to landing page (no CV, no heavy work)
                            await booking_page.navigate_to_floor_view(building, floor)
                            run_multi_date_booking_web_mode._last_keepalive = current_time
                            web_logger.info("✓ Session keepalive successful")
                        except Exception as e:
                            web_logger.warning(f"Session keepalive failed: {e}")
                    
                    # Wait in chunks of 60s to check for config changes
                    # This allows quick response when user saves new dates in /config
                    wait_start = datetime.now()
                    while (datetime.now() - wait_start).total_seconds() < wait_time:
                        await asyncio.sleep(60)  # Check every minute
                        
                        # Check if config has changed (user saved new dates)
                        if app_context and user_id:
                            try:
                                with app_context:
                                    from models import BotConfig
                                    bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                                    if bot_config:
                                        current_updated = bot_config.updated_at
                                        if run_multi_date_booking_web_mode._last_config_check is None:
                                            run_multi_date_booking_web_mode._last_config_check = current_updated
                                        elif current_updated > run_multi_date_booking_web_mode._last_config_check:
                                            web_logger.info("📋 Config change detected! Recalculating dates now...")
                                            run_multi_date_booking_web_mode._last_config_check = current_updated
                                            break  # Exit wait loop to recalculate dates immediately
                            except Exception as e:
                                pass  # Silently ignore config check errors
                    
                    round_num += 1
                    continue
                else:
                    web_logger.info("✅ All dates are booked - nothing left to do!")
                    break

            # Try booking each date
            for idx, date_str in enumerate(dates_to_try_now, 1):
                web_logger.info(f"Attempting booking for {date_str} ({idx}/{len(dates_to_try_now)})")

                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d')
                    days_ahead = (target_date.date() - datetime.now().date()).days

                    success, desk_code = await _try_booking_date_web_mode(
                        booking_page=booking_page,
                        page=page,
                        date_str=date_str,
                        days_ahead=days_ahead,
                        building=building,
                        floor=floor,
                        desk_prefix=desk_prefix,
                        web_logger=web_logger,
                        config=config
                    )

                    current_round_results[date_str] = success
                    results[date_str] = success

                    if success:
                        web_logger.success(f"Successfully booked {date_str} - Desk {desk_code}")

                        # Play success sound
                        try:
                            from src.utils.sound_notification import play_booking_success_alert
                            play_booking_success_alert()
                        except:
                            pass  # Ignore sound errors in headless mode
                    else:
                        web_logger.info(f"No available desks for {date_str}")

                except Exception as e:
                    web_logger.error(f"Error booking {date_str}: {e}")
                    current_round_results[date_str] = False
                    results[date_str] = False

            # Check if we should continue
            any_booked = any(current_round_results.values())

            if not continuous_loop:
                break

            if any_booked:
                web_logger.info("Round successful - continuing to next round")
                await asyncio.sleep(2)
            else:
                # Calculate wait time from user configuration
                wait_time = calculate_wait_time_from_config(round_num, config)
                minutes = wait_time // 60
                seconds = wait_time % 60
                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                web_logger.info(f"No bookings this round - waiting {time_str} ({wait_time}s) for next round")
                await asyncio.sleep(wait_time)

            round_num += 1

        return {
            "success": True,
            "results": results,
            "dates_processed": list(results.keys()),
            "successful_bookings": sum(1 for success in results.values() if success),
            "total_attempts": len(results)
        }

    except Exception as e:
        web_logger.error(f"Fatal error in booking workflow: {e}")
        import traceback
        web_logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e), "success": False}

    finally:
        try:
            await session_manager.close()
        except:
            pass


async def _try_booking_date_web_mode(
    booking_page: SpaceIQBookingPage,
    page,
    date_str: str,
    days_ahead: int,
    building: str,
    floor: str,
    desk_prefix: str,
    web_logger,
    config: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Try booking a specific date in web mode.

    Returns:
        Tuple of (success: bool, desk_code: str or None)
    """
    try:
        web_logger.info(f"Loading floor map for {date_str}...")
        await booking_page.navigate_to_floor_view(building, floor)
        await booking_page.click_book_desk_button()
        await booking_page.open_date_picker()

        try:
            await booking_page.select_date_from_calendar(days_ahead=days_ahead)
        except Exception as e:
            if "disabled" in str(e).lower() or "beyond booking window" in str(e).lower():
                web_logger.warning(f"Date {date_str} is beyond booking window")
                return False, None
            else:
                raise

        await booking_page.click_update_button()
        await booking_page.wait_for_floor_map_to_load()
        await asyncio.sleep(7)  # Wait for SVG to render

        # Capture screenshot for CV detection (silent)
        await booking_page.capture_screenshot("floor_map_loaded")

        # Check available desks
        web_logger.info(f"Checking available {desk_prefix}.* desks...")
        locked_desks = config.get('locked_desks', []) if config else []
        available_desks = await booking_page.get_available_desks_from_sidebar(
            desk_prefix=desk_prefix,
            logger=web_logger,
            locked_desks=locked_desks
        )

        if not available_desks:
            web_logger.info(f"No {desk_prefix}.* desks available for {date_str}")
            return False, None

        web_logger.info(f"Found {len(available_desks)} available desks")

        # Sort by priority if configured
        priority_config = config.get("desk_preferences", {}).get("priority_ranges", [])
        if priority_config:
            try:
                from src.utils.desk_priority import sort_desks_by_priority
                available_desks = sort_desks_by_priority(available_desks, priority_config)
                web_logger.info(f"Desks sorted by priority")
            except Exception as e:
                web_logger.warning(f"Error sorting desks by priority: {e}")

        # Find and click desk using position cache or computer vision
        web_logger.info("Locating desk on map...")
        found_desk = await booking_page.find_and_click_available_desks(
            available_desks=available_desks,
            logger=web_logger
        )

        if not found_desk:
            web_logger.error(f"Could not locate desk on map for {date_str}")
            return False, None

        web_logger.info(f"Clicked desk {found_desk}, submitting booking...")
        await booking_page.click_book_now_in_popup()
        await asyncio.sleep(2)

        success = await booking_page.verify_booking_success()
        if success:
            web_logger.success(f"Booking verified for {date_str} - Desk {found_desk}")
            return True, found_desk
        else:
            web_logger.error(f"Booking verification failed for {date_str}")
            return False, None

    except Exception as e:
        web_logger.error(f"Error booking {date_str}: {e}")
        return False, None
