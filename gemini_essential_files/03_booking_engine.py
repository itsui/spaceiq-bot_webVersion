"""
Core Booking Engine
Pure booking business logic without UI dependencies.
This is the heart of the booking system that can be controlled by any interface.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import uuid
import logging

from src.interfaces.progress_reporter import ProgressReporter, BookingStatus, BookingState, ProgressUpdate
from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from src.utils.supabase_validator import validate_user_from_auth_file


@dataclass
class BookingConfig:
    """Configuration for booking operations"""
    building: str = "LC"
    floor: str = "2"
    desk_prefix: str = "2.24"
    weekdays: List[int] = None  # [2, 3] for Wednesday, Thursday
    refresh_interval: int = 30
    max_attempts_per_date: int = 10
    headless: bool = True
    continuous_loop: bool = True
    skip_validation: bool = False
    booking_cutoff_hour: int = 18
    booking_cutoff_minute: int = 0
    browser_restart_interval: int = 50

    def __post_init__(self):
        if self.weekdays is None:
            self.weekdays = [2, 3]  # Wednesday, Thursday by default

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookingConfig':
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_file(cls, config_path: Path) -> 'BookingConfig':
        """Load from JSON file"""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)

            # Extract relevant fields
            return cls(
                building=data.get("building", "LC"),
                floor=data.get("floor", "2"),
                desk_prefix=data.get("desk_preferences", {}).get("prefix", "2.24"),
                weekdays=data.get("booking_days", {}).get("weekdays", [2, 3]),
                refresh_interval=data.get("wait_times", {}).get("rounds_1_to_5", {}).get("seconds", 30),
                headless=True,  # Always headless in web mode
                continuous_loop=True,  # Always continuous in web mode
                skip_validation=data.get("skip_validation", False),
                booking_cutoff_hour=data.get("booking_cutoff_hour", 18),
                booking_cutoff_minute=data.get("booking_cutoff_minute", 0),
                browser_restart_interval=data.get("browser_restart", {}).get("restart_every_n_rounds", 50)
            )
        except Exception as e:
            logging.error(f"Failed to load config from {config_path}: {e}")
            return cls()  # Return default config


@dataclass
class BookingRequest:
    """Request for booking operation"""
    user_id: str
    config: BookingConfig
    dates_to_try: Optional[List[str]] = None
    booking_id: Optional[str] = None

    def __post_init__(self):
        if self.booking_id is None:
            self.booking_id = str(uuid.uuid4())


@dataclass
class BookingResult:
    """Result of booking operation"""
    booking_id: str
    user_id: str
    success: bool
    results: Dict[str, bool]  # date -> success mapping
    successful_bookings: int
    total_attempts: int
    dates_processed: List[str]
    error_message: Optional[str] = None
    start_time: datetime = None
    end_time: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

    def finalize(self):
        """Finalize the result with end time"""
        self.end_time = datetime.now()

    @property
    def duration(self) -> Optional[timedelta]:
        """Get operation duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class BookingEngine:
    """Core booking engine with pure business logic"""

    def __init__(self, progress_reporter: ProgressReporter):
        self.progress_reporter = progress_reporter
        self.logger = logging.getLogger(__name__)
        self._current_status: Optional[BookingStatus] = None

    async def execute_booking(self, request: BookingRequest, auth_file: str = None) -> BookingResult:
        """
        Execute the complete booking workflow

        Args:
            request: Booking request with configuration

        Returns:
            BookingResult with comprehensive results
        """
        # Initialize booking status
        status = BookingStatus(
            booking_id=request.booking_id,
            user_id=request.user_id,
            state=BookingState.PENDING,
            message="Initializing booking system...",
            total_dates=len(request.dates_to_try) if request.dates_to_try else 0
        )

        self._current_status = status
        await self.progress_reporter.report_status(status)

        result = BookingResult(
            booking_id=request.booking_id,
            user_id=request.user_id,
            success=False,
            results={},
            successful_bookings=0,
            total_attempts=0,
            dates_processed=[]
        )

        try:
            # Validate user if required
            if not request.config.skip_validation:
                await self._validate_user()

            # Initialize session manager
            await self.progress_reporter.report_status(BookingStatus(
                booking_id=request.booking_id,
                user_id=request.user_id,
                state=BookingState.AUTHENTICATING,
                message="Setting up authentication session..."
            ))

            session_manager = SessionManager(headless=request.config.headless, auth_file=auth_file)

            # Validate session for headless mode
            if request.config.headless:
                success = await self._validate_session(session_manager, request)
                if not success:
                    result.error_message = "Session validation failed"
                    return result

            # Start the booking workflow
            results = await self._run_booking_workflow(
                request, session_manager, result
            )

            # Finalize result
            result.results = results
            result.successful_bookings = sum(1 for success in results.values() if success)
            result.total_attempts = len(results)
            result.dates_processed = list(results.keys())
            result.success = result.successful_bookings > 0

            return result

        except Exception as e:
            error_msg = f"Fatal error in booking workflow: {e}"
            self.logger.error(error_msg)
            await self.progress_reporter.report_error(error_msg)

            result.error_message = str(e)
            result.success = False
            return result

        finally:
            result.finalize()

    async def _validate_user(self):
        """Validate user against whitelist if configured"""
        is_valid, error_msg = validate_user_from_auth_file(skip_validation=False)
        if not is_valid:
            await self.progress_reporter.report_error(error_msg)
            raise ValueError(error_msg)

    async def _validate_session(self, session_manager: SessionManager, request: BookingRequest) -> bool:
        """Validate and refresh session for headless mode"""
        await self.progress_reporter.report_log("INFO", "Validating session for headless mode...")

        try:
            from src.auth.session_validator import validate_and_refresh_session
            session_valid, use_headless = await validate_and_refresh_session(force_headless=True)

            if not session_valid:
                await self.progress_reporter.report_error("Session validation failed")
                return False

            # Update headless setting
            request.config.headless = use_headless
            session_manager.headless = use_headless

            await self.progress_reporter.report_log("INFO", "Session validation successful")
            return True

        except Exception as e:
            await self.progress_reporter.report_error(f"Session validation error: {e}")
            return False

    async def _run_booking_workflow(self, request: BookingRequest, session_manager: SessionManager, result: BookingResult) -> Dict[str, bool]:
        """Run the main booking workflow"""
        config = request.config

        # Calculate dates to try
        dates_to_try = self._calculate_dates(config)
        if request.dates_to_try:
            # Use provided dates if available
            dates_to_try = [d for d in request.dates_to_try if d in dates_to_try]

        if not dates_to_try:
            await self.progress_reporter.report_error("No eligible dates found")
            return {}

        await self.progress_reporter.report_log("INFO", f"Found {len(dates_to_try)} dates to book: {dates_to_try}")

        # Initialize session
        context = await session_manager.initialize()
        page = await context.new_page()
        booking_page = SpaceIQBookingPage(page)

        # Navigate to SpaceIQ
        await self.progress_reporter.report_status(BookingStatus(
            booking_id=request.booking_id,
            user_id=request.user_id,
            state=BookingState.NAVIGATING,
            message="Navigating to SpaceIQ...",
            total_dates=len(dates_to_try)
        ))

        await booking_page.navigate_to_floor_view(config.building, config.floor)

        results = {}
        round_num = 1

        try:
            while True:
                await self.progress_reporter.report_status(BookingStatus(
                    booking_id=request.booking_id,
                    user_id=request.user_id,
                    state=BookingState.WAITING,
                    message=f"Starting Round {round_num}",
                    current_round=round_num
                ))

                # Check existing bookings
                existing_bookings = await self._check_existing_bookings(booking_page, request)

                # Calculate dates for this round
                dates_to_try_now = self._filter_available_dates(dates_to_try, existing_bookings, config)

                if not dates_to_try_now:
                    if existing_bookings and config.continuous_loop:
                        await self._wait_for_next_round(config, round_num, "All dates already booked")
                        round_num += 1
                        continue
                    else:
                        break

                # Try booking each date
                round_results = await self._process_dates_round(
                    dates_to_try_now, booking_page, request, round_num
                )

                results.update(round_results)

                # Check if we should continue
                if not config.continuous_loop:
                    break

                if any(round_results.values()):
                    await self.progress_reporter.report_log("INFO", "Round successful - continuing")
                    await asyncio.sleep(2)
                else:
                    await self._wait_for_next_round(config, round_num, "No bookings this round")

                round_num += 1

                # Restart browser periodically
                if round_num % config.browser_restart_interval == 0:
                    await self._restart_browser(booking_page, session_manager, config, request)

        finally:
            await session_manager.close()

        return results

    def _calculate_dates(self, config: BookingConfig) -> List[str]:
        """Calculate eligible dates for booking"""
        today = datetime.now().date()
        furthest_date = today + timedelta(weeks=4, days=1)  # 29 days

        dates = []
        current_date = today

        while current_date <= furthest_date:
            if current_date.weekday() in config.weekdays:
                if current_date >= today:
                    dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)

        dates.sort(reverse=True)  # Furthest first
        return dates

    async def _check_existing_bookings(self, booking_page: SpaceIQBookingPage, request: BookingRequest) -> List[str]:
        """Check existing bookings"""
        await self.progress_reporter.report_status(BookingStatus(
            booking_id=request.booking_id,
            user_id=request.user_id,
            state=BookingState.CHECKING_BOOKINGS,
            message="Checking existing bookings..."
        ))

        try:
            existing_bookings = await booking_page.get_existing_bookings(logger=self.logger)
            await self.progress_reporter.report_log("INFO", f"Found {len(existing_bookings)} existing bookings")
            return existing_bookings
        except Exception as e:
            await self.progress_reporter.report_error(f"Error checking existing bookings: {e}")
            return []

    def _filter_available_dates(self, dates_to_try: List[str], existing_bookings: List[str], config: BookingConfig) -> List[str]:
        """Filter dates that are still available for booking"""
        today = datetime.now().date()
        available_dates = []

        for date_str in dates_to_try:
            # Skip if already booked
            if date_str in existing_bookings:
                continue

            # Check cutoff time for today
            if date_str == today.strftime("%Y-%m-%d"):
                current_time = datetime.now()
                cutoff_time = current_time.replace(
                    hour=config.booking_cutoff_hour,
                    minute=config.booking_cutoff_minute,
                    second=0,
                    microsecond=0
                )
                if current_time >= cutoff_time:
                    self.logger.info(f"Skipping today ({date_str}) - after cutoff time")
                    continue

            available_dates.append(date_str)

        available_dates.sort(reverse=True)
        return available_dates

    async def _process_dates_round(self, dates_to_try: List[str], booking_page: SpaceIQBookingPage, request: BookingRequest, round_num: int) -> Dict[str, bool]:
        """Process one round of booking attempts"""
        results = {}

        for idx, date_str in enumerate(dates_to_try, 1):
            await self.progress_reporter.report_status(BookingStatus(
                booking_id=request.booking_id,
                user_id=request.user_id,
                state=BookingState.SEARCHING_DESKS,
                message=f"Booking {date_str}",
                current_date=date_str,
                processed_dates=idx - 1,
                progress_percentage=(idx - 1) / len(dates_to_try) * 100
            ))

            success, desk_code = await self._try_booking_date(
                booking_page, date_str, request, idx, len(dates_to_try)
            )

            results[date_str] = success

            # Report result
            await self.progress_reporter.report_booking_result(date_str, success, desk_code)

            # Update progress
            await self.progress_reporter.report_progress(ProgressUpdate(
                current=idx,
                total=len(dates_to_try),
                message=f"Processed {date_str}: {'SUCCESS' if success else 'SKIPPED'}"
            ))

        return results

    async def _try_booking_date(self, booking_page: SpaceIQBookingPage, date_str: str, request: BookingRequest, idx: int, total: int) -> tuple[bool, str]:
        """Try booking a specific date"""
        try:
            config = request.config
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            days_ahead = (target_date.date() - datetime.now().date()).days

            # Navigate and select date
            await booking_page.navigate_to_floor_view(config.building, config.floor)
            await booking_page.click_book_desk_button()
            await booking_page.open_date_picker()

            try:
                await booking_page.select_date_from_calendar(days_ahead=days_ahead)
            except Exception as e:
                if "disabled" in str(e).lower() or "beyond booking window" in str(e).lower():
                    await self.progress_reporter.report_log("WARNING", f"Date {date_str} is beyond booking window")
                    return False, None
                else:
                    raise

            await booking_page.click_update_button()
            await booking_page.wait_for_floor_map_to_load()
            await asyncio.sleep(7)  # Wait for SVG to render

            # Check available desks
            available_desks = await booking_page.get_available_desks_from_sidebar(
                desk_prefix=config.desk_prefix,
                logger=self.logger
            )

            if not available_desks:
                await self.progress_reporter.report_log("INFO", f"No {config.desk_prefix}.* desks available for {date_str}")
                return False, None

            await self.progress_reporter.report_log("INFO", f"Found {len(available_desks)} desks: {', '.join(available_desks[:3])}")

            # Sort by priority if configured
            priority_config = self._get_priority_config(request)
            if priority_config:
                try:
                    from src.utils.desk_priority import sort_desks_by_priority
                    available_desks = sort_desks_by_priority(available_desks, priority_config)
                except Exception as e:
                    await self.progress_reporter.report_log("WARNING", f"Error sorting desks by priority: {e}")

            # Find and click desk
            found_desk = await booking_page.find_and_click_available_desks(
                available_desks=available_desks,
                logger=self.logger
            )

            if not found_desk:
                await self.progress_reporter.report_log("ERROR", f"Could not locate desk on map for {date_str}")
                return False, None

            await self.progress_reporter.report_log("INFO", f"Clicked desk {found_desk}, submitting booking...")
            await booking_page.click_book_now_in_popup()
            await asyncio.sleep(2)

            success = await booking_page.verify_booking_success()
            if success:
                await self.progress_reporter.report_status(BookingStatus(
                    booking_id=request.booking_id,
                    user_id=request.user_id,
                    state=BookingState.SUCCESS,
                    message=f"Successfully booked {date_str} - Desk {found_desk}",
                    current_date=date_str,
                    desk_code=found_desk
                ))

                # Play success sound
                try:
                    from src.utils.sound_notification import play_booking_success_alert
                    play_booking_success_alert()
                except:
                    pass  # Ignore sound errors in headless mode

                return True, found_desk
            else:
                await self.progress_reporter.report_log("ERROR", f"Booking verification failed for {date_str}")
                return False, None

        except Exception as e:
            await self.progress_reporter.report_error(f"Error booking {date_str}: {e}")
            return False, None

    def _get_priority_config(self, request: BookingRequest) -> List[Dict]:
        """Get priority configuration from request"""
        # This would come from the request config in a real implementation
        # For now, return empty list
        return []

    async def _wait_for_next_round(self, config: BookingConfig, round_num: int, message: str):
        """Wait before next round with progressive timing"""
        if round_num <= 5:
            wait_time = 60  # 1 minute
        elif round_num <= 15:
            wait_time = 300  # 5 minutes
        else:
            wait_time = 900  # 15 minutes

        await self.progress_reporter.report_status(BookingStatus(
            booking_id=self._current_status.booking_id if self._current_status else "",
            user_id=self._current_status.user_id if self._current_status else "",
            state=BookingState.WAITING,
            message=f"{message} - waiting {wait_time}s for next round"
        ))

        # Wait with countdown updates
        for remaining in range(wait_time, 0, -1):
            await self.progress_reporter.report_progress(ProgressUpdate(
                current=wait_time - remaining,
                total=wait_time,
                message=f"Waiting for next round: {remaining}s remaining"
            ))
            await asyncio.sleep(1)

    async def _restart_browser(self, booking_page: SpaceIQBookingPage, session_manager: SessionManager, config: BookingConfig, request: BookingRequest):
        """Restart browser to prevent degradation"""
        await self.progress_reporter.report_log("INFO", "Restarting browser to prevent degradation")

        try:
            await booking_page.page.close()
            await session_manager.close()
            await asyncio.sleep(2)

            context = await session_manager.initialize()
            page = await context.new_page()
            booking_page = SpaceIQBookingPage(page)
            await booking_page.navigate_to_floor_view(config.building, config.floor)

            await self.progress_reporter.report_log("INFO", "Browser restarted successfully")
        except Exception as e:
            await self.progress_reporter.report_error(f"Browser restart failed: {e}")

    async def cancel_booking(self, booking_id: str):
        """Cancel an ongoing booking operation"""
        # This would need to be implemented with proper cancellation logic
        # For now, just report cancellation
        await self.progress_reporter.report_status(BookingStatus(
            booking_id=booking_id,
            user_id="",
            state=BookingState.CANCELLED,
            message="Booking operation cancelled by user"
        ))