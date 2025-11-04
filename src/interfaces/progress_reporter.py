"""
Progress Reporter Interfaces
Abstract interfaces for reporting progress from bot operations to different UI backends.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


class BookingState(Enum):
    """Booking process states"""
    PENDING = "pending"
    AUTHENTICATING = "authenticating"
    NAVIGATING = "navigating"
    CHECKING_BOOKINGS = "checking_bookings"
    SEARCHING_DESKS = "searching_desks"
    BOOKING = "booking"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"


@dataclass
class BookingStatus:
    """Comprehensive booking status information"""
    booking_id: str
    user_id: str
    state: BookingState
    message: str
    current_date: Optional[str] = None
    total_dates: int = 0
    processed_dates: int = 0
    successful_bookings: int = 0
    failed_attempts: int = 0
    current_round: int = 1
    progress_percentage: float = 0.0
    desk_code: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()


@dataclass
class ProgressUpdate:
    """Generic progress update information"""
    current: int
    total: int
    message: str
    details: Optional[Dict[str, Any]] = None

    @property
    def percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0


class ProgressReporter(ABC):
    """Abstract base class for progress reporting"""

    @abstractmethod
    async def report_status(self, status: BookingStatus):
        """Report booking status change"""
        pass

    @abstractmethod
    async def report_progress(self, update: ProgressUpdate):
        """Report progress update"""
        pass

    @abstractmethod
    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error occurrence"""
        pass

    @abstractmethod
    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log message"""
        pass

    @abstractmethod
    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result for specific date"""
        pass


class MultiProgressReporter(ProgressReporter):
    """Composite progress reporter that forwards to multiple reporters"""

    def __init__(self):
        self.reporters: list[ProgressReporter] = []

    def add_reporter(self, reporter: ProgressReporter):
        """Add a progress reporter"""
        self.reporters.append(reporter)

    def remove_reporter(self, reporter: ProgressReporter):
        """Remove a progress reporter"""
        if reporter in self.reporters:
            self.reporters.remove(reporter)

    async def report_status(self, status: BookingStatus):
        """Report status to all reporters"""
        await asyncio.gather(*[
            reporter.report_status(status)
            for reporter in self.reporters
        ], return_exceptions=True)

    async def report_progress(self, update: ProgressUpdate):
        """Report progress to all reporters"""
        await asyncio.gather(*[
            reporter.report_progress(update)
            for reporter in self.reporters
        ], return_exceptions=True)

    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error to all reporters"""
        await asyncio.gather(*[
            reporter.report_error(error, details)
            for reporter in self.reporters
        ], return_exceptions=True)

    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log to all reporters"""
        await asyncio.gather(*[
            reporter.report_log(level, message, timestamp)
            for reporter in self.reporters
        ], return_exceptions=True)

    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result to all reporters"""
        await asyncio.gather(*[
            reporter.report_booking_result(date, success, desk_code)
            for reporter in self.reporters
        ], return_exceptions=True)