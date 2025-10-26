"""
SpaceIQ Workflow Recorder

Opens SpaceIQ and records elements you interact with.
This helps us automatically discover the correct selectors.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from config import Config
from src.auth.session_manager import SessionManager
import json
from datetime import datetime


async def record_workflow():
    """Record a manual workflow to discover selectors"""

    print("\n" + "=" * 70)
    print("SpaceIQ Workflow Recorder")
    print("=" * 70)
    print("\n📋 WHAT THIS DOES:")
    print("1. Opens SpaceIQ with your authenticated session")
    print("2. Opens Chrome DevTools on the side")
    print("3. You perform your booking manually")
    print("4. Take screenshots and notes as you go")
    print("5. Describe your workflow to me")
    print("\n💡 TIP: Keep DevTools' 'Elements' tab open to see HTML structure")
    print("=" * 70 + "\n")

    # Check auth file
    if not Config.AUTH_STATE_FILE.exists():
        print("❌ Authentication file not found!")
        print("Please run: python src/auth/capture_session.py")
        return

    input("Press Enter to start...")

    try:
        session_manager = SessionManager()
        context = await session_manager.initialize()

        # Create page
        page = await context.new_page()

        print(f"\n⏳ Opening SpaceIQ...")
        await page.goto(Config.SPACEIQ_URL)
        print("✅ SpaceIQ loaded")

        # Inject a helper script to highlight elements on hover
        await page.evaluate("""
            // Helper to highlight elements on hover
            let lastHighlighted = null;

            document.addEventListener('mouseover', (e) => {
                if (lastHighlighted) {
                    lastHighlighted.style.outline = '';
                }
                e.target.style.outline = '2px solid red';
                lastHighlighted = e.target;
            });

            // Log clicks
            document.addEventListener('click', (e) => {
                const el = e.target;
                const info = {
                    tag: el.tagName,
                    id: el.id,
                    classes: el.className,
                    text: el.textContent?.substring(0, 50),
                    role: el.getAttribute('role'),
                    ariaLabel: el.getAttribute('aria-label'),
                    type: el.type,
                    name: el.name,
                    placeholder: el.placeholder,
                };
                console.log('CLICKED:', JSON.stringify(info));
            });

            console.log('🎯 Element inspector active! Elements will highlight on hover.');
        """)

        # Set up console listener
        recorded_clicks = []

        def handle_console(msg):
            text = msg.text
            if text.startswith('CLICKED:'):
                try:
                    data = json.loads(text.replace('CLICKED:', ''))
                    recorded_clicks.append(data)
                    print(f"\n📝 Recorded click: {data.get('tag', 'unknown')} - {data.get('text', '')[:30]}")
                except:
                    pass
            print(f"   [Browser] {text}")

        page.on("console", handle_console)

        print("\n" + "=" * 70)
        print("🎯 RECORDING MODE ACTIVE")
        print("=" * 70)
        print("\n✨ Elements will highlight RED when you hover over them")
        print("\n📝 NOW DO THIS:")
        print("1. Perform your complete booking workflow")
        print("2. Click each button/field you normally would")
        print("3. I'm recording what you click!")
        print("4. When done, come back here and press Ctrl+C")
        print("\n⏳ Browser is open and recording...")
        print("=" * 70 + "\n")

        try:
            # Keep browser open indefinitely
            await asyncio.sleep(3600)
        except KeyboardInterrupt:
            print("\n\n✅ Recording stopped by user")

        # Save results
        print("\n" + "=" * 70)
        print("Saving Recording")
        print("=" * 70)

        output_dir = Path("inspector_output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save screenshot
        screenshot_path = output_dir / f"final_page_{timestamp}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"📸 Screenshot: {screenshot_path}")

        # Save HTML
        html_path = output_dir / f"page_html_{timestamp}.html"
        html_path.write_text(await page.content(), encoding='utf-8')
        print(f"📄 HTML: {html_path}")

        # Save recorded clicks
        if recorded_clicks:
            clicks_path = output_dir / f"recorded_clicks_{timestamp}.json"
            clicks_path.write_text(json.dumps(recorded_clicks, indent=2))
            print(f"🖱️  Clicks: {clicks_path}")

            print(f"\n📊 Recorded {len(recorded_clicks)} interactions:")
            for i, click in enumerate(recorded_clicks, 1):
                tag = click.get('tag', 'unknown')
                text = click.get('text', '')[:40]
                role = click.get('role', '')
                print(f"   {i}. {tag} {f'role={role}' if role else ''} - {text}")

        print("\n" + "=" * 70)
        print("✅ Recording saved to: inspector_output/")
        print("=" * 70)

        await session_manager.close()

        # Ask for description
        print("\n" + "=" * 70)
        print("📝 NEXT: Describe Your Workflow")
        print("=" * 70)
        print("\nPlease describe what you did in plain English.")
        print("I'll use this + the recorded data to create the selectors.")
        print("\nExample:")
        print('  "I clicked the Book Desk button, then selected Building LC')
        print('   Floor 2 from the dropdown, picked tomorrow\'s date from')
        print('   the calendar, and clicked Confirm."')
        print("\n" + "=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n💡 Make sure you've completed Step 3 (authentication capture) first!\n")
    asyncio.run(record_workflow())
