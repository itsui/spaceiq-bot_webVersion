"""
Session Manager for SpaceIQ Bot

Handles loading and validating stored authentication sessions.
Creates high-fidelity browser contexts with pre-authenticated state.
"""

from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext
from config import Config


class SessionManager:
    """Manages authenticated browser sessions"""

    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.playwright = None

    async def initialize(self) -> BrowserContext:
        """
        Initialize a high-fidelity browser with authenticated session.

        Returns:
            BrowserContext: Authenticated browser context ready for automation

        Raises:
            FileNotFoundError: If auth state file doesn't exist
            Exception: If browser initialization fails
        """

        # Check if auth state exists
        if not Config.AUTH_STATE_FILE.exists():
            raise FileNotFoundError(
                f"\n[ERROR] Authentication file not found: {Config.AUTH_STATE_FILE}\n\n"
                f"Please run the session capture script first:\n"
                f"    python src/auth/capture_session.py\n"
            )

        print(f"[INFO] Initializing authenticated browser session...")

        # Launch Playwright
        self.playwright = await async_playwright().start()

        # Launch browser (high-fidelity, not CDP)
        self.browser = await self.playwright.chromium.launch(
            headless=Config.HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',  # Avoid detection
            ]
        )

        print(f"[INFO] Browser launched")

        # Create context with saved authentication state
        self.context = await self.browser.new_context(
            storage_state=str(Config.AUTH_STATE_FILE),
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Set default timeout
        self.context.set_default_timeout(Config.TIMEOUT)

        print(f"[INFO] Authenticated context created")
        print(f"       Session file: {Config.AUTH_STATE_FILE}")

        return self.context

    async def close(self):
        """Clean up browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        print("[INFO] Browser session closed")

    async def __aenter__(self):
        """Context manager entry"""
        return await self.initialize()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()


async def create_authenticated_context() -> BrowserContext:
    """
    Helper function to quickly create an authenticated browser context.

    Returns:
        BrowserContext: Ready-to-use authenticated context

    Example:
        context = await create_authenticated_context()
        page = await context.new_page()
        await page.goto("https://spaceiq.com")
    """
    manager = SessionManager()
    return await manager.initialize()
