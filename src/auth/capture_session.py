"""
One-time session capture script for SpaceIQ authentication.

This script connects to a manually-launched browser via CDP (Chrome DevTools Protocol)
to capture the authenticated session state after manual SSO/2FA login.

Usage:
    python src/auth/capture_session.py

IMPORTANT: This script is designed to be run ONCE to establish the initial session.
The captured session can then be reused for all automated runs until it expires.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright
from config import Config
import platform


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


def print_instructions():
    """Print step-by-step instructions for the user"""
    print("\n" + "=" * 70)
    print("SpaceIQ Bot - Session Capture Tool")
    print("=" * 70)
    print("\nThis tool will capture your authenticated SpaceIQ session.")
    print("\nSTEPS TO FOLLOW:")
    print("\n1. Copy the Chrome launch command shown below")
    print("2. Open a NEW terminal/command prompt window")
    print("3. Paste and run the command")
    print("4. In the opened browser, navigate to SpaceIQ and complete login (SSO/2FA)")
    print("5. Once logged in, return here and press Enter")
    print("6. Your session will be saved automatically")
    print("\n" + "=" * 70)


async def capture_session():
    """Main function to capture authenticated session"""

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        return False

    print_instructions()

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
    print("CHROME LAUNCH COMMAND (copy this entire line):")
    print(f"{'─' * 70}")

    if platform.system() == "Windows":
        print(f'"{chrome_path}" --remote-debugging-port={Config.CDP_PORT} --user-data-dir="{user_data_dir}"')
    else:
        print(f'"{chrome_path}" --remote-debugging-port={Config.CDP_PORT} --user-data-dir="{user_data_dir}"')

    print(f"{'─' * 70}\n")

    input("Press Enter AFTER you have:\n  1. Run the command above in a NEW terminal\n  2. Completed login in the opened browser\n")

    print("\n⏳ Connecting to browser via CDP...")

    try:
        async with async_playwright() as p:
            # Connect to the manually launched browser
            print(f"   Connecting to localhost:{Config.CDP_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{Config.CDP_PORT}")

            print("✅ Connected successfully!")

            # Get the default context (the one with the manual session)
            contexts = browser.contexts
            if not contexts:
                print("❌ No browser contexts found. Make sure the browser is running.")
                return False

            context = contexts[0]
            pages = context.pages

            if not pages:
                print("⚠️  No pages found. Make sure you have SpaceIQ open in the browser.")
                return False

            print(f"   Found {len(pages)} page(s)")

            # Save the storage state
            print(f"\n⏳ Capturing session state...")
            await context.storage_state(path=str(Config.AUTH_STATE_FILE))

            print(f"✅ Session saved successfully to: {Config.AUTH_STATE_FILE}")
            print("\n" + "=" * 70)
            print("SUCCESS! Authentication capture complete.")
            print("=" * 70)
            print("\nYou can now:")
            print("1. Close the manually opened browser")
            print("2. Run the main bot with: python main.py")
            print("\nNote: Re-run this script if your session expires.")
            print("=" * 70 + "\n")

            await browser.close()
            return True

    except Exception as e:
        print(f"\n❌ Error during session capture: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome was launched with the exact command provided")
        print(f"2. Verify Chrome is running on port {Config.CDP_PORT}")
        print("3. Ensure you completed the login process in the browser")
        print("4. Try closing Chrome completely and starting over")
        return False


if __name__ == "__main__":
    success = asyncio.run(capture_session())
    sys.exit(0 if success else 1)
