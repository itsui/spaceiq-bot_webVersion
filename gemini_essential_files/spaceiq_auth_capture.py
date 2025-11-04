"""
SpaceIQ Authentication Session Capture
Handles user authentication and session cookie capture

For Windows: Uses headed browser that user can see and interact with
For Linux: Will use VNC streaming (future enhancement)
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import threading
from typing import Optional

from models import db, SpaceIQSession, VNCSession
from src.utils.auth_encryption import encrypt_data, decrypt_data
from config import Config

logger = logging.getLogger('spaceiq_auth')


class SpaceIQAuthCapture:
    """Captures SpaceIQ authentication session"""

    def __init__(self, user_id: int, app_context):
        self.user_id = user_id
        self.app_context = app_context
        self.browser = None
        self.context = None
        self.page = None
        self.status = 'initializing'
        self.error = None
        self.authenticated_as = None

    async def start_capture(self) -> bool:
        """
        Start authentication capture process

        For Windows: Opens a regular browser window
        For Linux with VNC: Would use virtual display
        """
        try:
            logger.info(f"Starting SpaceIQ auth capture for user {self.user_id}")
            self.status = 'waiting_for_login'

            # Target URL
            target_url = f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/LC/floor/2"

            # Launch browser
            async with async_playwright() as p:
                # On Windows, we launch a visible browser
                # User can see and interact with it
                self.browser = await p.chromium.launch(
                    headless=False,  # Show browser window
                    args=[
                        '--start-maximized',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )

                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                self.page = await self.context.new_page()

                # Navigate to SpaceIQ
                await self.page.goto(target_url, wait_until='domcontentloaded')

                logger.info(f"Browser opened for user {self.user_id}, waiting for login...")

                # Wait for user to complete SSO login
                # We detect success when URL changes to the target pattern
                try:
                    await self.page.wait_for_url(
                        lambda url: "/login" not in url.lower() and "/finder/building/" in url,
                        timeout=300000  # 5 minutes
                    )

                    self.status = 'capturing_session'
                    logger.info(f"Login detected for user {self.user_id}, capturing session...")

                    # Give it a moment to fully load
                    await asyncio.sleep(2)

                    # Try to extract username
                    try:
                        # Look for user info in page
                        # This depends on SpaceIQ's UI structure
                        user_elem = await self.page.query_selector('[data-test="user-name"], .user-name, #user-name')
                        if user_elem:
                            self.authenticated_as = await user_elem.text_content()
                            self.authenticated_as = self.authenticated_as.strip()
                    except Exception as e:
                        logger.warning(f"Could not extract username: {e}")
                        self.authenticated_as = "Unknown User"

                    # Capture session state
                    storage_state = await self.context.storage_state()

                    # Save to database (encrypted)
                    success = await self._save_session(storage_state)

                    if success:
                        self.status = 'completed'
                        logger.info(f"Session captured successfully for user {self.user_id}")
                        return True
                    else:
                        self.status = 'error'
                        self.error = "Failed to save session"
                        return False

                except asyncio.TimeoutError:
                    self.status = 'timeout'
                    self.error = "Login timeout - user did not complete authentication within 5 minutes"
                    logger.warning(f"Login timeout for user {self.user_id}")
                    return False

                except Exception as e:
                    self.status = 'error'
                    self.error = str(e)
                    logger.error(f"Error during login wait for user {self.user_id}: {e}")
                    return False

                finally:
                    # Close browser
                    if self.browser:
                        await self.browser.close()

        except Exception as e:
            self.status = 'error'
            self.error = str(e)
            logger.error(f"Error in auth capture for user {self.user_id}: {e}", exc_info=True)
            return False

    async def _save_session(self, storage_state: dict) -> bool:
        """Save captured session to database (encrypted)"""
        try:
            with self.app_context:
                # Encrypt session data
                session_json = json.dumps(storage_state)
                encrypted_data = encrypt_data(session_json)

                # Get or create session record
                session = SpaceIQSession.query.filter_by(user_id=self.user_id).first()
                if not session:
                    session = SpaceIQSession(user_id=self.user_id)
                    db.session.add(session)

                # Update session
                session.session_data = encrypted_data
                session.authenticated_as = self.authenticated_as or "Unknown"
                session.created_at = datetime.utcnow()
                session.expires_at = datetime.utcnow() + timedelta(days=7)  # Sessions expire after 7 days
                session.is_valid = True

                db.session.commit()

                logger.info(f"Session saved for user {self.user_id} (authenticated as {self.authenticated_as})")
                return True

        except Exception as e:
            logger.error(f"Error saving session for user {self.user_id}: {e}", exc_info=True)
            return False


class AuthCaptureManager:
    """Manages authentication capture sessions for multiple users"""

    def __init__(self, app):
        self.app = app
        self.active_captures = {}  # {user_id: AuthCaptureThread}
        self.lock = threading.Lock()

    def start_capture(self, user_id: int) -> tuple[bool, str]:
        """Start authentication capture for a user"""
        with self.lock:
            # Check if already running
            if user_id in self.active_captures:
                thread = self.active_captures[user_id]
                if thread.is_alive():
                    return False, "Authentication already in progress"
                else:
                    # Clean up dead thread
                    del self.active_captures[user_id]

            # Start new capture thread
            thread = AuthCaptureThread(user_id, self.app.app_context())
            thread.start()

            self.active_captures[user_id] = thread

            return True, "Authentication started - browser will open for you to log in"

    def get_capture_status(self, user_id: int) -> Optional[dict]:
        """Get status of authentication capture"""
        with self.lock:
            if user_id in self.active_captures:
                thread = self.active_captures[user_id]
                is_completed = thread.capture.status == 'completed' if thread.capture else False
                return {
                    'status': thread.capture.status if thread.capture else 'initializing',
                    'error': thread.capture.error if thread.capture else None,
                    'authenticated_as': thread.capture.authenticated_as if thread.capture else None,
                    'is_authenticated': is_completed,
                    'completed': is_completed
                }

            # Check database for existing session
            with self.app.app_context():
                session = SpaceIQSession.query.filter_by(user_id=user_id).first()
                if session and session.is_valid and session.session_data:
                    return {
                        'status': 'completed',
                        'error': None,
                        'authenticated_as': session.authenticated_as,
                        'is_authenticated': True,
                        'completed': True
                    }

            return {
                'status': 'not_started',
                'error': None,
                'authenticated_as': None,
                'is_authenticated': False,
                'completed': False
            }

    def cleanup_completed(self):
        """Remove completed capture threads"""
        with self.lock:
            completed = []
            for user_id, thread in self.active_captures.items():
                if not thread.is_alive():
                    completed.append(user_id)

            for user_id in completed:
                del self.active_captures[user_id]


class AuthCaptureThread(threading.Thread):
    """Thread for running authentication capture"""

    def __init__(self, user_id: int, app_context):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.app_context = app_context
        self.capture = None

    def run(self):
        """Run the capture process"""
        try:
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create capture instance
            self.capture = SpaceIQAuthCapture(self.user_id, self.app_context)

            # Run capture
            loop.run_until_complete(self.capture.start_capture())

        except Exception as e:
            logger.error(f"Auth capture thread error for user {self.user_id}: {e}", exc_info=True)
        finally:
            loop.close()
