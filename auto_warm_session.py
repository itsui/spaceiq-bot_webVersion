"""
Automated Session Warmer Script

Automatically launches browser, navigates to SpaceIQ, and maintains session.
Uses the same authentication method as headless booking (storage_state with auth.json).

Usage:
    python auto_warm_session.py            # Standard mode (opens browser, waits for login if needed)
    python auto_warm_session.py --headless # Headless mode (only works if already logged in)

How it works:
    1. Loads existing session from auth.json (if exists)
    2. Launches browser and navigates to SpaceIQ floor view
    3. Checks login status:
       - If logged in: Saves refreshed session and exits
       - If logged out: Opens browser window for manual SSO login, waits, then saves session
    4. Session is saved to auth.json for use by booking scripts

Schedule this to run before booking scripts to ensure fresh session.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config
from src.utils.auth_encryption import load_encrypted_session


async def auto_warm_session(headless: bool = False):
    """
    Automatically warm the session by launching browser and checking login status.

    Args:
        headless: If True, runs in headless mode (only works if already logged in)

    Returns:
        True if session is valid, False otherwise
    """
    print("\n" + "=" * 70)
    print("         Automated Session Warmer")
    print("=" * 70)
    print(f"\nMode: {'Headless' if headless else 'Headed (with browser window)'}")
    print(f"Target: {Config.SPACEIQ_URL}/finder/building/LC/floor/2")
    print("=" * 70 + "\n")

    # Check if auth state exists
    auth_exists = Config.AUTH_STATE_FILE.exists()
    if not auth_exists:
        print("[WARNING] No existing session found. Will need to login.")
        if headless:
            print("[ERROR] Cannot login in headless mode without existing session!")
            print("Run without --headless flag first to complete initial login.")
            return False

    try:
        async with async_playwright() as p:
            print("[INFO] Launching browser...")

            # Launch browser (same method as headless booking)
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # Avoid detection
                ],
            )

            print("[INFO] Browser launched successfully")

            # Create context with saved authentication state (if exists)
            if auth_exists:
                print(f"[INFO] Loading existing session from {Config.AUTH_STATE_FILE}")

                # Load and decrypt session
                session_data = load_encrypted_session(Config.AUTH_STATE_FILE)

                if not session_data:
                    print("[WARNING] Could not load/decrypt session - will need to login")
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                else:
                    context = await browser.new_context(
                        storage_state=session_data,  # Use decrypted dict
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
            else:
                print("[INFO] Creating new browser context (no existing session)")
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

            # Create or get page
            if context.pages:
                page = context.pages[0]
            else:
                page = await context.new_page()

            # Navigate to SpaceIQ floor view
            target_url = f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/LC/floor/2"
            print(f"[INFO] Navigating to {target_url}")

            try:
                await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[WARNING] Navigation timeout or error: {e}")
                print("[INFO] Checking current URL anyway...")

            # Wait a bit for any redirects
            await asyncio.sleep(3)

            current_url = page.url
            print(f"[INFO] Current URL: {current_url}")

            # Check if we're logged in
            if "/login" in current_url:
                print("\n" + "=" * 70)
                print("         SESSION EXPIRED - LOGIN REQUIRED")
                print("=" * 70)

                if headless:
                    print("\n[ERROR] Cannot login in headless mode!")
                    print("Run without --headless flag to complete login.")
                    await context.close()
                    return False

                print("\nThe browser window is now open.")
                print("Please complete these steps:")
                print("  1. Click 'Login with SSO' in the browser window")
                print("  2. Enter your company email")
                print("  3. Complete SSO authentication")
                print("  4. Wait until you see the floor map with desks")
                print("\nThis script will automatically detect when login is complete...")
                print("=" * 70 + "\n")

                # Wait for login to complete (URL changes from /login to /finder)
                try:
                    print("[INFO] Waiting for login (max 5 minutes)...")
                    await page.wait_for_url(
                        lambda url: "/login" not in url and "/finder/building/" in url,
                        timeout=300000  # 5 minutes
                    )
                    print("\n[SUCCESS] Login detected!")
                    await asyncio.sleep(2)  # Wait for page to settle
                except Exception as e:
                    print(f"\n[ERROR] Login timeout: {e}")
                    print("Please try again or check your SSO configuration.")
                    await context.close()
                    await browser.close()
                    return False

            elif "/finder/building/" in current_url:
                print("\n[SUCCESS] Already logged in!")
            else:
                print(f"\n[WARNING] Unexpected URL: {current_url}")
                print("Expected to be on floor view or login page.")
                if not headless:
                    print("\nPlease navigate to the floor view manually in the browser window.")
                    print(f"Target: {target_url}")
                    input("\nPress Enter after you've navigated to the floor view...")
                else:
                    await context.close()
                    await browser.close()
                    return False

            # Save session state
            print(f"\n[INFO] Saving session state...")
            Config.AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Save to temporary file first (Playwright requires direct path)
            temp_file = Config.AUTH_STATE_FILE.parent / "temp_auth.json"
            await context.storage_state(path=str(temp_file))

            # Read the saved session and encrypt it
            import json
            from src.utils.auth_encryption import save_encrypted_session

            with open(temp_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Save with encryption
            if save_encrypted_session(Config.AUTH_STATE_FILE, session_data):
                # Remove temp file
                temp_file.unlink()
                print(f"[SUCCESS] Session saved and encrypted: {Config.AUTH_STATE_FILE}")
            else:
                # If encryption fails, use unencrypted version
                temp_file.rename(Config.AUTH_STATE_FILE)
                print(f"[WARNING] Session saved without encryption: {Config.AUTH_STATE_FILE}")
            print("\n" + "=" * 70)
            print("         Session Warmed Successfully!")
            print("=" * 70)
            print("\nYour session is now active and ready for booking.")
            print("The booking scripts will use this session automatically.")
            print("\nNext steps:")
            print("  - Run: python multi_date_book.py")
            print("  - Or wait for scheduled booking to run automatically")
            print("\nNote: Re-run this script when your session expires.")
            print("=" * 70 + "\n")

            # Close browser
            await context.close()
            await browser.close()
            return True

    except Exception as e:
        print(f"\n[ERROR] Failed to warm session: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("  1. Ensure Chrome is installed")
        print("  2. Check your internet connection")
        print("  3. Verify SpaceIQ URL is correct in config.py")
        print("  4. Try running without --headless flag")
        return False


async def main():
    """Main entry point"""
    # Check for headless flag (explicit override)
    force_headless = "--headless" in sys.argv or "-h" in sys.argv
    force_headed = "--headed" in sys.argv

    # Smart mode: Auto-detect based on auth file existence
    if not force_headless and not force_headed:
        # Check if auth exists - if yes, try headless first
        auth_exists = Config.AUTH_STATE_FILE.exists()
        if auth_exists:
            print("[INFO] Existing session found - trying headless mode first...")
            success = await auto_warm_session(headless=True)

            if success:
                exit(0)
            else:
                # Headless failed - probably session expired
                print("\n[WARNING] Headless mode failed - retrying with browser window...")
                print("[INFO] You may need to login again...\n")
                success = await auto_warm_session(headless=False)
        else:
            # No auth file - need browser for SSO login
            print("[INFO] No existing session - opening browser for login...")
            success = await auto_warm_session(headless=False)
    else:
        # User explicitly chose mode
        headless = force_headless
        success = await auto_warm_session(headless=headless)

    if not success:
        print("\n[FAILED] Session warming failed.")
        exit(1)

    exit(0)


if __name__ == "__main__":
    asyncio.run(main())
