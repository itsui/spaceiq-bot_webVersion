"""
CDP-Based Browser Stream Manager
Uses Chrome DevTools Protocol for much faster interaction than screenshot polling
"""

import asyncio
import base64
import logging
import threading
from queue import Queue
from typing import Optional, Dict
from playwright.async_api import async_playwright

logger = logging.getLogger('cdp_browser')


class CDPBrowserSession:
    """Browser session using CDP for faster streaming"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.cdp_session = None

        # State
        self.current_url = "about:blank"
        self.authenticated = False
        self.last_screenshot = None

        # Threading
        self.thread = None
        self.loop = None
        self.running = False
        self.command_queue = Queue()
        self.result_queue = Queue()

        # CDP WebSocket URL
        self.cdp_ws_url = None

    def start_thread(self, target_url: str):
        """Start browser in dedicated thread"""
        self.running = True
        self.thread = threading.Thread(
            target=self._run_async_loop,
            args=(target_url,),
            daemon=True
        )
        self.thread.start()

    def _run_async_loop(self, target_url: str):
        """Run persistent event loop in this thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._start_browser(target_url))

            # Keep loop running and process commands
            while self.running:
                self.loop.run_until_complete(self._process_commands())
        except Exception as e:
            logger.error(f"Browser loop error: {e}")
        finally:
            try:
                self.loop.run_until_complete(self._cleanup())
            except:
                pass

    async def _start_browser(self, target_url: str):
        """Start browser with CDP enabled"""
        try:
            logger.info(f"Starting CDP browser for user {self.user_id}")

            self.playwright = await async_playwright().start()

            # Launch with CDP endpoint
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                ]
            )

            # Smaller viewport for faster rendering
            self.context = await self.browser.new_context(
                viewport={'width': 800, 'height': 600},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            self.page = await self.context.new_page()

            # Create CDP session for faster operations
            self.cdp_session = await self.context.new_cdp_session(self.page)

            # Enable page events
            await self.cdp_session.send('Page.enable')

            # Set up navigation callback
            self.page.on('framenavigated', self._on_navigation)

            # Navigate to target
            await self.page.goto(target_url, wait_until='networkidle', timeout=30000)

            logger.info(f"✓ CDP browser started for user {self.user_id}")

        except Exception as e:
            logger.error(f"Failed to start CDP browser: {e}")
            self.running = False

    async def _process_commands(self):
        """Process commands from Flask threads"""
        try:
            if not self.command_queue.empty():
                cmd = self.command_queue.get_nowait()
                cmd_type = cmd.get('type')

                if cmd_type == 'screenshot':
                    screenshot = await self._get_screenshot_cdp()
                    self.result_queue.put({'success': True, 'data': screenshot})

                elif cmd_type == 'click':
                    await self._click_cdp(cmd['x'], cmd['y'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'type':
                    await self._type_async(cmd['text'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'press':
                    await self._press_async(cmd['key'])
                    self.result_queue.put({'success': True})

                elif cmd_type == 'save_session':
                    success = await self._save_session_async(cmd['path'])
                    self.result_queue.put({'success': success})

            else:
                await asyncio.sleep(0.01)  # Small sleep to prevent busy loop

        except Exception as e:
            logger.error(f"Command processing error: {e}")
            self.result_queue.put({'success': False, 'error': str(e)})

    async def _get_screenshot_cdp(self) -> Optional[str]:
        """Get screenshot using CDP (much faster than Playwright's screenshot)"""
        try:
            # Use CDP for faster screenshot capture
            result = await self.cdp_session.send('Page.captureScreenshot', {
                'format': 'jpeg',
                'quality': 50,  # Balance between quality and speed
                'fromSurface': True  # Capture from compositor surface (faster)
            })

            self.last_screenshot = result['data']
            return self.last_screenshot

        except Exception as e:
            logger.error(f"CDP screenshot error: {e}")
            return self.last_screenshot

    async def _click_cdp(self, x: int, y: int):
        """Click using CDP (faster than Playwright)"""
        try:
            # Send mousePressed event
            await self.cdp_session.send('Input.dispatchMouseEvent', {
                'type': 'mousePressed',
                'x': x,
                'y': y,
                'button': 'left',
                'clickCount': 1
            })

            # Small delay
            await asyncio.sleep(0.05)

            # Send mouseReleased event
            await self.cdp_session.send('Input.dispatchMouseEvent', {
                'type': 'mouseReleased',
                'x': x,
                'y': y,
                'button': 'left',
                'clickCount': 1
            })

        except Exception as e:
            logger.error(f"CDP click error: {e}")

    async def _type_async(self, text: str):
        """Type text"""
        if self.page:
            await self.page.keyboard.type(text, delay=15)  # 15ms delay - much faster typing

    async def _press_async(self, key: str):
        """Press key"""
        if self.page:
            await self.page.keyboard.press(key)

    async def _save_session_async(self, path: str) -> bool:
        """Save session"""
        try:
            if not self.context or not self.authenticated:
                return False
            await self.context.storage_state(path=path)
            return True
        except:
            return False

    def _on_navigation(self, frame):
        """Handle navigation"""
        try:
            if frame == self.page.main_frame:
                self.current_url = self.page.url
                logger.info(f"Navigation to: {self.current_url}")

                # Check if authenticated
                if '/finder' in self.current_url and 'spaceiq.com' in self.current_url:
                    if not self.authenticated:
                        # Schedule the async sleep in the event loop
                        asyncio.create_task(self._mark_authenticated())

        except Exception as e:
            logger.error(f"Navigation callback error: {e}")

    async def _mark_authenticated(self):
        """Mark as authenticated after delay"""
        logger.info(f"✓ Authentication detected for user {self.user_id}")
        logger.info(f"  Waiting 3 seconds for cookies...")
        await asyncio.sleep(3)
        self.authenticated = True
        logger.info(f"✓✓✓ Authentication SUCCESSFUL for user {self.user_id}")

    # Public methods (sync wrappers for Flask)

    def get_screenshot(self) -> Optional[str]:
        """Get screenshot (sync wrapper)"""
        self.command_queue.put({'type': 'screenshot'})
        try:
            result = self.result_queue.get(timeout=0.5)  # Faster timeout
            return result.get('data') if result.get('success') else self.last_screenshot
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

    async def _cleanup(self):
        """Cleanup resources"""
        try:
            if self.cdp_session:
                await self.cdp_session.detach()
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def stop(self):
        """Stop browser session"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


class CDPBrowserStreamManager:
    """Manages multiple CDP browser sessions"""

    def __init__(self):
        self.sessions: Dict[int, CDPBrowserSession] = {}

    def start_session(self, user_id: int, target_url: str) -> bool:
        """Start browser session for user"""
        try:
            # Stop existing session if any
            self.stop_session(user_id)

            # Create new session
            session = CDPBrowserSession(user_id)
            session.start_thread(target_url)

            self.sessions[user_id] = session

            logger.info(f"Started CDP session for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start CDP session: {e}")
            return False

    def get_session(self, user_id: int) -> Optional[CDPBrowserSession]:
        """Get session for user"""
        return self.sessions.get(user_id)

    def stop_session(self, user_id: int):
        """Stop session for user"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            session.stop()
            del self.sessions[user_id]
            logger.info(f"Stopped CDP session for user {user_id}")


# Global manager instance
cdp_stream_manager = CDPBrowserStreamManager()
