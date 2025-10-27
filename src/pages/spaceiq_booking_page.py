"""
SpaceIQ Booking Page Object - Customized for your instance

Based on recorded workflow and screenshots.
This implements the actual booking flow for your SpaceIQ system.
"""

from .base_page import BasePage
from playwright.async_api import Page
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio
from src.api.booking_api import BookingAPI
from src.vision.desk_detector import DeskDetector


class SpaceIQBookingPage(BasePage):
    """
    Page Object for SpaceIQ booking interface.
    Customized for the floor map-based booking system.
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self.booking_api = BookingAPI(page)
        self.desk_detector = DeskDetector()

    async def check_and_wait_for_login(self, expected_path: str):
        """
        Check if user got logged out and wait for manual login.

        Args:
            expected_path: Expected URL path after login (e.g., "/finder/building/LC/floor/2")
        """
        current_url = self.page.url

        if "/login" in current_url:
            print("\n" + "=" * 70)
            print("         SESSION EXPIRED - PLEASE LOGIN")
            print("=" * 70)
            print(f"\nCurrent URL: {current_url}")
            print(f"Expected URL: https://main.spaceiq.com{expected_path}")
            print("\nPlease login in the browser window...")
            print("Bot will automatically continue after successful login.")
            print("=" * 70 + "\n")

            # Wait for URL to change to expected path (with timeout)
            # IMPORTANT: Must wait for URL to NOT contain "/login" anymore
            try:
                await self.page.wait_for_url(
                    lambda url: "/login" not in url and "/finder/building/" in url,
                    timeout=300000  # 5 minutes
                )
                print("\n[SUCCESS] Login detected! Continuing booking...\n")
                await asyncio.sleep(2)  # Wait for page to settle
            except Exception as e:
                print(f"\n[ERROR] Login timeout: {e}")
                raise

    async def navigate_to_floor_view(self, building: str = "LC", floor: str = "2"):
        """
        Navigate to the floor view for booking.

        Args:
            building: Building code (default: LC)
            floor: Floor number (default: 2)
        """
        # If SPACEIQ_URL already contains the full path, use it directly
        if "finder/building" in Config.SPACEIQ_URL:
            url = Config.SPACEIQ_URL
        else:
            url = f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/{building}/floor/{floor}"

        await self.navigate(url)

        # Check if redirected to login page
        await self.check_and_wait_for_login(f"/finder/building/{building}/floor/{floor}")

        # Verbose output suppressed - using pretty output in workflow
        # print(f"       Navigated to Building {building}, Floor {floor}")

    async def click_book_desk_button(self):
        """
        Click the 'Book Desk' button to start booking process.

        Based on screenshot 01: Teal/turquoise button with "Book Desk" text
        """
        # Try multiple selector strategies

        # Strategy 1: By text (most direct based on your recording)
        book_button = self.get_by_text('Book Desk', exact=True)

        # Alternative strategies if needed:
        # book_button = self.get_by_role('button', name='Book Desk')
        # book_button = self.locator('button:has-text("Book Desk")')

        await self.click_element(book_button, "Book Desk button")

        # Wait for date picker to appear
        await asyncio.sleep(0.5)

    async def open_date_picker(self):
        """
        Click on the date display to open the calendar picker.

        Based on screenshot 02: Date display showing date ranges like:
        - "Fri, Oct 24 - Fri, Oct 24, BST"
        - "Sun, Oct 26 - Sun, Oct 26, GMT"
        The element is: <div style="padding: 7px 10px; border-radius: 5px; background: white;
                              white-space: nowrap; cursor: pointer;">...</div>
        """
        # Strategy 1: Look for div with cursor pointer containing date range pattern (flexible timezone)
        # Matches: "Mon, Oct 26 - Mon, Oct 26, GMT|BST|PST|etc"
        date_display = self.page.locator('div[style*="cursor: pointer"]').filter(has_text=" - ")

        # Alternative strategies if needed:
        # Strategy 2: By style attributes (more specific)
        # date_display = self.locator('div[style*="border-radius: 5px"][style*="cursor: pointer"]')

        # Strategy 3: Look for Cancel button sibling (date picker is next to Cancel button)
        # date_display = self.page.locator('button:has-text("Cancel")').locator('xpath=preceding-sibling::div[1]')

        await self.click_element(date_display, "Date picker")

        # Wait for calendar to appear
        await asyncio.sleep(0.5)

    async def select_date_from_calendar(self, days_ahead: int = 1):
        """
        Select a date from the calendar picker.

        Args:
            days_ahead: Number of days from today (default: 1 for tomorrow)

        Based on recording: gridcell with aria-label containing the date

        Raises:
            Exception if date is disabled (grayed out / beyond booking window)
        """
        # Calculate target date
        target_date = datetime.now() + timedelta(days=days_ahead)

        # Format the aria-label (e.g., "Mon Nov 17 2025")
        day_str = target_date.strftime("%d")  # With leading zero (e.g., "06")
        month_str = target_date.strftime("%b")  # Mon, Tue, etc.
        year_str = target_date.strftime("%Y")
        weekday_str = target_date.strftime("%a")

        aria_label = f"{weekday_str} {month_str} {day_str} {year_str}"

        # Verbose output suppressed - using pretty output in workflow
        # print(f"       Looking for date: {aria_label}")

        # Find calendar cell by role and aria-label
        # IMPORTANT: Filter out disabled dates (aria-disabled="true")
        # Try exact match first
        date_cell = self.page.locator(
            f'div[role="gridcell"][aria-label="{aria_label}"][aria-disabled="false"]'
        )

        # Check if date exists but is disabled (grayed out)
        disabled_cell = self.page.locator(
            f'div[role="gridcell"][aria-label="{aria_label}"][aria-disabled="true"]'
        )
        if await disabled_cell.count() > 0:
            # print(f"       [WARNING] Date {aria_label} is disabled (beyond booking window)")
            raise Exception(f"Date {aria_label} is disabled/grayed out - beyond booking window")

        # Alternative: Partial match if exact doesn't work
        if await date_cell.count() == 0:
            # print(f"       Trying partial match...")
            date_cell = self.page.locator(
                f'div[role="gridcell"][aria-label*="{month_str} {day_str}"][aria-disabled="false"]'
            )

        # Fallback: Find by day number and class (exclude disabled)
        if await date_cell.count() == 0:
            # print(f"       Trying by day number: {day_str}")
            date_cell = self.page.locator(
                f'div.HotelingCalendar---day:has-text("{day_str}"):not(.HotelingCalendar---disabled)'
            )

        # Final check: if still 0, date is not available
        if await date_cell.count() == 0:
            raise Exception(f"Date {aria_label} not found or is disabled")

        await self.click_element(date_cell, f"Date: {month_str} {day_str}")

    async def click_update_button(self):
        """
        Click the 'Update' button to confirm date selection.

        Based on screenshot 03 and recording:
        - BUTTON element
        - Classes: SButton---base SButton---primary SButton---default
        - Text: "Update"
        - Type: submit
        """
        # Strategy 1: By text (simplest and most reliable)
        update_button = self.get_by_text('Update', exact=True)

        # Alternative strategies:
        # update_button = self.get_by_role('button', name='Update')
        # update_button = self.locator('button.SButton---primary:has-text("Update")')
        # update_button = self.locator('button[type="submit"]:has-text("Update")')

        await self.click_element(update_button, "Update button")

        # Wait for floor map to update with new date
        await asyncio.sleep(1)

    async def wait_for_floor_map_to_load(self):
        """
        Wait for the floor map image to be fully loaded.

        Based on recording: IMG with id="floorImage"
        """
        floor_map = self.locator('#floorImage')
        await self.wait_for_element(floor_map, 'visible', 'Floor map')

        # Additional wait for any overlays/circles to render
        await asyncio.sleep(1)
        # Verbose output suppressed - using pretty output in workflow
        # print("       Floor map loaded with availability circles")

    async def get_available_desks_from_sidebar(self, desk_prefix: str, logger=None) -> list:
        """
        Parse sidebar to find available desks.

        Args:
            desk_prefix: Desk prefix to filter (e.g., "2.24")
            logger: Optional logger

        Returns:
            List of available desk codes
        """
        import re
        import json
        from pathlib import Path

        # Get all booked desks from sidebar
        booked_desks = []
        sidebar_entries = self.page.locator('.BookingsAccordion---accordionTitle')
        entry_count = await sidebar_entries.count()

        msg = f"Found {entry_count} booking entries in sidebar"
        if logger:
            logger.info(msg)

        for i in range(entry_count):
            try:
                entry = sidebar_entries.nth(i)
                text = await entry.text_content()
                match = re.search(r'(\d+\.\d+\.\d+)', text)
                if match:
                    booked_desks.append(match.group(1))
            except:
                continue

        msg = f"Found {len(booked_desks)} booked desks"
        if logger:
            logger.info(msg)

        # Generate all possible desks for prefix
        all_possible_desks = [f"{desk_prefix}.{i:02d}" for i in range(1, 71)]

        # Load locked desks from config file
        config_path = Path(__file__).parent.parent.parent / "config" / "locked_desks.json"
        try:
            with open(config_path, 'r') as f:
                locked_config = json.load(f)
                permanent_desks = locked_config.get("locked_desks", {}).get(desk_prefix, [])
                msg = f"Loaded {len(permanent_desks)} locked desks from config"
                if logger:
                    logger.info(msg)
        except FileNotFoundError:
            # Verbose output suppressed - using empty list silently
            # print(f"       [WARNING] locked_desks.json not found, using empty list")
            permanent_desks = []
        except Exception as e:
            # Verbose output suppressed
            # print(f"       [WARNING] Error loading locked desks config: {e}")
            permanent_desks = []

        # Calculate available = all - booked - permanent
        available_desks = [
            desk for desk in all_possible_desks
            if desk not in booked_desks and desk not in permanent_desks
        ]

        msg = f"Found {len(available_desks)} available desks: {available_desks}"
        # Verbose output suppressed - using pretty output in workflow
        # print(f"       {msg}")
        if logger:
            logger.info(msg)

        return available_desks

    async def close_popup(self, logger=None):
        """
        Close the desk booking popup.

        Escape key doesn't work - need to click X button or outside popup.
        """
        try:
            # Look for close button (SVG with X icon)
            close_button = self.page.locator('svg[stroke="#A4AFB7"]').first
            if await close_button.count() > 0:
                await close_button.click()
                if logger:
                    logger.info(f"Closed popup by clicking X button")
            else:
                # Fallback: Click outside popup area (top-left corner)
                await self.page.mouse.click(50, 50)
                if logger:
                    logger.info(f"Closed popup by clicking outside (close button not found)")
        except Exception as close_error:
            # Fallback: Click outside popup area
            await self.page.mouse.click(50, 50)
            if logger:
                logger.warning(f"Failed to click close button, clicked outside instead: {close_error}")

        await asyncio.sleep(0.5)

    async def find_and_click_available_desks(self, available_desks: List[str], logger=None) -> Optional[str]:
        """
        Find available desks using CV and click them in priority order.

        Strategy:
        1. Detect blue circles using CV (fast)
        2. If position cache available:
           - Look up desk codes from circle positions (instant)
           - Click highest priority desk directly (fast)
        3. If no cache:
           - Click all circles to identify desks (slow)
           - Then click highest priority desk

        Args:
            available_desks: List of available desk codes in PRIORITY ORDER (e.g., ['2.24.20', '2.24.28'])
                            First desk in list = highest priority
            logger: Optional logger

        Returns:
            Desk code if successfully clicked and popup appeared, None otherwise
        """
        from config import Config
        from src.utils.desk_position_cache import get_cache
        import os
        import re

        # Log browser viewport size (affects text visibility)
        viewport_size = self.page.viewport_size
        if logger:
            logger.info(f"Browser viewport size: {viewport_size}")

        # Load position cache
        cache = get_cache()
        use_cache = cache.is_available() and cache.validate_viewport(viewport_size)

        if use_cache:
            # print(f"       ⚡ Using cached desk positions (fast mode)")
            if logger:
                cache_info = cache.get_cache_info()
                logger.info(f"Using position cache - {cache_info['total_desks']} desks cached from {cache_info['mapping_date']}")
        else:
            if cache.is_available():
                # print(f"       ⚠️  Cache viewport mismatch, using discovery mode")
                if logger:
                    logger.warning(f"Viewport mismatch: cache {cache.get_cache_info()['viewport']} vs current {viewport_size}")
            else:
                # print(f"       ℹ️  No position cache, using discovery mode (run map_desk_positions.py to build cache)")
                if logger:
                    logger.info("No position cache available - using click-all-circles discovery mode")

        # Get latest screenshot path
        screenshot_files = sorted(
            Config.SCREENSHOTS_DIR.glob("floor_map_loaded_*.png"),
            key=os.path.getmtime,
            reverse=True
        )

        if not screenshot_files:
            # print("       [FAILED] No floor map screenshot found")
            return None

        screenshot_path = str(screenshot_files[0])
        # print(f"       Analyzing screenshot: {screenshot_path}")
        if logger:
            logger.info(f"Using screenshot: {screenshot_path}")

        # Detect blue circles
        circles = self.desk_detector.find_blue_circles(screenshot_path, debug=True)

        if not circles:
            # print(f"       [FAILED] No blue circles detected")
            if logger:
                logger.error("CV Detection failed: No blue circles found in screenshot")
            return None

        # print(f"       Found {len(circles)} blue circles")
        if logger:
            logger.info(f"CV Detection - Found {len(circles)} blue circles at coordinates: {circles}")

        # PHASE 1: Discovery - Map all blue circles to desk codes
        desk_to_coords = {}  # {desk_code: (x, y)}

        # Fast path: Use cache if available
        if use_cache:
            # print(f"       PHASE 1: Looking up desk codes from cache... ⚡")
            desk_to_coords = cache.lookup_desks_from_circles(circles, tolerance=10)

            if logger:
                logger.info(f"Cache lookup - Identified {len(desk_to_coords)} desks: {list(desk_to_coords.keys())}")

            # print(f"       ✓ Identified {len(desk_to_coords)} desks instantly from cache")

            # Log any circles that weren't in cache
            if len(desk_to_coords) < len(circles):
                unknown_count = len(circles) - len(desk_to_coords)
                # print(f"       ℹ️  {unknown_count} circle(s) not in cache (may be new desks)")
                if logger:
                    logger.info(f"Found {unknown_count} circles not in cache - these may be newly added desks")

        # Slow path: Click all circles to identify desks
        else:
            # print(f"       PHASE 1: Identifying all blue circle desks...")

            for i, (x, y) in enumerate(circles, 1):
                try:
                    msg = f"Checking circle {i}/{len(circles)} at ({x}, {y})..."
                    print(f"       {msg}")
                    if logger:
                        logger.info(msg)

                    # Click the circle
                    await self.page.mouse.click(x, y)
                    await asyncio.sleep(1.5)

                    # Check if popup appeared - use the specific HTML element from the popup dialog
                    # Looking for: <td colspan="2">Hoteling Desk 2.24.40</td>
                    # IMPORTANT: Create a fresh locator AFTER clicking to avoid stale element references
                    popup = self.page.locator('td:has-text("Hoteling Desk")').first

                    # Wait for popup to be visible (with timeout)
                    try:
                        await popup.wait_for(state='visible', timeout=3000)
                    except Exception as popup_error:
                        msg = f"No popup appeared for circle at ({x}, {y})"
                        # print(f"       → {msg}")
                        if logger:
                            logger.warning(f"{msg}: {popup_error}")
                        continue

                    # Read popup text
                    try:
                        popup_text = await popup.text_content()
                    except Exception as text_error:
                        msg = f"Failed to read popup text for circle at ({x}, {y})"
                        # print(f"       → {msg}")
                        if logger:
                            logger.warning(f"{msg}: {text_error}")
                        continue

                    if popup_text:

                        if logger:
                            logger.info(f"Circle {i} popup text: '{popup_text}'")

                        # Extract desk code from popup (e.g., "Hoteling Desk 2.24.28")
                        match = re.search(r'(\d+\.\d+\.\d+)', popup_text)
                        if match:
                            desk_code = match.group(1)
                            # print(f"       → Identified: {desk_code}")

                            if logger:
                                logger.info(f"Extracted desk code '{desk_code}' from circle at ({x}, {y})")

                            # Store coordinates for this desk
                            desk_to_coords[desk_code] = (x, y)

                            # Close popup (Escape doesn't work, need to click X or outside)
                            await self.close_popup(logger=logger)

                            # Wait for popup to be hidden/detached from DOM
                            try:
                                await popup.wait_for(state='hidden', timeout=2000)
                            except:
                                pass  # Continue even if wait times out
                        else:
                            msg = f"Could not extract desk code from popup text: '{popup_text}'"
                            # print(f"       → {msg}")
                            if logger:
                                logger.warning(msg)

                            # Close popup (Escape doesn't work, need to click X or outside)
                            await self.close_popup(logger=logger)

                            # Wait for popup to be hidden/detached from DOM
                            try:
                                await popup.wait_for(state='hidden', timeout=2000)
                            except:
                                pass  # Continue even if wait times out

                except Exception as e:
                    msg = f"Error checking circle {i}: {e}"
                    # print(f"       {msg}")
                    if logger:
                        logger.error(msg)
                    continue

        # print(f"       Identified {len(desk_to_coords)} desks from blue circles")
        if logger:
            logger.info(f"CV Detection - Identified desks: {list(desk_to_coords.keys())}")

        # print(f"       PHASE 2: Booking highest priority available desk...")
        if logger:
            logger.info(f"PHASE 2 - Available desks (priority order): {available_desks}")
            logger.info(f"PHASE 2 - Detected desks (from CV): {list(desk_to_coords.keys())}")

        # PHASE 2: Booking - Iterate through available_desks in PRIORITY ORDER
        for desk_code in available_desks:
            if desk_code in desk_to_coords:
                x, y = desk_to_coords[desk_code]
                priority_pos = available_desks.index(desk_code) + 1
                msg = f"Found highest priority desk: {desk_code} (Priority position: {priority_pos}/{len(available_desks)})"
                # print(f"       [PRIORITY] {msg}")
                if logger:
                    logger.info(f"PRIORITY MATCH - Desk: {desk_code}, Priority Position: {priority_pos}, Coordinates: ({x}, {y})")
                    logger.info(f"This is the FIRST match in priority order - booking this desk")

                # Click this desk to book it
                # print(f"       Clicking to book {desk_code} at ({x}, {y})...")
                await self.page.mouse.click(x, y)
                await asyncio.sleep(1.5)

                # Verify popup appeared
                popup = self.page.locator('text=/Hoteling Desk/')
                if await popup.count() > 0:
                    popup_text = await popup.first.text_content()
                    if desk_code in popup_text:
                        msg = f"Successfully selected highest priority desk {desk_code}!"
                        # print(f"       [SUCCESS] {msg}")
                        if logger:
                            logger.info(msg)
                        return desk_code
                    else:
                        # print(f"       [WARNING] Popup shows different desk, trying next priority...")
                        if logger:
                            logger.warning(f"Popup shows different desk (expected {desk_code}), closing and trying next")
                        await self.close_popup(logger=logger)
                        continue
            else:
                # Log when we skip a desk because CV didn't detect it
                priority_pos = available_desks.index(desk_code) + 1
                if logger:
                    logger.info(f"Skipping desk {desk_code} (Priority position: {priority_pos}) - CV did not detect this desk")
                continue

        # print(f"       [FAILED] None of the blue circles matched available desks")
        # print(f"       Available: {available_desks}")
        # print(f"       Detected: {list(desk_to_coords.keys())}")
        if logger:
            logger.error(f"NO MATCH - Available desks (priority order): {available_desks}")
            logger.error(f"NO MATCH - Detected blue circles: {list(desk_to_coords.keys())}")
            logger.error(f"NO MATCH - No overlap between available and detected desks!")
        return None

    async def book_desk_via_api(self, desk_code: str, date_str: str, logger=None) -> bool:
        """
        Book a desk directly via GraphQL API (bypasses UI clicking).

        Args:
            desk_code: Desk code like "2.24.28"
            date_str: Date in YYYY-MM-DD format
            logger: Optional logger

        Returns:
            True if successful, False otherwise
        """
        from config import Config

        msg = f"Booking desk {desk_code} via API..."
        print(f"       {msg}")
        if logger:
            logger.info(msg)

        try:
            success = await self.booking_api.book_desk_by_code(
                desk_code=desk_code,
                employee_id=Config.EMPLOYEE_ID,
                date=date_str
            )
            return success
        except Exception as e:
            msg = f"API booking failed: {e}"
            print(f"       [FAILED] {msg}")
            if logger:
                logger.error(msg)
            return False

    async def click_available_desk_on_map(self, desk_preference: Optional[str] = None, desk_prefix: Optional[str] = None, logger=None):
        """
        Click on an available (blue circle) desk on the floor map.

        Based on screenshot 04:
        - Blue circles = available desks
        - Grey circles = occupied desks
        - Desks have labels like "2.24.30", "2.24.22", etc.

        Args:
            desk_preference: Optional specific desk ID (e.g., "2.24.30")
            desk_prefix: Optional prefix filter (e.g., "2.24" to only book desks starting with 2.24)
            logger: Optional logger for detailed logging

        Note: This is challenging because the circles are part of an image/SVG overlay.
        We'll need to use coordinates or canvas interaction (Phase 2).
        """
        if logger:
            logger.info("Selecting available desk...")
        print("       Selecting available desk...")

        if desk_prefix:
            msg = f"Filtering by prefix: {desk_prefix}.*"
            print(f"   {msg}")
            if logger:
                logger.info(msg)

        # Strategy 1: Try specific desk preference first
        if desk_preference:
            msg = f"Looking for specific desk: {desk_preference}"
            print(f"   {msg}")
            if logger:
                logger.info(msg)

            desk_label = self.page.locator(f'text={desk_preference}')
            if await desk_label.count() > 0:
                await self.click_element(desk_label, f"Desk {desk_preference}")
                return True

        # Strategy 2: Use sidebar to determine which desks are available
        # NOTE: Blue circles are hard to locate in DOM (might be canvas-based).
        # Instead, parse the sidebar to find booked desks, then calculate available ones.
        msg = "📋 Parsing sidebar to find booked desks..."
        print(f"   {msg}")
        if logger:
            logger.info(msg)

        # Get all booked desks from sidebar
        import re
        booked_desks = []

        # Find all desk entries in sidebar (e.g., "Hoteling Desk: LC-2-2.24.28")
        sidebar_entries = self.page.locator('.BookingsAccordion---accordionTitle')
        entry_count = await sidebar_entries.count()

        msg = f"Found {entry_count} booking entries in sidebar"
        if logger:
            logger.info(msg)

        for i in range(entry_count):
            try:
                entry = sidebar_entries.nth(i)
                text = await entry.text_content()

                # Extract desk ID (e.g., "2.24.28")
                match = re.search(r'(\d+\.\d+\.\d+)', text)
                if match:
                    desk_id = match.group(1)
                    booked_desks.append(desk_id)
            except:
                continue

        msg = f"Found {len(booked_desks)} booked desks"
        if logger:
            logger.info(msg)

        # Define all bookable desks for the prefix
        if desk_prefix:
            # Generate all possible desk numbers for prefix (e.g., 2.24.01 to 2.24.70)
            all_possible_desks = []
            for i in range(1, 71):  # 2.24.01 to 2.24.70
                desk_num = f"{desk_prefix}.{i:02d}"
                all_possible_desks.append(desk_num)

            # Permanent desks that are NOT bookable
            permanent_desks = [
                "2.24.01", "2.24.13", "2.24.18", "2.24.19", "2.24.42", "2.24.45",
                "2.24.47", "2.24.48", "2.24.50", "2.24.51", "2.24.52",
                "2.24.53", "2.24.55", "2.24.56", "2.24.60", "2.24.65",
                "2.24.67", "2.24.68", "2.24.69", "2.24.70"
            ]

            # Calculate available desks = All desks - Booked desks - Permanent desks
            available_desks = [
                desk for desk in all_possible_desks
                if desk not in booked_desks and desk not in permanent_desks
            ]

            msg = f"Calculated {len(available_desks)} available desks: {available_desks}"
            print(f"   {msg}")
            if logger:
                logger.info(msg)

            if len(available_desks) == 0:
                msg = f"❌ No available desks found for prefix {desk_prefix}"
                print(f"   {msg}")
                if logger:
                    logger.warning(msg)
                await self.capture_screenshot("no_available_desks")
                return False

            # Desk coordinates on the floor map (obtained from HAR file)
            # Key: desk code (e.g., "2.24.28"), Value: (x, y) coordinates
            desk_coordinates = {
                "2.24.28": (2807, 742),
                "2.24.20": (2807, 742),  # TODO: Get actual coordinates for other desks
                # Add more as needed
            }

            # Try clicking each available desk using multiple strategies
            for desk_id in available_desks:
                try:
                    msg = f"Trying to book desk {desk_id}..."
                    print(f"   {msg}")
                    if logger:
                        logger.info(msg)

                    # Strategy A: Try clicking at known coordinates (most reliable)
                    if desk_id in desk_coordinates:
                        x, y = desk_coordinates[desk_id]
                        msg = f"Clicking at coordinates ({x}, {y}) for desk {desk_id}..."
                        print(f"       {msg}")
                        if logger:
                            logger.info(msg)

                        try:
                            await self.page.mouse.click(x, y)
                            await asyncio.sleep(2)

                            # Check if popup appeared
                            popup = self.page.locator('text=/Hoteling Desk/')
                            if await popup.count() > 0:
                                popup_text = await popup.first.text_content()
                                if desk_id in popup_text:
                                    msg = f"Successfully clicked desk {desk_id} via coordinates!"
                                    # print(f"       [SUCCESS] {msg}")
                                    if logger:
                                        logger.info(msg)
                                    await self.capture_screenshot(f"desk_{desk_id}_popup")
                                    return True
                                else:
                                    # Wrong desk, close and continue
                                    if logger:
                                        logger.warning(f"Clicked wrong desk at ({x}, {y}), expected {desk_id}")
                                    await self.close_popup(logger=logger)
                        except Exception as e:
                            msg = f"Could not click at coordinates: {e}"
                            if logger:
                                logger.debug(msg)

                    # Strategy B: Try finding SVG text elements (desk labels are likely SVG)
                    svg_text = self.page.locator(f'svg text:has-text("{desk_id}")')
                    svg_count = await svg_text.count()

                    if svg_count > 0:
                        msg = f"Found SVG text for desk {desk_id}, trying to click nearby button..."
                        print(f"   {msg}")
                        if logger:
                            logger.info(msg)

                        # Get the position of the SVG text
                        try:
                            box = await svg_text.first.bounding_box()
                            if box:
                                # Click slightly to the left of the text (where the blue circle usually is)
                                x = box['x'] - 15
                                y = box['y'] + (box['height'] / 2)

                                await self.page.mouse.click(x, y)
                                await asyncio.sleep(1.5)

                                # Check if popup appeared
                                popup = self.page.locator('text=/Hoteling Desk/')
                                if await popup.count() > 0:
                                    popup_text = await popup.first.text_content()
                                    if desk_id in popup_text:
                                        msg = f"[SUCCESS] Successfully clicked desk {desk_id} via SVG coordinates!"
                                        print(f"   {msg}")
                                        if logger:
                                            logger.info(msg)
                                        await self.capture_screenshot(f"desk_{desk_id}_popup")
                                        return True
                                    else:
                                        # Wrong desk, close and continue
                                        if logger:
                                            logger.warning(f"Clicked wrong desk, expected {desk_id}")
                                        await self.close_popup(logger=logger)
                        except Exception as e:
                            msg = f"Could not click via SVG coordinates: {e}"
                            if logger:
                                logger.debug(msg)

                    # Strategy B: Try finding HTML text elements
                    desk_label = self.page.get_by_text(desk_id, exact=True)
                    label_count = await desk_label.count()

                    if label_count > 0:
                        msg = f"Found HTML label for desk {desk_id}, clicking..."
                        print(f"   {msg}")
                        if logger:
                            logger.info(msg)

                        try:
                            await desk_label.first.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await desk_label.first.click()
                            await asyncio.sleep(1.5)

                            popup = self.page.locator('text=/Hoteling Desk/')
                            if await popup.count() > 0:
                                popup_text = await popup.first.text_content()
                                if desk_id in popup_text:
                                    msg = f"[SUCCESS] Successfully clicked desk {desk_id} via HTML label!"
                                    print(f"   {msg}")
                                    if logger:
                                        logger.info(msg)
                                    await self.capture_screenshot(f"desk_{desk_id}_popup")
                                    return True
                                else:
                                    if logger:
                                        logger.warning(f"Clicked wrong desk, expected {desk_id}")
                                    await self.close_popup(logger=logger)
                        except Exception as e:
                            msg = f"Could not click HTML label: {e}"
                            if logger:
                                logger.debug(msg)

                    # Strategy C: Smarter button iteration with visibility checks
                    msg = f"Trying button approach for desk {desk_id}..."
                    if logger:
                        logger.debug(msg)

                    all_buttons = self.page.locator('[role="button"]')
                    button_count = await all_buttons.count()

                    # Try only visible, enabled buttons
                    for i in range(button_count):
                        try:
                            button = all_buttons.nth(i)

                            # Check if button is visible before trying to click
                            if not await button.is_visible():
                                continue

                            # Try to click with shorter timeout
                            try:
                                await button.click(timeout=1500, force=True)
                                await asyncio.sleep(1)

                                # Check if popup appeared
                                popup = self.page.locator('text=/Hoteling Desk/')
                                if await popup.count() > 0:
                                    popup_text = await popup.first.text_content()

                                    if desk_id in popup_text:
                                        msg = f"[SUCCESS] Found desk {desk_id} via button {i}!"
                                        print(f"   {msg}")
                                        if logger:
                                            logger.info(msg)
                                        await self.capture_screenshot(f"desk_{desk_id}_popup")
                                        return True
                                    else:
                                        # Wrong desk, close and continue
                                        if logger:
                                            logger.warning(f"Clicked wrong desk, expected {desk_id}")
                                        await self.close_popup(logger=logger)
                            except:
                                # Click failed, skip this button
                                continue

                        except Exception as e:
                            # Button processing failed, continue
                            continue

                    msg = f"⚠️  Could not click desk {desk_id} using any strategy, trying next desk..."
                    if logger:
                        logger.debug(msg)

                except Exception as e:
                    msg = f"Error while trying desk {desk_id}: {e}"
                    print(f"       [WARNING] {msg}")
                    if logger:
                        logger.error(msg)
                    continue

            # If we get here, couldn't click any available desk
            msg = f"Could not successfully click any of the {len(available_desks)} available desks (labels may not be visible)"
            print(f"       [FAILED] {msg}")
            if logger:
                logger.warning(msg)
            await self.capture_screenshot("no_desks_clicked")
            return False

    async def _check_if_desk_available(self, desk_element) -> bool:
        """
        Try to detect if a desk is available (blue) or occupied (grey).

        This checks for blue color indicators near the desk label.

        Args:
            desk_element: The desk label element

        Returns:
            True if appears available (blue), False if occupied (grey) or unknown
        """
        try:
            # Get the bounding box of the desk label
            box = await desk_element.bounding_box()
            if not box:
                return False  # Can't determine, assume occupied

            # Look for SVG circles near this desk label
            # Blue circles indicate available, grey/other colors indicate occupied
            x, y = box['x'], box['y']

            # Search for circles within ~50px of the desk label
            circles = self.page.locator('circle')
            circle_count = await circles.count()

            for i in range(circle_count):
                circle = circles.nth(i)
                circle_box = await circle.bounding_box()

                if circle_box:
                    # Check if circle is near the desk label
                    distance_x = abs(circle_box['x'] - x)
                    distance_y = abs(circle_box['y'] - y)

                    if distance_x < 50 and distance_y < 50:
                        # Circle is near this desk, check its color
                        fill = await circle.get_attribute('fill')
                        stroke = await circle.get_attribute('stroke')

                        # Check for blue color indicators
                        if fill and ('blue' in fill.lower() or '#' in fill):
                            # Try to detect if it's a blue shade
                            if 'blue' in fill.lower() or fill.startswith('#') and self._is_blue_color(fill):
                                return True

                        if stroke and ('blue' in stroke.lower() or '#' in stroke):
                            if 'blue' in stroke.lower() or stroke.startswith('#') and self._is_blue_color(stroke):
                                return True

            return False  # No blue circle found, assume occupied

        except Exception as e:
            # If we can't determine, assume occupied (safer)
            return False

    def _is_blue_color(self, color_hex: str) -> bool:
        """
        Check if a hex color is blue-ish.

        Args:
            color_hex: Color in hex format (e.g., "#4A90E2")

        Returns:
            True if blue-ish, False otherwise
        """
        try:
            if not color_hex.startswith('#'):
                return False

            # Remove # and convert to RGB
            hex_color = color_hex.lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)

                # Blue-ish if blue component is dominant
                return b > r and b > g and b > 100

            return False
        except:
            return False

    async def verify_desk_popup_appeared(self) -> bool:
        """
        Verify that the desk information popup appeared.

        Based on screenshot 05: Modal showing "Hoteling Desk 2.24.17" with details
        """
        # Look for the popup title (starts with "Hoteling Desk")
        popup_title = self.page.locator('text=/Hoteling Desk/')

        try:
            await self.wait_for_element(popup_title, 'visible', 'Desk info popup')
            return True
        except:
            return False

    async def click_book_now_in_popup(self):
        """
        Click the 'BOOK NOW' button in the desk information popup.

        Based on screenshot 05 and recording:
        - BUTTON element
        - Classes: SButton---base SButton---primary SButton---small
        - Text: "BOOK NOW" or "Book Now"
        - Type: submit
        """
        # Strategy 1: By text (case-insensitive)
        book_button = self.page.locator('button:has-text("Book Now")')

        # Alternative strategies:
        # book_button = self.get_by_role('button', name='Book Now')
        # book_button = self.locator('button.SButton---primary.SButton---small')

        await self.click_element(book_button, "Book Now button (in popup)")

        # Wait for booking confirmation
        await asyncio.sleep(1)

    async def verify_booking_success(self) -> bool:
        """
        Verify that the booking was successful.

        Look for success indicators like:
        - Success message/notification
        - The circle on the map turning grey
        - A confirmation popup
        """
        # Strategy 1: Look for success message
        success_indicators = [
            'text=/booking.*success/i',
            'text=/success/i',
            'text=/confirmed/i',
            'text=/booked/i',
        ]

        for indicator in success_indicators:
            element = self.page.locator(indicator)
            if await element.count() > 0:
                await self.wait_for_element(element, 'visible', 'Success message')
                success_text = await element.text_content()
                # print(f"       [SUCCESS] {success_text}")
                return True

        # Strategy 2: Check if popup closed (might indicate success)
        popup_title = self.page.locator('text=/Hoteling Desk/')
        try:
            await popup_title.wait_for(state='hidden', timeout=5000)
            # print("       [SUCCESS] Popup closed (likely successful)")
            return True
        except:
            pass

        # If we can't confirm, take a screenshot for manual verification
        await self.capture_screenshot("booking_result")
        print("       [WARNING] Could not verify booking success - screenshot saved")
        return False

    # ========================================================================
    # Helper method: Get desk information from popup
    # ========================================================================

    async def get_desk_info_from_popup(self) -> dict:
        """
        Extract desk information from the popup.

        Returns:
            Dictionary with desk details (name, department, etc.)
        """
        info = {}

        # Desk name (e.g., "Hoteling Desk 2.24.17")
        title = self.page.locator('text=/Hoteling Desk/')
        if await title.count() > 0:
            info['desk_name'] = await title.text_content()

        # Department
        dept = self.page.locator('text=/Department:/')
        if await dept.count() > 0:
            info['department'] = await dept.text_content()

        return info

    async def get_existing_bookings(self, logger=None) -> List[str]:
        """
        Fetch existing bookings from 'My Bookings' modal.

        Returns:
            List of dates (YYYY-MM-DD format) that are already booked
        """
        existing_bookings = []

        try:
            # Click on the user menu (Felipe Vargas)
            # print("       Fetching existing bookings...")
            user_menu = self.page.locator('.Navbar---menuToggle')
            await user_menu.click()
            await asyncio.sleep(0.5)

            # Click on "My Bookings"
            my_bookings_btn = self.page.locator('#my_bookings_button')
            await my_bookings_btn.click()
            await asyncio.sleep(1)

            # Wait for modal to appear
            modal = self.page.locator('.modal-content')
            await modal.wait_for(state='visible', timeout=5000)

            # Parse ONLY the "Upcoming Bookings" tab (the active one)
            # Both tabs exist in DOM, but only one is active (has "active in" classes)
            # Select only rows from the active tab pane
            upcoming_pane = self.page.locator('#bookings-pane-upcoming\\ bookings')
            rows = upcoming_pane.locator('.UITable---row')  # This selector already excludes header
            row_count = await rows.count()

            # No need to skip header - .UITable---row excludes .UITable---headerRow
            # print(f"       DEBUG: Found {row_count} data rows in Upcoming Bookings table")
            for i in range(0, row_count):  # Start at 0, not 1!
                try:
                    # Get the first cell which contains the date
                    date_cell = rows.nth(i).locator('.UITable---cell').first
                    date_text = await date_cell.text_content()

                    # Parse date like "Oct 29, 2025" to "2025-10-29"
                    # Remove extra whitespace
                    date_text = date_text.strip()
                    # print(f"       DEBUG: Row {i} date text: '{date_text}'")

                    # Convert to YYYY-MM-DD format
                    from datetime import datetime
                    try:
                        parsed_date = datetime.strptime(date_text, '%b %d, %Y')
                        date_str = parsed_date.strftime('%Y-%m-%d')

                        # Only add if not already in list (avoid duplicates)
                        if date_str not in existing_bookings:
                            existing_bookings.append(date_str)
                            # print(f"       DEBUG: Found existing booking: {date_str}")
                            if logger:
                                logger.info(f"Existing booking found: {date_str}")
                    except ValueError as ve:
                        # Skip if date parsing fails
                        # print(f"       DEBUG: Could not parse date '{date_text}': {ve}")
                        if logger:
                            logger.warning(f"Could not parse date: {date_text}")
                        continue

                except Exception as e:
                    if logger:
                        logger.warning(f"Error parsing booking row {i}: {e}")
                    continue

            # Close the modal - use more specific selector in the modal footer
            close_btn = self.page.locator('.modal-footer button:has-text("Close")')
            await close_btn.click(timeout=3000)
            await asyncio.sleep(0.5)

            # print(f"       Found {len(existing_bookings)} existing booking(s)")
            if logger:
                logger.info(f"Total existing bookings: {len(existing_bookings)} - {existing_bookings}")

        except Exception as e:
            msg = f"Error fetching existing bookings: {e}"
            # print(f"       [WARNING] {msg}")
            if logger:
                logger.warning(msg)

            # Try to close any open modals
            try:
                close_btn = self.page.locator('.modal-footer button:has-text("Close")')
                if await close_btn.count() > 0:
                    await close_btn.click(timeout=3000)
                    await asyncio.sleep(0.5)
            except:
                # If close button fails, try pressing Escape key
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                except:
                    pass

        return existing_bookings


# Import Config for URL construction
from config import Config
