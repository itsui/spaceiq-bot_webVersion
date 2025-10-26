"""
Interactive Selector Inspector

This tool helps you discover the correct selectors for your SpaceIQ instance.
It opens SpaceIQ and allows you to interact with it while capturing element information.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright, Page
from config import Config
from src.auth.session_manager import SessionManager
import json
from datetime import datetime


class SelectorInspector:
    """Interactive tool to capture selectors from SpaceIQ"""

    def __init__(self):
        self.session_manager = SessionManager()
        self.captured_elements = []

    async def inspect(self):
        """Run the interactive inspection session"""

        print("\n" + "=" * 70)
        print("SpaceIQ Selector Inspector")
        print("=" * 70)
        print("\nThis tool will help you identify the correct selectors.")
        print("\n📋 INSTRUCTIONS:")
        print("1. A browser will open with SpaceIQ (already logged in)")
        print("2. Perform your booking workflow manually")
        print("3. The browser will stay open for you to explore")
        print("4. Press Ctrl+C in this terminal when done")
        print("5. Describe what you did, and I'll capture the selectors")
        print("=" * 70 + "\n")

        input("Press Enter to open SpaceIQ with developer tools...")

        try:
            # Initialize authenticated session
            context = await self.session_manager.initialize()

            # Create page
            page = await context.new_page()

            # Enable developer mode logging
            page.on("console", lambda msg: print(f"   [Browser] {msg.text}"))

            # Navigate to SpaceIQ
            print(f"\n⏳ Opening SpaceIQ: {Config.SPACEIQ_URL}")
            await page.goto(Config.SPACEIQ_URL)
            print("✅ SpaceIQ loaded\n")

            print("=" * 70)
            print("🎯 INTERACTIVE MODE ACTIVE")
            print("=" * 70)
            print("\nThe browser is now open and ready.")
            print("\n📝 DO THIS NOW:")
            print("1. In the browser, perform your booking workflow step by step")
            print("2. Take note of what you click, fill, and select")
            print("3. When done, come back here and press Ctrl+C")
            print("\n⏳ Waiting... (browser will stay open)")
            print("=" * 70 + "\n")

            # Keep browser open
            try:
                await asyncio.sleep(3600)  # Wait for 1 hour or until interrupted
            except KeyboardInterrupt:
                print("\n\n✅ Capture interrupted by user")

            print("\n" + "=" * 70)
            print("Browser Session Information")
            print("=" * 70)

            # Capture page information
            current_url = page.url
            page_title = await page.title()

            print(f"\nFinal URL: {current_url}")
            print(f"Page Title: {page_title}")

            # Ask user for workflow description
            print("\n" + "=" * 70)
            print("📝 DESCRIBE YOUR WORKFLOW")
            print("=" * 70)
            print("\nPlease describe the steps you took to make a booking.")
            print("For example:")
            print("  1. Clicked 'Book Now' button")
            print("  2. Selected location 'Building LC, Floor 2'")
            print("  3. Chose date from calendar")
            print("  4. etc.")
            print("\nI will use this to inspect the page and find the selectors.")
            print("\n(Press Ctrl+C when you're ready to close the browser)")

            try:
                await asyncio.sleep(3600)
            except KeyboardInterrupt:
                print("\n\n✅ Closing browser...")

            # Save page snapshot for analysis
            await self._save_page_snapshot(page)

            await self.session_manager.close()

        except Exception as e:
            print(f"\n❌ Error during inspection: {e}")
            import traceback
            traceback.print_exc()

    async def _save_page_snapshot(self, page: Page):
        """Save page information for analysis"""

        snapshot_dir = Path("inspector_output")
        snapshot_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save screenshot
        screenshot_path = snapshot_dir / f"page_screenshot_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\n📸 Screenshot saved: {screenshot_path}")

        # Save page HTML
        html_path = snapshot_dir / f"page_html_{timestamp}.html"
        content = await page.content()
        html_path.write_text(content, encoding='utf-8')
        print(f"📄 HTML saved: {html_path}")

        # Save page info
        info = {
            "url": page.url,
            "title": await page.title(),
            "timestamp": timestamp,
        }

        info_path = snapshot_dir / f"page_info_{timestamp}.json"
        info_path.write_text(json.dumps(info, indent=2))
        print(f"ℹ️  Info saved: {info_path}")

        print("\n" + "=" * 70)
        print("✅ Page snapshot saved to: inspector_output/")
        print("=" * 70)


async def main():
    inspector = SelectorInspector()
    await inspector.inspect()

    print("\n" + "=" * 70)
    print("Next Steps")
    print("=" * 70)
    print("\n1. Review the saved files in inspector_output/")
    print("2. Tell me what actions you performed")
    print("3. I'll help you identify the correct selectors")
    print("4. We'll update booking_page.py together")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
