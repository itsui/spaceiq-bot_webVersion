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

            # IMPORTANT: Use EXACT same settings as session_manager.py to avoid fingerprinting mismatch
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

            # Wait for any redirects to complete (SAML redirects can take time)
            # Try to detect navigation completion by waiting for stable URL
            logger.info("Waiting for SAML redirects to complete...")
            stable_url_count = 0
            last_url = self.page.url

            for i in range(15):  # Wait up to 15 seconds for redirects
                await asyncio.sleep(1)
                current_url = self.page.url

                # Check if we reached the destination
                if '/finder' in current_url:
                    logger.info(f"Authentication successful - landed on finder page (after {i+1}s)")
                    # Wait for page to fully load - use network idle instead of fixed sleep
                    logger.info("Waiting for network idle to ensure all cookies are set...")
                    try:
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                        logger.info("Network idle detected")
                    except:
                        logger.warning("Network idle timeout - continuing anyway")
                        await asyncio.sleep(5)  # Fallback to fixed wait

                    self.status = "success"
                    return await self._complete_authentication()

                # Check if we're on MFA selection page
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

                # Check if stuck on SAML auto-submit page
                if 'SAMLRequest' in current_url or 'SAMLResponse' in current_url:
                    logger.info("SAML redirect page detected - checking for auto-submit form")
                    # Look for auto-submit form
                    form = await self.page.query_selector('form')
                    if form:
                        logger.info("Found SAML form - submitting manually")
                        await form.evaluate('form => form.submit()')
                        await asyncio.sleep(2)
                        continue  # Check URL again after form submit

                # Check if hit PIV card error page (certificate authentication)
                if 'cert/error' in current_url and 'piv.card' in current_url:
                    logger.info("PIV card error detected - analyzing page for proper continue method")

                    # Take screenshot for debugging
                    try:
                        import tempfile
                        import os
                        screenshot_path = os.path.join(tempfile.gettempdir(), f'piv_error_user{self.user_id}.png')
                        await self.page.screenshot(path=screenshot_path)
                        logger.info(f"PIV error page screenshot saved to: {screenshot_path}")
                    except Exception as e:
                        logger.warning(f"Could not save screenshot: {e}")

                    # Log page content for debugging
                    page_content = await self.page.content()
                    logger.info(f"PIV error page HTML length: {len(page_content)} chars")
                    # Log first 1000 chars of HTML
                    logger.info(f"PIV error page HTML preview: {page_content[:1000]}")

                    # Look for any links or buttons that might continue the flow
                    all_links = await self.page.query_selector_all('a')
                    logger.info(f"Found {len(all_links)} links on PIV error page")

                    # Try to find skip/continue button with more variations
                    skip_selectors = [
                        'a[href*="skip"]',
                        'a[href*="continue"]',
                        'button:has-text("Skip")',
                        'button:has-text("Continue")',
                        'a:has-text("Skip")',
                        'a:has-text("Continue")',
                        'a:has-text("Continue without")',
                        '.button:has-text("Continue")',
                        '[role="button"]:has-text("Continue")'
                    ]

                    skip_button = None
                    for selector in skip_selectors:
                        try:
                            skip_button = await self.page.query_selector(selector)
                            if skip_button:
                                logger.info(f"Found skip element with selector: {selector}")
                                break
                        except:
                            continue

                    if skip_button:
                        logger.info("Clicking skip/continue button")
                        await skip_button.click()
                        await asyncio.sleep(3)
                        continue
                    else:
                        # Check if page will auto-redirect by waiting
                        logger.info("No skip button found - waiting 5s for auto-redirect")
                        await asyncio.sleep(5)

                        # If still on PIV error after waiting, log error and fail
                        if 'cert/error' in self.page.url:
                            logger.error("Still stuck on PIV error page - SSO flow cannot complete")
                            logger.error(f"Current URL: {self.page.url}")
                            # Log first few links to help debug
                            for i, link in enumerate(all_links[:5]):
                                try:
                                    href = await link.get_attribute('href')
                                    text = await link.text_content()
                                    logger.info(f"  Link {i+1}: text='{text}' href='{href}'")
                                except:
                                    pass
                            raise Exception("PIV card error - cannot find way to continue SSO flow")

                        continue

                # Check for stable URL (no more redirects)
                if current_url == last_url:
                    stable_url_count += 1
                    if stable_url_count >= 3:  # URL stable for 3 seconds
                        break
                else:
                    stable_url_count = 0
                    last_url = current_url
                    logger.info(f"Redirect detected: {current_url}")

            # After waiting, check final URL
            current_url = self.page.url
            if '/finder' in current_url:
                logger.info("Authentication successful - landed on finder page after redirects")
                # Wait for page to fully load - use network idle instead of fixed sleep
                logger.info("Waiting for network idle to ensure all cookies are set...")
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    logger.info("Network idle detected")
                except:
                    logger.warning("Network idle timeout - continuing anyway")
                    await asyncio.sleep(5)  # Fallback to fixed wait

                self.status = "success"
                return await self._complete_authentication()
            else:
                self.error = f"Unexpected page after redirects: {current_url}"
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
            # Wait for page to fully load - use network idle instead of fixed sleep
            logger.info("Waiting for network idle to ensure all cookies are set...")
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                logger.info("Network idle detected")
            except:
                logger.warning("Network idle timeout - continuing anyway")
                await asyncio.sleep(5)  # Fallback to fixed wait

            self.status = "success"
            return await self._complete_authentication()

        except Exception as e:
            self.error = f"MFA timeout or error: {str(e)}"
            logger.error(self.error)
            self.status = "error"
            await self.cleanup()
            return {'status': 'error', 'error': self.error}

    async def _complete_authentication(self) -> Dict:
        """Save session and validate it works before returning success"""
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

            # CRITICAL: Validate the session works in a new context before declaring success
            logger.info("Validating saved session works...")
            try:
                test_context = await self.browser.new_context(
                    storage_state=session_json,
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                test_page = await test_context.new_page()

                # Try to navigate to finder page with saved session
                await test_page.goto('https://main.spaceiq.com/finder/building/LC/floor/2',
                                    timeout=15000, wait_until='domcontentloaded')
                await asyncio.sleep(2)

                # Check if we got redirected to login (session invalid)
                if '/login' in test_page.url:
                    await test_context.close()
                    raise Exception("Saved session is invalid - redirected to login page immediately after saving!")

                logger.info("✓ Session validation successful - session works!")
                await test_context.close()

            except Exception as validation_error:
                logger.error(f"Session validation FAILED: {validation_error}")
                await self.cleanup()
                return {'status': 'error', 'error': f'Session validation failed: {str(validation_error)}'}

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
