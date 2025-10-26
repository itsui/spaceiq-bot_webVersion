"""
Session Warmer Script

Opens SpaceIQ and checks if session is still valid.
If logged out, waits for manual login.
Useful to run before scheduled booking to ensure session is fresh.

Usage:
    python warm_session.py

Recommended Schedule:
    - Tuesday 8:00 PM: Run this script (warm session for Wed booking)
    - Tuesday 11:59 PM: Run multi_date_book.py (book Wed seats)
    - Wednesday 11:59 PM: Run multi_date_book.py (book Thu seats)

This script uses the SAME approach as capture_session.py for maximum reliability.
"""

import asyncio
import platform
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config


def get_chrome_path():
    """Get the Chrome executable path based on OS"""
    system = platform.system()

    if system == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    elif system == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:  # Linux
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]

    for path in paths:
        if Path(path).exists():
            return path

    return None


async def warm_session():
    """
    Warm the session using manual Chrome launch (same as capture_session.py).
    This approach works reliably with SSO.
    """
    print("\n" + "=" * 70)
    print("         Session Warmer - Checking Login Status")
    print("=" * 70)
    print("\nThis script uses the same reliable method as the initial setup.")
    print("You'll manually launch Chrome and login if needed.")
    print("=" * 70 + "\n")

    # Get Chrome executable path
    chrome_path = get_chrome_path()
    if not chrome_path:
        print("\n⚠️  Could not auto-detect Chrome/Edge installation.")
        chrome_path = input("Please enter the full path to Chrome/Edge executable: ").strip()
        if not Path(chrome_path).exists():
            print(f"❌ Path not found: {chrome_path}")
            return False

    # Generate the launch command
    user_data_dir = Config.AUTH_DIR / "browser_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'─' * 70}")
    print("STEP 1: LAUNCH CHROME WITH THIS COMMAND")
    print(f"{'─' * 70}")
    print("\nCopy this ENTIRE command and run it in a NEW terminal window:\n")

    if platform.system() == "Windows":
        print(f'"{chrome_path}" --remote-debugging-port={Config.CDP_PORT} --user-data-dir="{user_data_dir}"')
    else:
        print(f'"{chrome_path}" --remote-debugging-port={Config.CDP_PORT} --user-data-dir="{user_data_dir}"')

    print(f"\n{'─' * 70}")
    print("STEP 2: NAVIGATE AND LOGIN")
    print(f"{'─' * 70}")
    print(f"\nIn the Chrome window that opens:")
    print(f"1. Navigate to: {Config.SPACEIQ_URL}/finder/building/LC/floor/2")
    print(f"2. If logged out, click 'Login with SSO'")
    print(f"3. Enter your company email")
    print(f"4. Complete login on your company's SSO page")
    print(f"5. Wait until you see the floor map with desks")
    print(f"\n{'─' * 70}\n")

    input("Press Enter AFTER you have:\n  1. Run the Chrome command in a NEW terminal\n  2. Completed login in Chrome (or verified you're still logged in)\n")

    print("\n⏳ Connecting to your Chrome browser...")

    try:
        async with async_playwright() as p:
            # Connect to the manually launched browser
            print(f"   Connecting to localhost:{Config.CDP_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{Config.CDP_PORT}")

            print("✅ Connected successfully!")

            # Get the default context (the one with the manual session)
            contexts = browser.contexts
            if not contexts:
                print("❌ No browser contexts found. Make sure Chrome is running with the command above.")
                return False

            context = contexts[0]
            pages = context.pages

            if not pages:
                print("⚠️  No pages found. Make sure you opened SpaceIQ in the Chrome window.")
                return False

            print(f"   Found {len(pages)} page(s)")

            # Check the current URL
            current_page = pages[0]
            current_url = current_page.url
            print(f"   Current URL: {current_url}")

            # Verify we're logged in (not on login page)
            if "/login" in current_url:
                print("\n⚠️  You're still on the login page!")
                print("   Please complete the login in the Chrome window, then run this script again.")
                await browser.close()
                return False

            if "/finder/building/" not in current_url:
                print("\n⚠️  You're not on the floor view page!")
                print(f"   Please navigate to: {Config.SPACEIQ_URL}/finder/building/LC/floor/2")
                print("   Then run this script again.")
                await browser.close()
                return False

            # Save the storage state
            print(f"\n⏳ Capturing session state...")
            await context.storage_state(path=str(Config.AUTH_STATE_FILE))

            print(f"✅ Session saved successfully to: {Config.AUTH_STATE_FILE}")
            print("\n" + "=" * 70)
            print("         Session Warmed Successfully")
            print("=" * 70)
            print("\nYou are logged in and ready for booking.")
            print("The scheduled booking script will use this session.")
            print("\nYou can now:")
            print("1. Close the Chrome window (or keep it open)")
            print("2. Run your booking scripts: python multi_date_book.py")
            print("\nNote: Re-run this script when your session expires.")
            print("=" * 70 + "\n")

            await browser.close()
            return True

    except Exception as e:
        print(f"\n❌ Error during session warming: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome was launched with the exact command provided above")
        print(f"2. Verify Chrome is running on port {Config.CDP_PORT}")
        print("3. Ensure you completed the login process in Chrome")
        print("4. Try closing Chrome completely and starting over")
        print("\nCommon issues:")
        print("- If you see 'Connection refused', Chrome is not running with --remote-debugging-port")
        print("- If you see 'No contexts found', Chrome didn't launch correctly")
        return False


async def main():
    success = await warm_session()

    if not success:
        print("\n❌ Session warming failed. Please try again.")

    input("\nPress Enter to exit...")
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
