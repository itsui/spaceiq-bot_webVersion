"""
Unified Booking Adapter
Adapter that allows the new booking engine to work with existing code patterns
while providing a clean migration path to the new architecture.
"""

import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from src.core.booking_engine import BookingEngine, BookingRequest, BookingConfig
from src.interfaces.progress_reporter import ProgressReporter
from src.reporters.console_progress_reporter import ConsoleProgressReporter
from src.reporters.web_progress_reporter import WebProgressReporter


class UnifiedBookingAdapter:
    """
    Adapter that provides both old and new interfaces for booking operations.
    This allows gradual migration from the old architecture to the new one.
    """

    def __init__(self, progress_reporter: Optional[ProgressReporter] = None):
        """
        Initialize the adapter with an optional progress reporter.

        Args:
            progress_reporter: Progress reporter (defaults to ConsoleProgressReporter)
        """
        if progress_reporter is None:
            progress_reporter = ConsoleProgressReporter()

        self.booking_engine = BookingEngine(progress_reporter)
        self.progress_reporter = progress_reporter

    # Legacy interface - maintains backward compatibility
    async def run_multi_date_booking_legacy(
        self,
        refresh_interval: int = 30,
        max_attempts_per_date: int = 10,
        polling_mode: bool = False,
        headless: bool = False,
        continuous_loop: bool = False,
        skip_validation: bool = False,
        config_path: Optional[Path] = None
    ) -> Dict[str, bool]:
        """
        Legacy interface that matches the original run_multi_date_booking function.

        This maintains backward compatibility with existing code.
        """
        # Load config
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "booking_config.json"

        config = BookingConfig.from_file(config_path)

        # Override with provided parameters
        config.refresh_interval = refresh_interval
        config.max_attempts_per_date = max_attempts_per_date
        config.headless = headless
        config.continuous_loop = continuous_loop or headless  # Headless implies continuous
        config.skip_validation = skip_validation

        # Create request
        request = BookingRequest(
            user_id="legacy_user",  # Default user for legacy mode
            config=config
        )

        # Execute booking
        result = await self.booking_engine.execute_booking(request)

        # Return in the expected format (dict mapping date -> success)
        return result.results

    async def run_multi_date_booking_new(
        self,
        refresh_interval: int = 30,
        max_attempts_per_date: int = 10,
        polling_mode: bool = False,
        headless: bool = False,
        continuous_loop: bool = False,
        skip_validation: bool = False,
        config: Dict = None
    ) -> Dict[str, bool]:
        """
        New interface that properly handles multi-user auth files from web mode.

        This interface uses the config parameter to extract user-specific auth files.
        """
        # Create booking config from provided config dict
        booking_config = BookingConfig(
            building=config.get('building', 'LC'),
            floor=config.get('floor', '2'),
            desk_prefix=config.get('desk_prefix', '2.24'),
            weekdays=config.get('weekdays', [2, 3]),
            refresh_interval=refresh_interval,
            max_attempts_per_date=max_attempts_per_date,
            headless=headless,
            continuous_loop=continuous_loop,
            skip_validation=skip_validation,
            booking_cutoff_hour=config.get('booking_cutoff_hour', 18),
            booking_cutoff_minute=config.get('booking_cutoff_minute', 0),
            browser_restart_interval=config.get('browser_restart_interval', 50)
        )

        # Create request with user_id and auth_file from config
        request = BookingRequest(
            user_id=config.get('user_id', 'web_user'),
            config=booking_config
        )

        # Store auth_file in request for later use by SessionManager
        request.auth_file = config.get('auth_file')

        # Execute booking
        result = await self.booking_engine.execute_booking(request, auth_file=request.auth_file)

        # Return in the expected format (dict mapping date -> success)
        return result.results

    # New interface - clean, modern API
    async def execute_booking_request(self, request: BookingRequest) -> Dict[str, Any]:
        """
        New interface using BookingRequest objects.

        Args:
            request: BookingRequest with all necessary parameters

        Returns:
            Dictionary with comprehensive booking results
        """
        result = await self.booking_engine.execute_booking(request)

        return {
            "booking_id": result.booking_id,
            "user_id": result.user_id,
            "success": result.success,
            "results": result.results,
            "successful_bookings": result.successful_bookings,
            "total_attempts": result.total_attempts,
            "dates_processed": result.dates_processed,
            "error_message": result.error_message,
            "duration": str(result.duration) if result.duration else None,
            "start_time": result.start_time.isoformat() if result.start_time else None,
            "end_time": result.end_time.isoformat() if result.end_time else None
        }

    # Simplified interface for web usage
    async def start_booking_for_user(
        self,
        user_id: str,
        config: Dict[str, Any],
        dates_to_try: Optional[list[str]] = None,
        websocket_manager=None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simplified interface for web-based booking control.

        Args:
            user_id: User identifier
            config: Configuration dictionary
            dates_to_try: Optional list of specific dates to try
            websocket_manager: WebSocket manager for real-time updates
            callback_url: HTTP callback URL (fallback)

        Returns:
            Dictionary with booking operation details
        """
        # Create progress reporter
        if websocket_manager or callback_url:
            progress_reporter = WebProgressReporter(
                websocket_manager=websocket_manager,
                callback_url=callback_url,
                user_id=user_id
            )
            # Replace the engine's progress reporter
            self.booking_engine.progress_reporter = progress_reporter
            self.progress_reporter = progress_reporter

        # Create booking config
        booking_config = BookingConfig.from_dict(config)

        # Create booking request
        request = BookingRequest(
            user_id=user_id,
            config=booking_config,
            dates_to_try=dates_to_try
        )

        # Execute booking
        result = await self.booking_engine.execute_booking(request)

        return {
            "booking_id": result.booking_id,
            "status": "started",
            "message": "Booking process initiated",
            "config": config,
            "estimated_duration": "2-30 minutes depending on availability"
        }

    async def cancel_booking(self, booking_id: str) -> bool:
        """
        Cancel an ongoing booking operation.

        Args:
            booking_id: ID of the booking to cancel

        Returns:
            True if cancellation was successful
        """
        try:
            await self.booking_engine.cancel_booking(booking_id)
            return True
        except Exception:
            return False

    def get_booking_logs(self) -> list[Dict[str, Any]]:
        """
        Get logs from the current progress reporter if available.

        Returns:
            List of log entries
        """
        if hasattr(self.progress_reporter, 'get_logs'):
            return self.progress_reporter.get_logs()
        return []

    async def check_booking_status(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """
        Check the status of an ongoing booking.

        Args:
            booking_id: ID of the booking to check

        Returns:
            Status information or None if not found
        """
        # This would need to be implemented with a booking tracking system
        # For now, return current status if it matches
        if (hasattr(self.booking_engine, '_current_status') and
            self.booking_engine._current_status and
            self.booking_engine._current_status.booking_id == booking_id):

            status = self.booking_engine._current_status
            return {
                "booking_id": status.booking_id,
                "user_id": status.user_id,
                "state": status.state.value,
                "message": status.message,
                "current_date": status.current_date,
                "progress_percentage": status.progress_percentage,
                "successful_bookings": status.successful_bookings,
                "failed_attempts": status.failed_attempts,
                "current_round": status.current_round,
                "updated_at": status.updated_at.isoformat() if status.updated_at else None
            }

        return None


class BackwardCompatibilityWrapper:
    """
    Wrapper that provides the exact same interface as the original multi_date_booking module
    while using the new architecture underneath.
    """

    def __init__(self):
        self.adapter = UnifiedBookingAdapter()

    async def run_multi_date_booking(
        self,
        refresh_interval: int = 30,
        max_attempts_per_date: int = 10,
        polling_mode: bool = False,
        headless: bool = False,
        continuous_loop: bool = False,
        skip_validation: bool = False,
        config: Dict = None,
        web_logger = None
    ) -> Dict[str, bool]:
        """
        Drop-in replacement for the original run_multi_date_booking function.

        This maintains 100% backward compatibility with existing code.
        """
        # If web_logger is provided, create a web progress reporter
        if web_logger is not None:
            # Convert web_logger to progress reporter
            from src.reporters.web_progress_reporter import WebProgressReporter

            # Create a simple adapter that converts web_logger calls to progress reports
            class WebLoggerAdapter:
                def __init__(self, web_logger):
                    self.web_logger = web_logger

                async def report_status(self, status):
                    self.web_logger.info(f"[{status.state.value}] {status.message}")

                async def report_progress(self, update):
                    self.web_logger.info(f"Progress: {update.current}/{update.total} ({update.percentage:.1f}%)")

                async def report_error(self, error, details=None):
                    self.web_logger.error(f"ERROR: {error}")
                    if details:
                        self.web_logger.error(f"Details: {details}")

                async def report_log(self, level, message, timestamp=None):
                    getattr(self.web_logger, level.lower(), self.web_logger.info)(message)

                async def report_booking_result(self, date, success, desk_code=None):
                    if success:
                        self.web_logger.success(f"Booked {date} - Desk {desk_code}")
                    else:
                        self.web_logger.info(f"Skipped {date} - No desks available")

            progress_reporter = WebLoggerAdapter(web_logger)
            adapter = UnifiedBookingAdapter(progress_reporter)
        else:
            adapter = self.adapter

        # If config is provided, use the new interface with proper multi-user support
        if config is not None:
            return await adapter.run_multi_date_booking_new(
                refresh_interval=refresh_interval,
                max_attempts_per_date=max_attempts_per_date,
                polling_mode=polling_mode,
                headless=headless,
                continuous_loop=continuous_loop,
                skip_validation=skip_validation,
                config=config
            )
        else:
            # Use the legacy interface for backward compatibility
            return await adapter.run_multi_date_booking_legacy(
                refresh_interval=refresh_interval,
                max_attempts_per_date=max_attempts_per_date,
                polling_mode=polling_mode,
                headless=headless,
                continuous_loop=continuous_loop,
                skip_validation=skip_validation
            )


# Global instance for backward compatibility
_backward_wrapper = BackwardCompatibilityWrapper()


# Export functions that maintain the original interface
async def run_multi_date_booking(
    refresh_interval: int = 30,
    max_attempts_per_date: int = 10,
    polling_mode: bool = False,
    headless: bool = False,
    continuous_loop: bool = False,
    skip_validation: bool = False,
    config: Dict = None,
    web_logger = None
) -> Dict[str, bool]:
    """
    Drop-in replacement for the original run_multi_date_booking function.

    This function maintains 100% backward compatibility while using the new architecture.
    """
    return await _backward_wrapper.run_multi_date_booking(
        refresh_interval=refresh_interval,
        max_attempts_per_date=max_attempts_per_date,
        polling_mode=polling_mode,
        headless=headless,
        continuous_loop=continuous_loop,
        skip_validation=skip_validation,
        config=config,
        web_logger=web_logger
    )