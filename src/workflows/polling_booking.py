"""
Polling Booking Workflow

For a single date, keeps trying to book a desk with periodic refreshes.
Useful when desks are often occupied and you want to catch one as soon as it becomes available.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from src.utils.file_logger import setup_file_logger


class PollingBookingWorkflow:
    """
    Keeps trying to book a desk for a specific date with periodic refreshes.

    Strategy:
    1. Try all desks matching prefix
    2. If none available, wait and refresh
    3. Try again
    4. Repeat until success or max attempts
    """

    def __init__(
        self,
        building: str = "LC",
        floor: str = "2",
        date_str: Optional[str] = None,
        desk_prefix: str = "2.24",
        refresh_interval: int = 30,  # seconds
        max_attempts: int = 20
    ):
        self.building = building
        self.floor = floor
        self.date_str = date_str
        self.desk_prefix = desk_prefix
        self.refresh_interval = refresh_interval
        self.max_attempts = max_attempts
        self.session_manager = SessionManager()

        # Setup file logging
        self.logger, self.log_file = setup_file_logger()
        self.logger.info("=" * 70)
        self.logger.info("Polling Booking Workflow Initialized")
        self.logger.info("=" * 70)

    async def run(self) -> bool:
        """
        Execute polling booking workflow.

        Returns:
            True if booking successful, False if max attempts reached
        """

        # Parse date
        if self.date_str:
            target_date = datetime.strptime(self.date_str, '%Y-%m-%d')
        else:
            target_date = datetime.now() + timedelta(days=1)  # Tomorrow
            self.date_str = target_date.strftime('%Y-%m-%d')

        days_ahead = (target_date.date() - datetime.now().date()).days

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("Polling Booking Workflow")
        self.logger.info("=" * 70)
        self.logger.info(f"Building: {self.building}, Floor: {self.floor}")
        self.logger.info(f"Target Date: {self.date_str}")
        self.logger.info(f"Desk Prefix: {self.desk_prefix}.*")
        self.logger.info(f"Refresh Interval: {self.refresh_interval}s")
        self.logger.info(f"Max Attempts: {self.max_attempts}")
        self.logger.info(f"Log File: {self.log_file}")
        self.logger.info("=" * 70)
        self.logger.info("")

        try:
            # Initialize session
            context = await self.session_manager.initialize()
            page = await context.new_page()
            booking_page = SpaceIQBookingPage(page)

            # Keep trying with refreshes
            for attempt in range(1, self.max_attempts + 1):
                print("\n" + "-" * 70)
                print(f"Attempt {attempt}/{self.max_attempts}")
                print("-" * 70 + "\n")

                # Try booking
                success = await self._try_booking(
                    booking_page=booking_page,
                    days_ahead=days_ahead
                )

                if success:
                    print("\n" + "=" * 70)
                    print("[SUCCESS] BOOKING SUCCESSFUL!")
                    print("=" * 70)
                    print(f"Date: {self.date_str}")
                    print(f"Attempt: {attempt}/{self.max_attempts}")
                    print("=" * 70 + "\n")

                    return True

                # No desk available
                if attempt < self.max_attempts:
                    print(f"\n[INFO] No desk available. Waiting {self.refresh_interval}s before refresh...")
                    print(f"        Next attempt: {attempt + 1}/{self.max_attempts}")

                    await asyncio.sleep(self.refresh_interval)

                    print("\n[INFO] Refreshing page...")
                    await page.reload()
                    await asyncio.sleep(2)  # Wait for page to load

            # Max attempts reached
            print("\n" + "=" * 70)
            print("[FAILED] MAX ATTEMPTS REACHED")
            print("=" * 70)
            print(f"Tried {self.max_attempts} times over {self.max_attempts * self.refresh_interval // 60} minutes")
            print(f"No {self.desk_prefix}.* desks available for {self.date_str}")
            print("=" * 70 + "\n")

            return False

        except Exception as e:
            print(f"\n[ERROR] Error during polling booking: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await self.session_manager.close()

    async def _try_booking(
        self,
        booking_page: SpaceIQBookingPage,
        days_ahead: int
    ) -> bool:
        """
        Single booking attempt.

        Returns:
            True if successful, False if no desk available
        """
        try:
            # Step 1: Navigate
            print("[1/9] Navigating to floor view...")
            await booking_page.navigate_to_floor_view(self.building, self.floor)

            # Step 2: Click Book Desk
            print("[2/9] Clicking 'Book Desk'...")
            await booking_page.click_book_desk_button()

            # Step 3: Open date picker
            print("[3/9] Opening date picker...")
            await booking_page.open_date_picker()

            # Step 4: Select date
            print(f"[4/9] Selecting date ({self.date_str})...")
            await booking_page.select_date_from_calendar(days_ahead=days_ahead)

            # Step 5: Click Update
            self.logger.info("Step 5: Clicking 'Update'...")
            print("[5/9] Clicking 'Update'...")
            await booking_page.click_update_button()

            # Step 6: Wait for floor map
            self.logger.info("Step 6: Waiting for floor map...")
            print("[6/9] Waiting for floor map...")
            await booking_page.wait_for_floor_map_to_load()

            # IMPORTANT: Wait longer for floor map to fully load with all desk labels and availability dots
            # SVG text elements and blue circles need time to render
            self.logger.info("Waiting 7 seconds for SVG elements (desk labels) to fully render...")
            await asyncio.sleep(7)

            # Verify SVG text elements are present
            svg_texts = booking_page.page.locator('svg text')
            svg_count = await svg_texts.count()
            self.logger.info(f"Found {svg_count} SVG text elements on floor map")
            print(f"      Found {svg_count} SVG text elements")

            # Step 7: Get available desks from sidebar
            self.logger.info(f"Step 7: Finding available {self.desk_prefix}.* desks...")
            print(f"[7/9] Finding available {self.desk_prefix}.* desks...")

            available_desks = await booking_page.get_available_desks_from_sidebar(
                desk_prefix=self.desk_prefix,
                logger=self.logger
            )

            if not available_desks:
                print(f"[FAILED] No available desks found")
                return False

            # Step 8: Use CV to find and click blue circles
            self.logger.info(f"Step 8: Using CV to find blue circles...")
            print(f"[8/9] Using computer vision to detect and click available desks...")

            found_desk = await booking_page.find_and_click_available_desks(
                available_desks=available_desks,
                logger=self.logger
            )

            if not found_desk:
                print(f"[FAILED] Could not click any available desks")
                return False

            # Verify popup appeared
            if not await booking_page.verify_desk_popup_appeared():
                print("[FAILED] Desk popup did not appear")
                return False

            print(f"[INFO] Successfully clicked desk {found_desk}")

            # Step 9: Click Book Now
            print("[9/9] Clicking 'Book Now'...")
            await booking_page.click_book_now_in_popup()

            # Verify success
            await asyncio.sleep(2)
            success = await booking_page.verify_booking_success()

            if success:
                print(f"[SUCCESS] Booked desk {found_desk}!")
                return True
            else:
                print(f"[FAILED] Booking verification failed")
                return False

        except Exception as e:
            print(f"[FAILED] Attempt failed: {e}")
            return False


async def run_polling_booking(
    date_str: Optional[str] = None,
    desk_prefix: str = "2.24",
    refresh_interval: int = 30,
    max_attempts: int = 20
) -> bool:
    """
    Quick helper to run polling booking.

    Args:
        date_str: Date in YYYY-MM-DD format (default: tomorrow)
        desk_prefix: Desk prefix to filter (e.g., "2.24")
        refresh_interval: Seconds between refresh attempts (default: 30)
        max_attempts: Maximum number of attempts (default: 20)

    Returns:
        True if successful

    Example:
        from src.workflows.polling_booking import run_polling_booking
        # Try booking 2.24.* desk for tomorrow, refresh every 30s, max 20 attempts
        success = await run_polling_booking("2025-10-28", "2.24", 30, 20)
    """
    workflow = PollingBookingWorkflow(
        date_str=date_str,
        desk_prefix=desk_prefix,
        refresh_interval=refresh_interval,
        max_attempts=max_attempts
    )
    return await workflow.run()
