"""
Persistent Browser Manager
Manages per-user persistent browser profiles for reliable cookie persistence

Each user gets their own persistent Chromium profile directory.
Auth and bot execution happen in the SAME profile → cookies persist!
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import json

logger = logging.getLogger(__name__)


class PersistentBrowserManager:
    """Manages persistent browser profiles for users"""

    def __init__(self, user_id: int, base_dir: Path = None):
        """
        Initialize persistent browser manager for a specific user

        Args:
            user_id: User ID for profile isolation
            base_dir: Base directory for profiles (default: playwright/.auth/profiles)
        """
        self.user_id = user_id

        # Setup profile directory
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "playwright" / ".auth" / "profiles"

        self.profile_dir = base_dir / f"user_{user_id}"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        logger.info(f"Persistent browser manager initialized for user {user_id}")
        logger.info(f"Profile directory: {self.profile_dir}")

    async def launch_browser(self, headless: bool = False, visible_for_auth: bool = False) -> BrowserContext:
        """
        Launch browser with persistent profile

        Args:
            headless: Run in headless mode (default: False for auth, True for bot)
            visible_for_auth: Force visible mode for authentication (even if headless=True)

        Returns:
            BrowserContext ready for use
        """
        try:
            self.playwright = await async_playwright().start()

            # Log launch mode
            if visible_for_auth:
                headless = False
                logger.info(f"Launching VISIBLE browser for authentication (user {self.user_id})")
            else:
                mode = "HEADLESS" if headless else "VISIBLE"
                logger.info(f"Launching {mode} browser for user {self.user_id}")

            # Launch with persistent profile
            logger.info(f"DEBUG: Using profile directory: {self.profile_dir}")
            logger.info(f"DEBUG: Headless mode: {headless}")
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ],
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                accept_downloads=False,
                ignore_https_errors=False
            )

            # launch_persistent_context returns a context directly
            self.context = self.browser

            # Create or reuse page
            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()

            # Debug: Check what cookies are in the profile
            try:
                cookies = await self.context.cookies()
                logger.info(f"✓ Browser launched successfully for user {self.user_id}")
                logger.info(f"DEBUG: Profile has {len(cookies)} cookies on launch")
                for cookie in cookies[:5]:  # Log first 5 cookies
                    logger.info(f"DEBUG: Cookie: {cookie.get('name')} for domain {cookie.get('domain')}")
            except Exception as e:
                logger.warning(f"Failed to check cookies: {e}")
                logger.info(f"✓ Browser launched successfully for user {self.user_id}")

            return self.context

        except Exception as e:
            logger.error(f"Failed to launch browser for user {self.user_id}: {e}", exc_info=True)
            raise

    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                # Give cookies time to be written to profile before closing
                import asyncio
                await asyncio.sleep(2)
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            # Wait a bit more to ensure profile is fully saved
            import asyncio
            await asyncio.sleep(1)
            logger.info(f"Browser closed for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error closing browser for user {self.user_id}: {e}")

    async def get_cookies(self) -> list:
        """Get all cookies from current context"""
        if not self.context:
            return []

        try:
            cookies = await self.context.cookies()
            logger.info(f"Retrieved {len(cookies)} cookies for user {self.user_id}")
            return cookies
        except Exception as e:
            logger.error(f"Error getting cookies for user {self.user_id}: {e}")
            return []

    async def get_storage_state(self) -> dict:
        """Get storage state (cookies + localStorage) from context"""
        if not self.context:
            return {}

        try:
            storage_state = await self.context.storage_state()
            logger.info(f"Retrieved storage state for user {self.user_id}")
            return storage_state
        except Exception as e:
            logger.error(f"Error getting storage state for user {self.user_id}: {e}")
            return {}

    def clear_profile(self):
        """Clear user's browser profile (logout)"""
        try:
            import shutil
            if self.profile_dir.exists():
                shutil.rmtree(self.profile_dir)
                self.profile_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Profile cleared for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error clearing profile for user {self.user_id}: {e}")


