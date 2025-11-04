"""
Web Progress Reporter
Implements progress reporting for web interfaces using WebSocket or HTTP-based updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from src.interfaces.progress_reporter import ProgressReporter, BookingStatus, BookingState, ProgressUpdate


class WebSocketProgressReporter(ProgressReporter):
    """Progress reporter using WebSocket connections for real-time web updates"""

    def __init__(self, websocket_manager=None, booking_id: str = None, user_id: str = None):
        self.websocket_manager = websocket_manager
        self.booking_id = booking_id
        self.user_id = user_id
        self._logs: List[Dict[str, Any]] = []
        self._max_logs = 500

    async def report_status(self, status: BookingStatus):
        """Report booking status change via WebSocket"""
        if self.booking_id:
            status.booking_id = self.booking_id
        if self.user_id:
            status.user_id = self.user_id

        message = {
            "type": "status_update",
            "status": asdict(status),
            "timestamp": datetime.now().isoformat()
        }

        await self._send_message(message)

    async def report_progress(self, update: ProgressUpdate):
        """Report progress update via WebSocket"""
        message = {
            "type": "progress_update",
            "progress": asdict(update),
            "timestamp": datetime.now().isoformat()
        }

        await self._send_message(message)

    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error via WebSocket"""
        message = {
            "type": "error",
            "error": error,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        await self._send_message(message)

    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log message via WebSocket and store in buffer"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": (timestamp or datetime.now()).isoformat()
        }

        # Store in buffer
        self._logs.append(log_entry)
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]

        # Send via WebSocket
        message = {
            "type": "log",
            "log": log_entry
        }

        await self._send_message(message)

    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result via WebSocket"""
        message = {
            "type": "booking_result",
            "date": date,
            "success": success,
            "desk_code": desk_code,
            "timestamp": datetime.now().isoformat()
        }

        await self._send_message(message)

    async def _send_message(self, message: Dict[str, Any]):
        """Send message via WebSocket if available"""
        if self.websocket_manager and self.booking_id:
            try:
                await self.websocket_manager.send_to_booking(self.booking_id, message)
            except Exception as e:
                # Log error but don't fail - web interface might be disconnected
                print(f"WebSocket send failed: {e}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get stored logs"""
        return self._logs.copy()


class HTTPProgressReporter(ProgressReporter):
    """Progress reporter using HTTP callbacks (fallback when WebSocket not available)"""

    def __init__(self, callback_url: str = None, booking_id: str = None, user_id: str = None):
        self.callback_url = callback_url
        self.booking_id = booking_id
        self.user_id = user_id
        self._logs: List[Dict[str, Any]] = []
        self._max_logs = 500

    async def report_status(self, status: BookingStatus):
        """Report booking status change via HTTP callback"""
        if self.booking_id:
            status.booking_id = self.booking_id
        if self.user_id:
            status.user_id = self.user_id

        await self._send_http_update("status", asdict(status))

    async def report_progress(self, update: ProgressUpdate):
        """Report progress update via HTTP callback"""
        await self._send_http_update("progress", asdict(update))

    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error via HTTP callback"""
        data = {"error": error, "details": details}
        await self._send_http_update("error", data)

    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log message and store in buffer"""
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": (timestamp or datetime.now()).isoformat()
        }

        self._logs.append(log_entry)
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]

        await self._send_http_update("log", log_entry)

    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result via HTTP callback"""
        data = {"date": date, "success": success, "desk_code": desk_code}
        await self._send_http_update("booking_result", data)

    async def _send_http_update(self, update_type: str, data: Dict[str, Any]):
        """Send update via HTTP callback"""
        if not self.callback_url:
            return

        try:
            import aiohttp
            payload = {
                "type": update_type,
                "booking_id": self.booking_id,
                "user_id": self.user_id,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.callback_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        print(f"HTTP callback failed: {response.status}")
        except Exception as e:
            # Don't fail the booking process due to callback issues
            print(f"HTTP callback error: {e}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get stored logs"""
        return self._logs.copy()


class WebProgressReporter(ProgressReporter):
    """Unified web progress reporter that tries WebSocket first, falls back to HTTP"""

    def __init__(self, websocket_manager=None, callback_url: str = None,
                 booking_id: str = None, user_id: str = None):
        self.ws_reporter = WebSocketProgressReporter(websocket_manager, booking_id, user_id)
        self.http_reporter = HTTPProgressReporter(callback_url, booking_id, user_id)
        self.booking_id = booking_id
        self.user_id = user_id

    async def report_status(self, status: BookingStatus):
        """Report status via WebSocket or HTTP"""
        await self._try_websocket_then_http("report_status", status)

    async def report_progress(self, update: ProgressUpdate):
        """Report progress via WebSocket or HTTP"""
        await self._try_websocket_then_http("report_progress", update)

    async def report_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Report error via WebSocket or HTTP"""
        await self._try_websocket_then_http("report_error", error, details)

    async def report_log(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Report log via WebSocket or HTTP"""
        await self._try_websocket_then_http("report_log", level, message, timestamp)

    async def report_booking_result(self, date: str, success: bool, desk_code: Optional[str] = None):
        """Report booking result via WebSocket or HTTP"""
        await self._try_websocket_then_http("report_booking_result", date, success, desk_code)

    async def _try_websocket_then_http(self, method_name: str, *args, **kwargs):
        """Try WebSocket first, fall back to HTTP"""
        try:
            # Try WebSocket first
            method = getattr(self.ws_reporter, method_name)
            await method(*args, **kwargs)
        except Exception as ws_error:
            print(f"WebSocket reporting failed, trying HTTP: {ws_error}")
            try:
                # Fall back to HTTP
                method = getattr(self.http_reporter, method_name)
                await method(*args, **kwargs)
            except Exception as http_error:
                print(f"HTTP reporting also failed: {http_error}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get logs from WebSocket reporter (primary)"""
        return self.ws_reporter.get_logs()