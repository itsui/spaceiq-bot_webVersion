"""
Session Validator

Checks if session is still valid before running headless mode.
If session expired, automatically opens visible browser for re-login.
Supports encrypted auth files transparently.
"""

import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext
from pathlib import Path
from config import Config
from src.utils.auth_encryption import load_encrypted_session


async def validate_and_refresh_session(force_headless: bool = False, auth_file: str = None) -> tuple[bool, bool]:
    """
    Validate session and refresh if needed.

    If session is expired and headless mode requested, automatically switches
    to visible browser so user can login, then returns to headless.

    Args:
        force_headless: True if user requested headless mode
        auth_file: Path to auth file (if None, uses Config.AUTH_STATE_FILE)

    Returns:
        Tuple of (session_valid, should_use_headless)
        - If session valid: (True, force_headless)
        - If session expired and user logged in: (True, force_headless)
        - If session expired and user cancelled: (False, False)
    """

    # Use provided auth file or fall back to default
    auth_file_path = Path(auth_file) if auth_file else Config.AUTH_STATE_FILE

    # Check if auth file exists
    if not auth_file_path.exists():
        print("\n[WARNING] No session file found. Need to login first.")
        print("Running session warmer...")

        # Need visible browser for first-time login
        return await _run_session_warmer(headless=False, force_headless=force_headless)

    # Try to validate existing session
    # print("[INFO] Validating session...")

    try:
        # Load and decrypt session first
        session_data = load_encrypted_session(auth_file_path)

        if not session_data:
            print("[WARNING] Could not load/decrypt session file")
            return await _run_session_warmer(headless=False, force_headless=force_headless)

        async with async_playwright() as p:
            # Quick test with existing session (headless for speed)
            browser = await p.chromium.launch(headless=True)
            # IMPORTANT: Use EXACT same settings as session_manager.py to avoid fingerprinting mismatch
            context = await browser.new_context(
                storage_state=session_data,  # Use decrypted dict, not file path
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            # Try to navigate to the app
            try:
                await page.goto(
                    f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/LC/floor/2",
                    timeout=15000,
                    wait_until="domcontentloaded"
                )

                # Wait a bit for any redirects
                await asyncio.sleep(2)

                current_url = page.url

                # Check if we got redirected to login
                if "/login" in current_url:
                    await browser.close()
                    print("[WARNING] Session expired (redirected to login page)")

                    # Need visible browser for re-login
                    return await _run_session_warmer(headless=False, force_headless=force_headless)

                else:
                    # Session is valid!
                    await browser.close()
                    # print("[SUCCESS] Session is valid")
                    return (True, force_headless)

            except Exception as e:
                await browser.close()
                print(f"[WARNING] Could not validate session: {e}")

                # Try to refresh session with visible browser
                return await _run_session_warmer(headless=False, force_headless=force_headless)

    except Exception as e:
        print(f"[ERROR] Session validation failed: {e}")
        return await _run_session_warmer(headless=False, force_headless=force_headless)


async def _run_session_warmer(headless: bool, force_headless: bool) -> tuple[bool, bool]:
    """
    Raise exception to tell user to re-authenticate via web interface.

    NOTE: This function used to open a headed browser for login, but that
    doesn't work in production. Now we raise an exception that the bot
    catches and tells the user to go to /auth/auto.

    Args:
        headless: Whether to run warmer in headless mode (always False for login)
        force_headless: Whether user wants headless mode for actual booking

    Returns:
        Never returns - always raises exception
    """
    # Raise exception with specific message for the user
    raise SessionExpiredException(
        "Session expired. Please re-authenticate via the web interface at /auth/auto"
    )


class SessionExpiredException(Exception):
    """Raised when session is expired and needs re-authentication"""
    pass
