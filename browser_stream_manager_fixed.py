"""
Browser Stream Manager - Fixed with dedicated async thread
"""

import asyncio
import base64
import json
import threading
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
import logging
from queue import Queue

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger('browser_stream')

class BrowserStreamSession:
    """Represents an active browser streaming session running in dedicated thread"""

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

        # Thread and event loop management
        self.thread = None
        self.loop = None
        self.running = False
        self.command_queue = Queue()
        self.result_queue = Queue()

    def start_thread(self, target_url: str):
        """Start the browser in a dedicated thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run_async_loop, args=(target_url,), daemon=True)
        self.thread.start()

        # Wait for browser to start (with timeout)
        try:
            result = self.result_queue.get(timeout=30)
            return result.get('success', False)
        except:
            return False

    def _run_async_loop(self, target_url: str):
        """Run async event loop in this thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._start_browser(target_url))
            # Signal success
            self.result_queue.put({'success': True})

            # Keep loop running to handle commands
            while self.running:
                self.loop.run_until_complete(self._process_commands())

        except Exception as e:
            logger.error(f"Browser thread error: {e}", exc_info=True)
            self.result_queue.put({'success': False, 'error': str(e)})
        finally:
            self.loop.close()

    async def _start_browser(self, target_url: str):
        """Start browser (runs in dedicated thread's event loop)"""
        try:
            logger.info(f"Starting browser for user {self.user_id}")

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                ]
            )

            self.context = await self.browser.new_context(
                viewport={'width': 640, 'height': 400},  # Low res for maximum speed
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            self.page = await self.context.new_page()

            # Set up navigation callback
            async def on_nav(frame):
                await self._on_navigation(frame)

            self.page.on('framenavigated', lambda frame: asyncio.create_task(on_nav(frame)))

            await self.page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
            self.current_url = self.page.url

            logger.info(f"✓ Browser started for user {self.user_id}")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}", exc_info=True)
            raise

    async def _process_commands(self):
        """Process commands from the queue"""
        await asyncio.sleep(0.001)  # 1ms delay for maximum responsiveness

        while not self.command_queue.empty():
            try:
                command = self.command_queue.get_nowait()
                cmd_type = command['type']

                if cmd_type == 'screenshot':
                    result = await self._get_screenshot_async()
                    self.result_queue.put({'success': True, 'data': result})

                elif cmd_type == 'click':
                    await self._click_async(command['x'], command['y'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'type':
                    await self._type_async(command['text'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'press':
                    await self._press_async(command['key'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'save_session':
                    result = await self._save_session_async(command['path'])
                    self.result_queue.put({'success': result})

            except Exception as e:
                logger.error(f"Command processing error: {e}")
                self.result_queue.put({'success': False, 'error': str(e)})

    async def _get_screenshot_async(self) -> Optional[str]:
        """Get screenshot (async, runs in browser thread)"""
        try:
            if not self.page:
                return None

            # Ultra low quality for maximum speed - 10 is minimum
            screenshot_bytes = await self.page.screenshot(type='jpeg', quality=10)
            self.last_screenshot = base64.b64encode(screenshot_bytes).decode('utf-8')
            return self.last_screenshot
        except:
            return self.last_screenshot

    async def _click_async(self, x: int, y: int):
        """Click (async)"""
        if self.page:
            await self.page.mouse.click(x, y)

    async def _type_async(self, text: str):
        """Type (async) - optimized for speed"""
        if self.page:
            # For longer text (batched input), use insertText which is much faster
            # For single chars (special keys), use keyboard.type
            if len(text) > 3:
                # Get focused element and insert text directly
                await self.page.keyboard.insert_text(text)
            else:
                await self.page.keyboard.type(text, delay=0)  # No delay between keystrokes
            # No delay - maximum speed, screenshots will catch up

    async def _press_async(self, key: str):
        """Press key (async)"""
        if self.page:
            await self.page.keyboard.press(key)

    async def _save_session_async(self, path: str) -> bool:
        """Save session (async)"""
        try:
            if not self.context:
                logger.error("Cannot save session: browser context is None")
                return False

            if not self.authenticated:
                logger.warning("Attempting to save session before authentication detected")
                # Allow saving even if not authenticated (user might have logged in but URL didn't match)

            # Save storage state
            await self.context.storage_state(path=path)

            # CRITICAL: Wait for file to be fully written to disk
            # On Windows especially, file writes may be buffered
            await asyncio.sleep(0.5)  # Increased from 0.1s to 0.5s

            # Validate that file was written and has content
            from pathlib import Path
            import os
            session_path = Path(path)
            if not session_path.exists():
                logger.error(f"Session file was not created at {path}")
                return False

            file_size = os.path.getsize(path)
            if file_size == 0:
                logger.error(f"Session file is empty (0 bytes) at {path}")
                return False

            if file_size < 10:  # Minimum valid JSON would be at least 10 bytes like {"cookies":[]}
                logger.error(f"Session file is too small ({file_size} bytes), likely invalid")
                return False

            logger.info(f"✓ Session saved successfully ({file_size} bytes) for user {self.user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session for user {self.user_id}: {e}", exc_info=True)
            return False

    async def _on_navigation(self, frame):
        """Handle navigation"""
        try:
            if frame == self.page.main_frame:
                self.current_url = self.page.url
                logger.info(f"Navigation to: {self.current_url}")

                # Check if authenticated (redirected to finder page after login)
                if '/finder' in self.current_url and 'spaceiq.com' in self.current_url:
                    if not self.authenticated:
                        self.authenticated = True
                        logger.info(f"✓✓✓ Authentication SUCCESSFUL for user {self.user_id} at {self.current_url}")
        except Exception as e:
            logger.error(f"Navigation callback error: {e}")

    # Public methods (called from Flask threads)

    def get_screenshot(self) -> Optional[str]:
        """Get screenshot (sync wrapper)"""
        self.command_queue.put({'type': 'screenshot'})
        try:
            result = self.result_queue.get(timeout=1)  # Faster timeout for real-time feel
            data = result.get('data') if result.get('success') else None
            # Always return cached screenshot if new one is None (page loading, etc.)
            return data if data is not None else self.last_screenshot
        except:
            return self.last_screenshot

    def click(self, x: int, y: int):
        """Click (sync wrapper)"""
        self.command_queue.put({'type': 'click', 'x': x, 'y': y})

    def type_text(self, text: str):
        """Type (sync wrapper)"""
        self.command_queue.put({'type': 'type', 'text': text})

    def press_key(self, key: str):
        """Press key (sync wrapper)"""
        self.command_queue.put({'type': 'press', 'key': key})

    def save_session(self, path: str) -> bool:
        """Save session (sync wrapper)"""
        self.command_queue.put({'type': 'save_session', 'path': path})
        try:
            result = self.result_queue.get(timeout=5)
            return result.get('success', False)
        except:
            return False

    def stop(self):
        """Stop the browser"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

class BrowserStreamManager:
    """Manages multiple browser streaming sessions"""

    def __init__(self):
        self.sessions: Dict[int, BrowserStreamSession] = {}

    def start_session(self, user_id: int, target_url: str = "https://main.spaceiq.com/login") -> bool:
        """Start a new streaming session"""
        # Stop existing session
        if user_id in self.sessions:
            self.stop_session(user_id)

        # Create and start new session
        session = BrowserStreamSession(user_id)
        success = session.start_thread(target_url)

        if success:
            self.sessions[user_id] = session
        return success

    def stop_session(self, user_id: int):
        """Stop a session"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            session.stop()
            del self.sessions[user_id]

    def get_session(self, user_id: int) -> Optional[BrowserStreamSession]:
        """Get active session"""
        return self.sessions.get(user_id)

# Global manager
stream_manager = BrowserStreamManager()
