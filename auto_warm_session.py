"""
Automated Session Warmer Script

Automatically launches browser, navigates to SpaceIQ, and maintains session.
This script eliminates the need to manually open terminals and run Chrome commands.

Usage:
    python auto_warm_session.py            # Standard mode (opens browser, waits for login if needed)
    python auto_warm_session.py --headless # Headless mode (only works if already logged in)

How it works:
    1. Launches browser with persistent session
    2. Navigates to SpaceIQ floor view
    3. Checks login status:
       - If logged in: Saves session and exits
       - If logged out: Opens browser window for manual SSO login, waits, then saves session
    4. Session is saved for use by booking scripts

Schedule this to run before booking scripts to ensure fresh session.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config


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

    # Setup browser data directory for persistent session
    user_data_dir = Config.AUTH_DIR / "browser_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            print("[INFO] Launching browser...")

            # Launch browser with persistent context (keeps cookies/sessions)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                channel="chrome",  # Use installed Chrome
                args=[
                    '--disable-blink-features=AutomationControlled',  # Avoid detection
                ],
                viewport={'width': 1920, 'height': 1080},
            )

            print("[INFO] Browser launched successfully")

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
                    return False

            # Save session state
            print(f"\n[INFO] Saving session state...")
            Config.AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(Config.AUTH_STATE_FILE))

            print(f"[SUCCESS] Session saved to: {Config.AUTH_STATE_FILE}")
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
    # Check for headless flag
    headless = "--headless" in sys.argv or "-h" in sys.argv

    success = await auto_warm_session(headless=headless)

    if not success:
        print("\n[FAILED] Session warming failed.")
        exit(1)

    exit(0)


if __name__ == "__main__":
    asyncio.run(main())
