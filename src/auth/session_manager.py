"""
Session Manager for SpaceIQ Bot

Handles loading and validating stored authentication sessions.
Creates high-fidelity browser contexts with pre-authenticated state.
Supports transparent decryption of encrypted auth files.
"""

from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext
from config import Config
from src.utils.auth_encryption import load_encrypted_session


class SessionManager:
    """Manages authenticated browser sessions"""

    def __init__(self, headless: bool = None, auth_file: str = None):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.playwright = None
        # Override Config.HEADLESS if explicitly provided
        self.headless = headless if headless is not None else Config.HEADLESS
        # Store user-specific auth file path
        self.auth_file = auth_file

    async def initialize(self) -> BrowserContext:
        """
        Initialize a high-fidelity browser with authenticated session.

        Returns:
            BrowserContext: Authenticated browser context ready for automation

        Raises:
            FileNotFoundError: If auth state file doesn't exist
            Exception: If browser initialization fails
        """

        # Use user-specific auth file if provided, otherwise use global config
        auth_path = Path(self.auth_file) if self.auth_file else Config.AUTH_STATE_FILE

        # Check if auth state exists
        if not auth_path.exists():
            raise FileNotFoundError(
                f"\n[ERROR] Authentication file not found: {auth_path}\n\n"
                f"Please run the session warming script first:\n"
                f"    python auto_warm_session.py\n"
            )

        # print(f"[INFO] Initializing authenticated browser session...")

        # Load and decrypt session (transparent - works with encrypted or plain JSON)
        print(f"[DEBUG] Loading session from: {auth_path}")
        session_data = load_encrypted_session(auth_path)

        if not session_data:
            raise Exception(
                f"\n[ERROR] Failed to load/decrypt authentication file\n\n"
                f"The auth file might be encrypted for a different user/machine.\n"
                f"Please delete the file and re-authenticate:\n"
                f"    rm {Config.AUTH_STATE_FILE}\n"
                f"    python auto_warm_session.py\n"
            )

        # Debug: Log session structure
        print(f"[DEBUG] Session loaded successfully")
        print(f"[DEBUG]   - Cookies: {len(session_data.get('cookies', []))}")
        print(f"[DEBUG]   - Origins: {len(session_data.get('origins', []))}")

        # Check for important authentication cookies
        auth_cookies = []
        for cookie in session_data.get('cookies', []):
            cookie_name = cookie.get('name', '')
            cookie_domain = cookie.get('domain', '')
            if any(keyword in cookie_name.lower() or keyword in cookie_domain.lower()
                   for keyword in ['spaceiq', 'okta', 'auth', 'session', 'token', 'sid', 'jwt']):
                auth_cookies.append(f"{cookie_name} @ {cookie_domain}")

        print(f"[DEBUG]   - Auth cookies: {auth_cookies}")

        # Launch Playwright
        self.playwright = await async_playwright().start()

        # Launch browser (high-fidelity, not CDP)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',  # Avoid detection
            ]
        )

        # print(f"[INFO] Browser launched")

        # Create context with decrypted authentication state
        # Pass session_data dict directly (not file path)
        self.context = await self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Set default timeout
        self.context.set_default_timeout(Config.TIMEOUT)

        # print(f"[INFO] Authenticated context created")
        # print(f"       Session file: {auth_path}")

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


async def create_authenticated_context(auth_file: str = None) -> BrowserContext:
    """
    Helper function to quickly create an authenticated browser context.

    Args:
        auth_file: Optional path to user-specific auth file

    Returns:
        BrowserContext: Ready-to-use authenticated context

    Example:
        context = await create_authenticated_context()
        page = await context.new_page()
        await page.goto("https://spaceiq.com")
    """
    manager = SessionManager(auth_file=auth_file)
    return await manager.initialize()
