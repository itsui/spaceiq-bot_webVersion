"""
Console Progress Reporter
Implements progress reporting using Rich console UI (preserves existing functionality).
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.interfaces.progress_reporter import ProgressReporter, BookingStatus, BookingState, ProgressUpdate
from src.utils.rich_ui import ui, DateStatus


class ConsoleProgressReporter(ProgressReporter):
    """Progress reporter using Rich console UI"""

    def __init__(self):
        self.booking_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self._initial_dates: list[str] = []

    async def report_status(self, status: BookingStatus):
        """Report booking status change to Rich UI"""
        self.booking_id = status.booking_id
        self.user_id = status.user_id

        # Map booking states to Rich UI operations
        state_mapping = {
            BookingState.PENDING: ("Preparing", "Initializing booking system..."),
            BookingState.AUTHENTICATING: ("Authenticating", "Logging into SpaceIQ..."),
            BookingState.NAVIGATING: ("Navigating", "Opening SpaceIQ booking page..."),
            BookingState.CHECKING_BOOKINGS: ("Checking existing bookings", "Fetching calendar data..."),
            BookingState.SEARCHING_DESKS: ("Searching desks", f"Looking for available desks for {status.current_date}..."),
            BookingState.BOOKING: ("Booking", f"Attempting to book {status.current_date}..."),
            BookingState.SUCCESS: ("Success", f"Successfully booked {status.current_date} - Desk {status.desk_code}"),
            BookingState.FAILED: ("Failed", f"Failed to book {status.current_date}: {status.message}"),
            BookingState.CANCELLED: ("Cancelled", "Booking process cancelled"),
            BookingState.WAITING: ("Waiting", status.message),
        }

        if status.state in state_mapping:
            operation, message = state_mapping[status.state]
            ui.set_operation(operation, message)
            ui.log_activity(message)

        # Update round number
        if status.current_round != ui.current_round:
            ui.current_round = status.current_round

        # Update date status if we have a current date
        if status.current_date:
            if status.state == BookingState.SUCCESS:
                ui.set_date_status(status.current_date, DateStatus.SUCCESS, desk=status.desk_code)
            elif status.state == BookingState.FAILED:
                ui.set_date_status(status.current_date, DateStatus.SKIPPED)
            elif status.state == BookingState.SEARCHING_DESKS:
                attempt_num = ui.date_attempts.get(status.current_date, 0) + 1
                ui.set_date_status(status.current_date, DateStatus.TRYING, attempt=attempt_num)

    async def report_progress(self, update: ProgressUpdate):
        """Report progress update to Rich UI"""
        # Rich UI doesn't have a generic progress bar, but we can log it
        percentage = update.percentage
        ui.log_activity(f"Progress: {update.current}/{update.total} ({percentage:.1f}%) - {update.message}")

    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error to Rich UI"""
        ui.log_activity(f"ERROR: {error}")
        if details:
            ui.log_activity(f"Error details: {details}")

    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log message to Rich UI"""
        if timestamp:
            formatted_message = f"[{timestamp.strftime('%H:%M:%S')}] [{level}] {message}"
        else:
            formatted_message = f"[{level}] {message}"

        ui.log_activity(formatted_message)

    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result for specific date"""
        if success:
            ui.set_date_status(date, DateStatus.SUCCESS, desk=desk_code)
            ui.log_activity(f"SUCCESS: Booked {date} - Desk {desk_code}")
        else:
            ui.set_date_status(date, DateStatus.SKIPPED)
            ui.log_activity(f"SKIPPED: {date} - No available desks")

    def initialize_dates(self, dates: list[str]):
        """Initialize Rich UI with dates to process"""
        self._initial_dates = dates.copy()
        ui.initialize_dates(dates)

    def start_countdown(self, seconds: int, message: str):
        """Start countdown in Rich UI"""
        ui.start_countdown(seconds, message)

    def update_countdown(self):
        """Update countdown display"""
        ui.update_countdown()

    def stop_countdown(self):
        """Stop countdown display"""
        ui.stop_countdown()

    def finalize_session(self, results: Dict[str, bool]):
        """Finalize the Rich UI session with results"""
        ui.stop_live_dashboard()
        ui.print_summary_table(results)