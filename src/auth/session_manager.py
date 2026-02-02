"""
Session Manager for SpaceIQ Bot

NOW USES STORAGE_STATE APPROACH!
Auth captures storage_state (cookies + localStorage + sessionStorage).
Bot loads storage_state from database and applies it to new browser context.
This ensures ALL session data persists, including session-only cookies!
"""

from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext
from config import Config
from src.utils.auth_encryption import load_encrypted_session
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages authenticated browser sessions using storage_state"""

    def __init__(self, headless: bool = None, auth_file: str = None, user_id: int = None, session_data: dict = None):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.playwright = None
        # Override Config.HEADLESS if explicitly provided
        self.headless = headless if headless is not None else Config.HEADLESS
        # Store user-specific auth file path (for backward compatibility)
        self.auth_file = auth_file
        # User ID for persistent profile
        self.user_id = user_id
        # Pre-loaded session data (avoids database query outside app context)
        self.session_data = session_data

    async def initialize(self) -> BrowserContext:
        """
        Initialize browser using storage_state

        Priority:
        1. Pre-loaded session_data (if provided)
        2. Auth file (if provided)
        3. Database query by user_id (if in app context)

        Returns:
            BrowserContext: Authenticated browser context ready for automation
        """

        # If auth_file is provided, always use it (bot_manager saves session to temp file)
        if self.auth_file:
            logger.info(f"Using auth file: {self.auth_file}")
            return await self._initialize_legacy()

        # If user_id provided, use storage_state approach (query DB or use pre-loaded data)
        if self.user_id is not None:
            logger.info(f"Using storage_state for user {self.user_id}")
            return await self._initialize_with_persistent_profile()

        # Fallback to default auth file
        logger.warning("No user_id or auth_file provided - using default auth file")
        return await self._initialize_legacy()

    async def _initialize_with_persistent_profile(self) -> BrowserContext:
        """Initialize using ACTUAL persistent profile directory (FIXED - prevents fingerprinting mismatch)"""
        try:
            from pathlib import Path
            import json

            # Setup profile directory (same as AutoAuthWithPersistentProfile)
            base_dir = Path(__file__).parent.parent.parent / "playwright" / ".auth" / "profiles"
            profile_dir = base_dir / f"user_{self.user_id}"

            # Create profile directory if it doesn't exist
            profile_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Using persistent profile directory: {profile_dir}")

            # Launch Playwright
            self.playwright = await async_playwright().start()

            # Launch with PERSISTENT PROFILE (same browser fingerprint as authentication!)
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ],
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # Apply fresh database cookies if session_data is provided
            if self.session_data and 'cookies' in self.session_data:
                # Clear old cookies first to avoid conflicts
                existing_cookies = await self.context.cookies()
                if existing_cookies:
                    logger.info(f"Clearing {len(existing_cookies)} old cookies from persistent profile")
                    await self.context.clear_cookies()

                # Apply fresh cookies from database
                await self.context.add_cookies(self.session_data['cookies'])
                logger.info(f"✓ Applied {len(self.session_data['cookies'])} fresh cookies from database to persistent profile")

            # Apply localStorage if available
            if self.session_data and 'origins' in self.session_data:
                # We need a page to set localStorage
                page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                for origin in self.session_data.get('origins', []):
                    origin_url = origin.get('origin')
                    if origin_url:
                        try:
                            await page.goto(origin_url)
                            for item in origin.get('localStorage', []):
                                await page.evaluate(
                                    f"localStorage.setItem({json.dumps(item['name'])}, {json.dumps(item['value'])})"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to set localStorage for {origin_url}: {e}")
                logger.info("✓ Applied localStorage from database")

            # Set default timeout
            self.context.set_default_timeout(Config.TIMEOUT)

            logger.info(f"✓ Browser initialized for user {self.user_id} with persistent profile")
            return self.context

        except Exception as e:
            logger.error(f"Failed to initialize with persistent profile: {e}", exc_info=True)
            raise

    async def _initialize_legacy(self) -> BrowserContext:
        """Legacy initialization using cookies (OLD METHOD - may not work reliably)"""
        # Use user-specific auth file if provided, otherwise use global config
        auth_path = Path(self.auth_file) if self.auth_file else Config.AUTH_STATE_FILE

        # Check if auth state exists
        if not auth_path.exists():
            raise FileNotFoundError(
                f"\n[ERROR] Authentication file not found: {auth_path}\n\n"
                f"Please authenticate via the web interface first.\n"
            )

        # Load and decrypt session
        session_data = load_encrypted_session(auth_path)

        if not session_data:
            raise Exception(
                f"\n[ERROR] Failed to load/decrypt authentication file\n\n"
                f"Please re-authenticate via the web interface.\n"
            )

        # Launch Playwright
        self.playwright = await async_playwright().start()

        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )

        # Create context with cookies
        self.context = await self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Set default timeout
        self.context.set_default_timeout(Config.TIMEOUT)

        logger.warning("Using legacy cookie-based authentication - may not persist reliably")
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
