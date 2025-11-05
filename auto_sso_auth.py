"""
Automated SSO Authentication
Handles SpaceIQ SSO login flow automatically without browser streaming.
"""

import asyncio
import logging
from typing import Optional, Dict, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class AutoSSOMFAHandler:
    """Handles automated SSO authentication with smart MFA detection"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.status = "initializing"
        self.mfa_number: Optional[str] = None
        self.error: Optional[str] = None

    async def start_authentication(self, email: str, password: str) -> Dict:
        """
        Start automated SSO authentication.

        Returns dict with:
        - status: "mfa_required", "success", or "error"
        - mfa_number: The number to tap in Okta Verify (if MFA required)
        - error: Error message if failed
        """
        try:
            logger.info(f"Starting automated SSO authentication for user {self.user_id}")
            self.status = "starting"

            # Launch browser
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
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            self.page = await self.context.new_page()

            # Step 1: Navigate to SpaceIQ login
            logger.info("Step 1: Navigating to SpaceIQ login")
            self.status = "navigating_to_login"
            await self.page.goto('https://main.spaceiq.com/login?redirectTo=/finder/building/LC/floor/2',
                                 wait_until='domcontentloaded', timeout=30000)

            # Step 2: Click "Login with SSO"
            logger.info("Step 2: Clicking Login with SSO")
            self.status = "clicking_sso"
            await self.page.wait_for_selector('#submit_sso', timeout=10000)
            await self.page.click('#submit_sso')
            await asyncio.sleep(1)

            # Step 3: Enter email and continue
            logger.info("Step 3: Entering email")
            self.status = "entering_email"
            await self.page.wait_for_selector('#email', timeout=10000)
            await self.page.fill('#email', email)
            await self.page.click('#submit')
            await asyncio.sleep(2)

            # Step 4: Enter password and verify
            logger.info("Step 4: Entering password")
            self.status = "entering_password"
            await self.page.wait_for_selector('input[name="identifier"]', timeout=10000)
            await self.page.fill('input[name="identifier"]', email)
            await self.page.click('input[type="submit"][value="Next"]')
            await asyncio.sleep(2)

            # Wait for password field
            await self.page.wait_for_selector('input[name="credentials.passcode"]', timeout=10000)
            await self.page.fill('input[name="credentials.passcode"]', password)
            await self.page.click('input[type="submit"][value="Verify"]')
            await asyncio.sleep(3)

            # Step 5: Check what page we landed on
            logger.info("Step 5: Checking authentication result")
            current_url = self.page.url

            # Case A: MFA required - look for Okta Verify push option
            if 'okta.com' in current_url and 'select-authenticator' in current_url:
                logger.info("MFA selection page detected")
                self.status = "mfa_selection"

                # Click "Get a push notification" for Okta Verify
                await self.page.click('[data-se="okta_verify-push"] a')
                await asyncio.sleep(2)

                # Extract MFA number
                number_elem = await self.page.query_selector('.phone--number[data-se="challenge-number"]')
                if number_elem:
                    self.mfa_number = await number_elem.text_content()
                    logger.info(f"MFA number extracted: {self.mfa_number}")
                    self.status = "waiting_for_mfa"
                    return {
                        'status': 'mfa_required',
                        'mfa_number': self.mfa_number,
                        'message': f'Tap {self.mfa_number} in your Okta Verify app'
                    }
                else:
                    self.error = "Could not extract MFA number"
                    logger.error(self.error)
                    return {'status': 'error', 'error': self.error}

            # Case B: MFA skipped or already completed - check if on finder page
            elif '/finder' in current_url:
                logger.info("Authentication successful - landed on finder page")
                self.status = "success"
                return await self._complete_authentication()

            # Wait a bit more to see if we get redirected
            else:
                logger.info(f"Waiting for redirect... Current URL: {current_url}")
                await asyncio.sleep(5)
                current_url = self.page.url

                if '/finder' in current_url:
                    logger.info("Authentication successful after wait")
                    self.status = "success"
                    return await self._complete_authentication()
                else:
                    self.error = f"Unexpected page: {current_url}"
                    logger.error(self.error)
                    return {'status': 'error', 'error': self.error}

        except Exception as e:
            self.error = str(e)
            logger.error(f"Authentication failed: {e}", exc_info=True)
            self.status = "error"
            await self.cleanup()
            return {'status': 'error', 'error': str(e)}

    async def wait_for_mfa_completion(self, timeout: int = 120) -> Dict:
        """
        Wait for user to complete MFA on their phone.
        Returns status dict when complete.
        """
        try:
            logger.info(f"Waiting for MFA completion (timeout: {timeout}s)")
            self.status = "waiting_for_mfa_approval"

            # Wait for navigation to finder page
            await self.page.wait_for_url('**/finder/**', timeout=timeout * 1000)

            logger.info("MFA completed successfully")
            self.status = "success"
            return await self._complete_authentication()

        except Exception as e:
            self.error = f"MFA timeout or error: {str(e)}"
            logger.error(self.error)
            self.status = "error"
            await self.cleanup()
            return {'status': 'error', 'error': self.error}

    async def _complete_authentication(self) -> Dict:
        """Save session and return success"""
        try:
            # Save session to temp file
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json')

            # Save storage state
            await self.context.storage_state(path=temp_path)
            await asyncio.sleep(0.5)  # Wait for file write

            # Read session data
            import os
            with os.fdopen(temp_fd, 'r') as f:
                session_data = f.read()

            # Validate it's not empty
            if not session_data or len(session_data.strip()) == 0:
                raise Exception("Session data is empty")

            session_json = json.loads(session_data)

            # Clean up temp file
            os.unlink(temp_path)

            # Cleanup browser
            await self.cleanup()

            logger.info(f"Authentication completed successfully for user {self.user_id}")
            return {
                'status': 'success',
                'session_data': session_json,
                'message': 'Authentication successful'
            }

        except Exception as e:
            logger.error(f"Failed to complete authentication: {e}", exc_info=True)
            await self.cleanup()
            return {'status': 'error', 'error': str(e)}

    async def cleanup(self):
        """Clean up browser resources"""
        try:
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

    def get_status(self) -> Dict:
        """Get current authentication status"""
        return {
            'status': self.status,
            'mfa_number': self.mfa_number,
            'error': self.error
        }
