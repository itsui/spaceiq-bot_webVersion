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
            context = await browser.new_context(
                storage_state=session_data,  # Use decrypted dict, not file path
                viewport={'width': 1920, 'height': 1080}
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
    Run session warming with visible browser for login.

    Args:
        headless: Whether to run warmer in headless mode (always False for login)
        force_headless: Whether user wants headless mode for actual booking

    Returns:
        Tuple of (success, should_use_headless)
    """
    print("\n" + "=" * 70)
    print("         SESSION EXPIRED - OPENING BROWSER FOR LOGIN")
    print("=" * 70)
    print("\nYour session has expired. Opening browser for re-login...")
    print("After you login, the bot will continue automatically.")
    if force_headless:
        print("Booking will resume in HEADLESS mode after login.")
    print("=" * 70 + "\n")

    try:
        async with async_playwright() as p:
            # Always use visible browser for login
            browser = await p.chromium.launch(
                headless=False,  # Must be visible for SSO login
                channel="chrome"
            )

            # Create new context (fresh session)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            # Navigate to the app
            target_url = f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/LC/floor/2"
            print(f"[INFO] Navigating to {target_url}")

            try:
                await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            except:
                pass  # Might timeout if redirected to login

            await asyncio.sleep(2)
            current_url = page.url

            # Check if on login page
            if "/login" in current_url:
                print("\n" + "=" * 70)
                print("         PLEASE LOGIN")
                print("=" * 70)
                print("\nBrowser window is now open.")
                print("Please complete these steps:")
                print("  1. Click 'Login with SSO'")
                print("  2. Enter your company email")
                print("  3. Complete SSO authentication")
                print("  4. Wait until you see the floor map")
                print("\nBot will detect login automatically...")
                print("=" * 70 + "\n")

                # Wait for login (URL changes from /login to /finder)
                try:
                    await page.wait_for_url(
                        lambda url: "/login" not in url and "/finder/building/" in url,
                        timeout=300000  # 5 minutes
                    )
                    print("\n[SUCCESS] Login detected!")
                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"\n[ERROR] Login timeout: {e}")
                    print("Please try again or check your SSO settings.")
                    await browser.close()
                    return (False, False)

            else:
                print("[INFO] Already logged in (session restored)")

            # Save the session
            print("[INFO] Saving session...")
            Config.AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Save to temporary file first
            temp_file = Config.AUTH_STATE_FILE.parent / "temp_auth.json"
            await context.storage_state(path=str(temp_file))

            # Read and encrypt the session
            import json
            from src.utils.auth_encryption import save_encrypted_session

            with open(temp_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Save with encryption
            if save_encrypted_session(Config.AUTH_STATE_FILE, session_data):
                temp_file.unlink()
                print(f"[SUCCESS] Session saved and encrypted: {Config.AUTH_STATE_FILE}")
            else:
                temp_file.rename(Config.AUTH_STATE_FILE)
                print(f"[WARNING] Session saved without encryption: {Config.AUTH_STATE_FILE}")

            # Close browser
            await browser.close()

            print("\n" + "=" * 70)
            print("         SESSION REFRESHED - CONTINUING BOOKING")
            print("=" * 70)
            if force_headless:
                print("\nResuming in HEADLESS mode (no browser window)")
            print("=" * 70 + "\n")

            return (True, force_headless)

    except Exception as e:
        print(f"\n[ERROR] Session warming failed: {e}")
        import traceback
        traceback.print_exc()
        return (False, False)
