"""
Base Page Object class implementing core automation patterns.

Following Phase 1 best practices:
- Resilient selector hierarchy (Role > TestId > Text > CSS)
- Auto-waiting (no manual sleeps)
- Proper error handling
- Screenshot capture on failure
"""

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
from pathlib import Path
from datetime import datetime
from config import Config
from typing import Optional


class BasePage:
    """
    Base class for all Page Objects.

    Encapsulates common patterns and enforces best practices:
    - Prioritizes user-facing selectors
    - Provides helper methods for common interactions
    - Handles screenshots and debugging
    """

    def __init__(self, page: Page):
        self.page = page

    async def navigate(self, url: str = None):
        """
        Navigate to a specific URL or the base SpaceIQ URL.

        Args:
            url: Full URL to navigate to. If None, uses Config.SPACEIQ_URL
        """
        target_url = url or Config.SPACEIQ_URL
        # Verbose output suppressed - using pretty output in workflow
        # print(f"       Navigating to: {target_url}")
        await self.page.goto(target_url, wait_until="domcontentloaded")
        # print(f"       Page loaded")

    # ============================================================================
    # TIER 1: User-Facing Selectors (Preferred)
    # ============================================================================

    def get_by_role(
        self, role: str, name: Optional[str] = None, exact: bool = False
    ) -> Locator:
        """
        Locate element by ARIA role and optional accessible name.
        This is the MOST resilient selector strategy.

        Args:
            role: ARIA role (e.g., 'button', 'textbox', 'heading', 'link')
            name: Accessible name (visible text or aria-label)
            exact: Whether to match name exactly

        Example:
            button = page.get_by_role('button', name='Book Now')
            await button.click()
        """
        options = {}
        if name:
            options['name'] = name
            options['exact'] = exact

        return self.page.get_by_role(role, **options)

    def get_by_label(self, text: str, exact: bool = False) -> Locator:
        """
        Locate input by associated label text.
        Good for form fields with proper label associations.

        Args:
            text: Label text
            exact: Whether to match exactly
        """
        return self.page.get_by_label(text, exact=exact)

    def get_by_placeholder(self, text: str, exact: bool = False) -> Locator:
        """
        Locate input by placeholder attribute.

        Args:
            text: Placeholder text
            exact: Whether to match exactly
        """
        return self.page.get_by_placeholder(text, exact=exact)

    # ============================================================================
    # TIER 2: Testing Hooks (Fallback for unique identification)
    # ============================================================================

    def get_by_test_id(self, test_id: str) -> Locator:
        """
        Locate element by data-testid attribute.
        Use when user-facing selectors are not stable enough.

        Args:
            test_id: Value of data-testid attribute

        Example:
            element = page.get_by_test_id('submit-booking-btn')
        """
        return self.page.get_by_test_id(test_id)

    # ============================================================================
    # TIER 3: Content-Based (Use with caution)
    # ============================================================================

    def get_by_text(self, text: str, exact: bool = False) -> Locator:
        """
        Locate element containing specific text.
        Less stable due to localization and content changes.

        Args:
            text: Text content to search for
            exact: Whether to match exactly
        """
        return self.page.get_by_text(text, exact=exact)

    # ============================================================================
    # TIER 4: CSS/XPath (Last Resort Only)
    # ============================================================================

    def locator(self, selector: str) -> Locator:
        """
        Locate element by CSS selector or XPath.
        ⚠️ USE ONLY AS LAST RESORT - These are brittle selectors.

        Args:
            selector: CSS selector or XPath string

        Note:
            If you find yourself using this frequently, consider:
            1. Requesting data-testid attributes in the UI
            2. Using more stable user-facing selectors
        """
        return self.page.locator(selector)

    # ============================================================================
    # Common Interactions (Leverage Playwright's auto-waiting)
    # ============================================================================

    async def click_element(self, locator: Locator, description: str = "element"):
        """
        Click an element with auto-waiting and error handling.

        Args:
            locator: Playwright locator for the element
            description: Human-readable description for logging
        """
        try:
            # Verbose output suppressed - using pretty output in workflow
            # print(f"       Clicking {description}...")
            await locator.click()
            # print(f"       Clicked {description}")
        except PlaywrightTimeoutError:
            await self.capture_screenshot(f"click_failed_{description}")
            raise Exception(f"Failed to click {description} - element not found or not clickable")

    async def fill_input(self, locator: Locator, value: str, description: str = "field"):
        """
        Fill an input field with auto-waiting.

        Args:
            locator: Playwright locator for the input
            value: Text to enter
            description: Human-readable description for logging
        """
        try:
            # Verbose output suppressed - using pretty output in workflow
            # print(f"       Filling {description} with: {value}")
            await locator.fill(value)
            # print(f"       Filled {description}")
        except PlaywrightTimeoutError:
            await self.capture_screenshot(f"fill_failed_{description}")
            raise Exception(f"Failed to fill {description} - element not found or not editable")

    async def select_dropdown(self, locator: Locator, value: str, description: str = "dropdown"):
        """
        Select option from dropdown.

        Args:
            locator: Playwright locator for the select element
            value: Option value or label to select
            description: Human-readable description for logging
        """
        try:
            # Verbose output suppressed - using pretty output in workflow
            # print(f"       Selecting '{value}' from {description}...")
            await locator.select_option(value)
            # print(f"       Selected option")
        except PlaywrightTimeoutError:
            await self.capture_screenshot(f"select_failed_{description}")
            raise Exception(f"Failed to select from {description} - element not found")

    async def wait_for_element(self, locator: Locator, state: str = "visible", description: str = "element"):
        """
        Explicitly wait for an element to reach a specific state.

        Args:
            locator: Playwright locator for the element
            state: State to wait for ('visible', 'hidden', 'attached', 'detached')
            description: Human-readable description for logging
        """
        try:
            # Verbose output suppressed - using pretty output in workflow
            # print(f"       Waiting for {description} to be {state}...")
            await locator.wait_for(state=state)
            # print(f"       {description} is {state}")
        except PlaywrightTimeoutError:
            await self.capture_screenshot(f"wait_failed_{description}")
            raise Exception(f"Timeout waiting for {description} to be {state}")

    async def get_text(self, locator: Locator) -> str:
        """
        Get text content of an element.

        Args:
            locator: Playwright locator for the element

        Returns:
            Text content of the element
        """
        return await locator.text_content()

    async def is_visible(self, locator: Locator) -> bool:
        """
        Check if element is visible.

        Args:
            locator: Playwright locator for the element

        Returns:
            True if visible, False otherwise
        """
        try:
            return await locator.is_visible()
        except:
            return False

    # ============================================================================
    # Debugging and Error Handling
    # ============================================================================

    async def capture_screenshot(self, name: str = "screenshot"):
        """
        Capture screenshot for debugging.

        Args:
            name: Base name for the screenshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = Config.SCREENSHOTS_DIR / filename

        await self.page.screenshot(path=str(filepath), full_page=True)
        # Verbose output suppressed - screenshot saved silently for debugging
        # print(f"   📸 Screenshot saved: {filepath}")

    async def get_page_title(self) -> str:
        """Get current page title"""
        return await self.page.title()

    async def get_current_url(self) -> str:
        """Get current page URL"""
        return self.page.url

    async def wait_for_navigation(self):
        """Wait for page navigation to complete"""
        await self.page.wait_for_load_state("domcontentloaded")
