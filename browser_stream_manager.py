"""
Browser Stream Manager
Manages browser streaming sessions for remote authentication
"""

import asyncio
import base64
import json
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
import logging

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger('browser_stream')

class BrowserStreamSession:
    """Represents an active browser streaming session"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.current_url = "about:blank"
        self.authenticated = False
        self.last_screenshot = None
        self.started_at = datetime.utcnow()

    async def start(self, target_url: str = "https://main.spaceiq.com/login"):
        """Start the browser session"""
        try:
            logger.info(f"Starting browser stream for user {self.user_id}...")

            self.playwright = await async_playwright().start()
            logger.info("Playwright started")

            # Launch browser in headless mode for server deployment
            # Screenshots will be captured and streamed
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Headless for server - no window opens
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                ]
            )
            logger.info("Browser launched")

            # Create new context
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            logger.info("Context created")

            # Create page
            self.page = await self.context.new_page()
            logger.info("Page created")

            # Start monitoring for authentication
            self.page.on('framenavigated', self._on_navigation)

            # Navigate to target
            logger.info(f"Navigating to {target_url}...")
            await self.page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
            self.current_url = self.page.url
            logger.info(f"Navigation complete. Current URL: {self.current_url}")

            # Take initial screenshot to verify it works
            test_screenshot = await self.page.screenshot(type='jpeg', quality=80)
            logger.info(f"Initial screenshot captured: {len(test_screenshot)} bytes")

            logger.info(f"✓ Browser stream started successfully for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start browser stream: {e}", exc_info=True)
            await self.stop()
            return False

    async def _on_navigation(self, frame):
        """Handle page navigation"""
        if frame == self.page.main_frame:
            self.current_url = self.page.url
            logger.info(f"Navigation: {self.current_url}")

            # Check if authenticated (redirected to finder page after login)
            if '/finder' in self.current_url and 'spaceiq.com' in self.current_url:
                self.authenticated = True
                logger.info(f"✓ Authentication detected for user {self.user_id}! URL: {self.current_url}")

    async def get_screenshot(self) -> Optional[str]:
        """Get current screenshot as base64"""
        try:
            if not self.page:
                logger.warning("No page available for screenshot")
                return self.last_screenshot

            # Don't wait for load state - capture whatever is currently visible
            # This prevents blocking during heavy page loads (like Okta SSO)
            screenshot_bytes = await self.page.screenshot(type='jpeg', quality=20)
            self.last_screenshot = base64.b64encode(screenshot_bytes).decode('utf-8')
            logger.debug(f"Screenshot captured: {len(self.last_screenshot)} bytes")
            return self.last_screenshot

        except Exception as e:
            logger.debug(f"Screenshot error (returning cached): {e}")
            return self.last_screenshot

    async def click(self, x: int, y: int):
        """Simulate click at coordinates"""
        try:
            if self.page:
                await self.page.mouse.click(x, y)
        except Exception as e:
            logger.error(f"Click error: {e}")

    async def type_text(self, text: str):
        """Type text"""
        try:
            if self.page:
                await self.page.keyboard.type(text)
                # Small delay to let page render the typed text before next screenshot
                # This prevents screenshots from capturing intermediate/partial render states
                await asyncio.sleep(0.05)  # 50ms should be enough for DOM to update
        except Exception as e:
            logger.error(f"Type error: {e}")

    async def press_key(self, key: str):
        """Press a key"""
        try:
            if self.page:
                await self.page.keyboard.press(key)
        except Exception as e:
            logger.error(f"Key press error: {e}")

    async def save_session(self, output_path: str) -> bool:
        """Save the authenticated session"""
        try:
            if not self.context:
                logger.error("Cannot save session: browser context is None")
                return False

            if not self.authenticated:
                logger.warning("Attempting to save session before authentication detected")
                # Allow saving even if not authenticated (user might have logged in but URL didn't match)

            # Save storage state (cookies, localStorage, etc.)
            await self.context.storage_state(path=output_path)

            # CRITICAL: Wait for file to be fully written to disk
            # On Windows especially, file writes may be buffered
            await asyncio.sleep(0.5)  # Increased from 0.1s to 0.5s

            # Validate that file was written and has content
            import os
            session_path = Path(output_path)
            if not session_path.exists():
                logger.error(f"Session file was not created at {output_path}")
                return False

            file_size = os.path.getsize(output_path)
            if file_size == 0:
                logger.error(f"Session file is empty (0 bytes) at {output_path}")
                return False

            if file_size < 10:  # Minimum valid JSON would be at least 10 bytes
                logger.error(f"Session file is too small ({file_size} bytes), likely invalid")
                return False

            logger.info(f"✓ Session saved successfully ({file_size} bytes) for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session for user {self.user_id}: {e}", exc_info=True)
            return False

    async def stop(self):
        """Stop the browser session"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            logger.info(f"Browser stream stopped for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error stopping browser stream: {e}")


class BrowserStreamManager:
    """Manages multiple browser streaming sessions"""

    def __init__(self):
        self.sessions: Dict[int, BrowserStreamSession] = {}
        self.lock = asyncio.Lock()

    async def start_session(self, user_id: int, target_url: str = "https://main.spaceiq.com/login") -> bool:
        """Start a new streaming session for a user"""
        async with self.lock:
            # Stop existing session if any
            if user_id in self.sessions:
                await self.stop_session(user_id)

            # Create new session
            session = BrowserStreamSession(user_id)
            success = await session.start(target_url)

            if success:
                self.sessions[user_id] = session
                return True
            return False

    async def stop_session(self, user_id: int):
        """Stop a streaming session"""
        async with self.lock:
            if user_id in self.sessions:
                session = self.sessions[user_id]
                await session.stop()
                del self.sessions[user_id]

    def get_session(self, user_id: int) -> Optional[BrowserStreamSession]:
        """Get active session for user"""
        return self.sessions.get(user_id)

    async def cleanup_old_sessions(self, max_age_minutes: int = 30):
        """Clean up sessions older than max_age"""
        async with self.lock:
            now = datetime.utcnow()
            to_remove = []

            for user_id, session in self.sessions.items():
                age = (now - session.started_at).total_seconds() / 60
                if age > max_age_minutes:
                    to_remove.append(user_id)

            for user_id in to_remove:
                await self.stop_session(user_id)
                logger.info(f"Cleaned up old session for user {user_id}")

# Global manager instance
stream_manager = BrowserStreamManager()