class AutoAuthWithPersistentProfile:
    """Automated authentication that captures storage_state"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.status = "initializing"
        # Browser instances (created in authenticate())
        self.playwright = None
        self.browser = None
        self.context = None
        self.error = None
        self.mfa_number = None
        self.session_data = None
        self._mfa_wait_thread = None
        self._event_loop = None  # Will be set by app.py to reuse existing loop

    def get_status(self) -> dict:
        """Get current authentication status"""
        result = {
            'status': self.status,
            'mfa_number': self.mfa_number,
            'error': self.error
        }
        # If MFA completed successfully, include session data
        if self.status == 'success' and self.session_data:
            result['session_data'] = self.session_data
        return result

    def start_mfa_wait_background(self):
        """Start waiting for MFA in a background thread"""
        import threading

        def mfa_wait_worker():
            """Worker function to wait for MFA in background"""
            import asyncio

            # Use existing event loop if available, otherwise create new one
            if self._event_loop:
                loop = self._event_loop
                asyncio.set_event_loop(loop)
                logger.info(f"Reusing existing event loop for MFA wait (user {self.user_id})")
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info(f"Created new event loop for MFA wait (user {self.user_id})")

            try:
                result = loop.run_until_complete(self.wait_for_mfa(timeout=120))
                if result['status'] == 'success':
                    self.status = 'success'
                    self.session_data = result.get('session_data')
                    logger.info(f"✓ MFA completed successfully in background for user {self.user_id}")
                else:
                    self.status = 'error'
                    self.error = result.get('error', 'MFA wait failed')
                    logger.error(f"MFA wait failed for user {self.user_id}: {self.error}")
            except Exception as e:
                self.status = 'error'
                self.error = str(e)
                logger.error(f"MFA wait exception for user {self.user_id}: {e}", exc_info=True)
            finally:
                # Only close loop if we created a new one
                if not self._event_loop:
                    loop.close()
                else:
                    # Close the existing loop since MFA is done
                    try:
                        loop.close()
                    except:
                        pass

        self._mfa_wait_thread = threading.Thread(target=mfa_wait_worker, daemon=True)
        self._mfa_wait_thread.start()
        logger.info(f"Started MFA wait background thread for user {self.user_id}")

    async def authenticate(self, email: str, password: str, debug_mode: bool = False) -> dict:
        """
        Authenticate user with credentials

        Args:
            email: User's email
            password: User's password
            debug_mode: If True, run in visible browser mode for debugging

        Returns:
            dict with status, message, and optional mfa_number
        """
        try:
            if debug_mode:
                logger.info(f"Starting automated authentication for user {self.user_id} in DEBUG MODE (visible browser)")
            else:
                logger.info(f"Starting automated authentication for user {self.user_id}")
            self.status = "starting"

            # Launch regular browser (headless unless debug mode)
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=not debug_mode,  # Visible if debug_mode is True
                args=[
                    '--disable-blink-features=AutomationControlled',
                ]
            )

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = await self.context.new_page()

            # Step 1: Navigate to SpaceIQ login
            logger.info("Step 1: Navigating to SpaceIQ login")
            await page.goto('https://main.spaceiq.com/login?redirectTo=/finder/building/LC/floor/2',
                          wait_until='domcontentloaded', timeout=30000)

            # Step 2: Click "Login with SSO" button
            logger.info("Step 2: Clicking 'Login with SSO' button")
            await page.wait_for_selector('#submit_sso', timeout=10000)

            # Log the button element to verify we're clicking the right thing
            button_html = await page.evaluate('document.querySelector("#submit_sso").outerHTML')
            logger.info(f"SSO button HTML: {button_html}")

            await page.click('#submit_sso')

            # Wait for navigation to complete after clicking SSO
            logger.info("Waiting for redirect after SSO button click...")
            await asyncio.sleep(3)  # Give more time for redirect
            logger.info(f"URL after SSO click: {page.url}")

            # Step 3: Enter email
            logger.info("Step 3: Entering email")
            await page.wait_for_selector('#email', timeout=10000)
            await page.fill('#email', email)
            await page.click('#submit')
            await asyncio.sleep(3)

            # Check if already logged in (persistent profile might have saved session)
            current_url = page.url
            logger.info(f"URL after email submit: {current_url}")

            if '/finder' in current_url:
                logger.info("✓ Already logged in via persistent profile - skipping password entry")
                self.status = "success"
                await asyncio.sleep(3)

                storage_state = await self.context.storage_state()
                cookies = storage_state.get('cookies', [])
                logger.info(f"✓ Using {len(cookies)} existing cookies from persistent profile")

                await self._close_browser()

                return {
                    'status': 'success',
                    'session_data': storage_state,
                    'message': 'Already authenticated via persistent profile',
                    'cookies_count': len(cookies)
                }

            # Step 4: Enter password (only if not already logged in)
            logger.info("Step 4: Entering password")
            await page.wait_for_selector('input[name="identifier"]', timeout=10000)
            await page.fill('input[name="identifier"]', email)
            await page.click('input[type="submit"][value="Next"]')
            await asyncio.sleep(2)

            await page.wait_for_selector('input[name="credentials.passcode"]', timeout=10000)
            await page.fill('input[name="credentials.passcode"]', password)
            await page.click('input[type="submit"][value="Verify"]')
            await asyncio.sleep(3)

            # Check for password error BEFORE proceeding to MFA
            password_error = await page.query_selector('.o-form-error-container.o-form-has-errors')
            if password_error:
                error_text_elem = await page.query_selector('.okta-form-infobox-error p')
                error_text = await error_text_elem.text_content() if error_text_elem else "Unable to sign in"
                logger.error(f"Password authentication failed: {error_text}")

                self.error = f"Wrong password: {error_text}"
                await self._close_browser()

                return {
                    'status': 'error',
                    'error': 'wrong_password',
                    'message': 'Incorrect password. Please try again.',
                    'retry': True  # Signal that user can retry
                }

            # Step 5: Wait for MFA page to load (check by element presence, not URL!)
            logger.info("Step 5: Waiting for MFA page to load...")

            mfa_selection_page = False
            mfa_push_page = False

            try:
                # Wait for MFA authenticator buttons to appear (selection page)
                await page.wait_for_selector('a.button.select-factor', timeout=5000)
                logger.info("✓ MFA selection page loaded - authenticator buttons found")
                mfa_selection_page = True
            except:
                logger.info("No MFA selection buttons found - checking for direct push page...")
                # Check if we're on a direct push page (alternative layout)
                try:
                    await page.wait_for_selector('.phone--number[data-se="challenge-number"]', timeout=5000)
                    logger.info("✓ Direct MFA push page detected - number already displayed")
                    mfa_push_page = True
                except:
                    logger.warning("Timeout waiting for MFA page - checking what page we're on...")

            # Check what's on the page
            current_url = page.url
            logger.info(f"Current URL: {current_url}")

            # Check if we reached finder (authentication complete without MFA)
            if '/finder' in current_url:
                logger.info("✓ Authentication successful (no MFA required)")
                self.status = "success"
                await asyncio.sleep(5)

                storage_state = await self.context.storage_state()
                cookies = storage_state.get('cookies', [])
                logger.info(f"✓ Captured {len(cookies)} cookies in persistent profile")

                await self._close_browser()

                return {
                    'status': 'success',
                    'session_data': storage_state,
                    'message': 'Authentication successful',
                    'cookies_count': len(cookies)
                }

            # Layout 1: MFA selection page - click the push notification button
            if mfa_selection_page and await page.query_selector('a.button.select-factor'):
                    logger.info("MFA selection page detected")

                    # Wait for MFA options to load completely
                    await asyncio.sleep(3)

                    # Try to click the Select button for push notification
                    try:
                        # First, let's log ALL authenticator options on the page
                        logger.info("Scanning all MFA options on the page...")
                        authenticator_list = await page.query_selector('.authenticator-list')
                        if authenticator_list:
                            # Get all authenticator rows
                            rows = await page.query_selector_all('.authenticator-row')
                            logger.info(f"Found {len(rows)} authenticator option(s)")

                            for idx, row in enumerate(rows):
                                try:
                                    # Get the authenticator name/description
                                    name_elem = await row.query_selector('.authenticator-description')
                                    name = await name_elem.text_content() if name_elem else "Unknown"
                                    logger.info(f"  Option {idx+1}: {name.strip()}")
                                except:
                                    pass

                        # Strategy 1: Try to find button by checking parent row text for "push"
                        logger.info("Strategy 1: Looking for 'push notification' in row text...")
                        all_buttons = await page.query_selector_all('a.button.select-factor')
                        logger.info(f"Found {len(all_buttons)} Select button(s)")

                        clicked = False
                        for idx, button in enumerate(all_buttons):
                            try:
                                # Get parent row to check text
                                parent_row = await button.evaluate_handle('el => el.closest(".authenticator-row")')
                                row_text = await parent_row.evaluate('el => el.textContent') if parent_row else ""
                                logger.info(f"Button {idx+1} parent row text: {row_text.strip()}")

                                if 'push notification' in row_text.lower():
                                    logger.info(f"✓ Found push notification button (button {idx+1}) - clicking!")
                                    await button.click()
                                    clicked = True
                                    # Wait for page to update after click
                                    await asyncio.sleep(1)
                                    break
                            except Exception as e:
                                logger.warning(f"Error checking button {idx+1}: {e}")
                                continue

                        # Strategy 2: Try aria-label if Strategy 1 failed
                        if not clicked:
                            logger.info("Strategy 2: Looking for 'push notification' in aria-label...")
                            for idx, button in enumerate(all_buttons):
                                try:
                                    aria_label = await button.get_attribute('aria-label')
                                    logger.info(f"Button {idx+1} aria-label: {aria_label}")

                                    if aria_label and 'push notification' in aria_label.lower():
                                        logger.info(f"✓ Found push notification button by aria-label - clicking!")
                                        await button.click()
                                        clicked = True
                                        # Wait for page to update after click
                                        await asyncio.sleep(1)
                                        break
                                except Exception as e:
                                    logger.warning(f"Error checking button {idx+1} aria-label: {e}")
                                    continue

                        if not clicked:
                            logger.error("Could not find push notification button - will NOT click random button to avoid triggering PIV")
                            raise Exception("Failed to find push notification MFA button")

                    except Exception as e:
                        logger.error(f"Error clicking MFA Select button: {e}", exc_info=True)
                        # Take a screenshot for debugging
                        try:
                            import tempfile
                            screenshot_path = tempfile.mktemp(suffix='.png')
                            await page.screenshot(path=screenshot_path)
                            logger.error(f"Screenshot saved to: {screenshot_path}")
                        except:
                            pass
                        raise

                    # Extract MFA number - wait for it to appear (page might need to update)
                    logger.info("Waiting for MFA number element to appear...")
                    try:
                        number_elem = await page.wait_for_selector(
                            '.phone--number[data-se="challenge-number"]',
                            timeout=15000  # 15 seconds timeout
                        )
                        self.mfa_number = await number_elem.text_content()
                        logger.info(f"MFA number: {self.mfa_number}")
                        self.status = "waiting_for_mfa_approval"

                        # Don't close browser - wait for MFA
                        return {
                            'status': 'mfa_required',
                            'mfa_number': self.mfa_number,
                            'message': f'Tap {self.mfa_number} in your Okta Verify app',
                            'continue_url': f'/api/auth/auto-mfa-wait/{self.user_id}'
                        }
                    except Exception as wait_error:
                        logger.error(f"Timeout waiting for MFA number element: {wait_error}")
                        # Fall through to check other layouts

            # Layout 2: Direct push page - number already displayed (no selection needed)
            if mfa_push_page:
                logger.info("Direct MFA push page - extracting number...")
                number_elem = await page.query_selector('.phone--number[data-se="challenge-number"]')
                if number_elem:
                    self.mfa_number = await number_elem.text_content()
                    logger.info(f"MFA number: {self.mfa_number}")
                    self.status = "waiting_for_mfa_approval"

                    # Don't close browser - wait for MFA
                    return {
                        'status': 'mfa_required',
                        'mfa_number': self.mfa_number,
                        'message': f'Tap {self.mfa_number} in your Okta Verify app',
                        'continue_url': f'/api/auth/auto-mfa-wait/{self.user_id}'
                    }
                else:
                    logger.error("Direct push page detected but couldn't find MFA number")

            # PIV card error - fallback
            if 'cert/error' in current_url and 'piv.card' in current_url:
                logger.error("PIV card error detected - authentication failed")
                self.error = "PIV certificate authentication error"
                await self._close_browser()
                return {'status': 'error', 'error': self.error}

            # Unexpected page state - CAPTURE DEBUG INFO
            logger.error(f"Unexpected authentication state - URL: {current_url}")

            # Capture debugging information
            try:
                from datetime import datetime
                from pathlib import Path

                # Create debug directory if it doesn't exist
                debug_dir = Path('debug')
                debug_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                # 1. Screenshot
                screenshot_path = debug_dir / f"auth_fail_user{self.user_id}_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                logger.error(f"DEBUG: Saved screenshot to {screenshot_path}")

                # 2. Page HTML
                html_path = debug_dir / f"auth_fail_user{self.user_id}_{timestamp}.html"
                page_content = await page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page_content)
                logger.error(f"DEBUG: Saved HTML to {html_path}")

                # 3. Page title and other details
                page_title = await page.title()
                logger.error(f"DEBUG: Page title: {page_title}")

                # 4. Check for error messages on page
                try:
                    error_elements = await page.query_selector_all('.okta-form-infobox-error, .o-form-error-container, [role="alert"]')
                    if error_elements:
                        logger.error(f"DEBUG: Found {len(error_elements)} error element(s) on page")
                        for idx, elem in enumerate(error_elements):
                            error_text = await elem.text_content()
                            if error_text and error_text.strip():
                                logger.error(f"DEBUG: Error {idx+1}: {error_text.strip()}")
                except Exception as e:
                    logger.warning(f"Could not check for error messages: {e}")

                # 5. Check if password field is still visible (indicates failed login)
                password_field = await page.query_selector('input[name="credentials.passcode"]')
                if password_field:
                    logger.error("DEBUG: Password field still visible - login likely failed (wrong password?)")

            except Exception as debug_e:
                logger.warning(f"Failed to capture debug info: {debug_e}")

            self.error = "Unexpected authentication state - check debug files for details"
            await self._close_browser()
            return {'status': 'error', 'error': self.error}

        except Exception as e:
            self.error = str(e)
            logger.error(f"Authentication failed for user {self.user_id}: {e}", exc_info=True)
            await self._close_browser()
            return {'status': 'error', 'error': str(e)}

    async def _close_browser(self):
        """Helper to close browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info(f"Browser closed for user {self.user_id}")
        except Exception as e:
            logger.warning(f"Error closing browser for user {self.user_id}: {e}")

    async def wait_for_mfa(self, timeout: int = 120) -> dict:
        """Wait for MFA completion"""
        try:
            # Get the page from context
            pages = self.context.pages
            if not pages:
                return {'status': 'error', 'error': 'Browser session lost'}
            page = pages[0]  # Use the first page

            logger.info(f"Waiting for MFA completion (timeout: {timeout}s)")

            # Wait for navigation to finder
            await page.wait_for_url('**/finder/**', timeout=timeout * 1000)

            logger.info("✓ MFA completed successfully")
            await asyncio.sleep(5)

            # Verify cookies
            storage_state = await self.context.storage_state()
            cookies = storage_state.get('cookies', [])
            logger.info(f"✓ Captured {len(cookies)} cookies after MFA")

            await self._close_browser()

            return {
                'status': 'success',
                'session_data': storage_state,  # Return session data for compatibility
                'message': 'Authentication successful with MFA',
                'cookies_count': len(cookies)
            }

        except Exception as e:
            logger.error(f"MFA wait error for user {self.user_id}: {e}")
            await self._close_browser()
            return {'status': 'error', 'error': str(e)}
