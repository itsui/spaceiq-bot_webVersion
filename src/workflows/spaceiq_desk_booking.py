"""
SpaceIQ Desk Booking Workflow - Customized Implementation

This workflow implements the exact booking process based on your SpaceIQ system:
1. Navigate to floor view (already at correct URL)
2. Click "Book Desk" button
3. Open date picker
4. Select date from calendar
5. Click "Update"
6. Wait for floor map to load
7. Click available desk (blue circle)
8. Click "Book Now" in popup
9. Verify success
"""

from playwright.async_api import Page
from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager
from datetime import datetime, timedelta
from typing import Optional
import asyncio


class SpaceIQDeskBookingWorkflow:
    """
    Complete workflow for booking a desk in your SpaceIQ system.
    """

    def __init__(self):
        self.session_manager = SessionManager()

    async def book_desk(
        self,
        building: str = "LC",
        floor: str = "2",
        days_ahead: int = 1,
        desk_preference: Optional[str] = None
    ) -> bool:
        """
        Execute complete desk booking workflow for SpaceIQ.

        Args:
            building: Building code (default: LC)
            floor: Floor number (default: 2)
            days_ahead: Number of days from today to book (default: 1 = tomorrow)
            desk_preference: Optional specific desk ID (e.g., "2.24.30")

        Returns:
            True if booking successful, False otherwise

        Example:
            workflow = SpaceIQDeskBookingWorkflow()
            success = await workflow.book_desk(
                building="LC",
                floor="2",
                days_ahead=1  # Tomorrow
            )
        """

        # Calculate booking date
        booking_date = datetime.now() + timedelta(days=days_ahead)
        date_str = booking_date.strftime('%Y-%m-%d (%A)')

        print("\n" + "=" * 70)
        print(f"SpaceIQ Desk Booking Workflow")
        print("=" * 70)
        print(f"Building: {building}")
        print(f"Floor: {floor}")
        print(f"Date: {date_str}")
        if desk_preference:
            print(f"Preferred Desk: {desk_preference}")
        print("=" * 70 + "\n")

        try:
            # Initialize authenticated session
            context = await self.session_manager.initialize()
            page = await context.new_page()

            # Create page object
            booking_page = SpaceIQBookingPage(page)

            # ================================================================
            # STEP 1: Navigate to floor view
            # ================================================================
            print("\n📍 Step 1: Navigating to floor view...")
            await booking_page.navigate_to_floor_view(building, floor)

            # ================================================================
            # STEP 2: Click "Book Desk" button
            # ================================================================
            print("\n📍 Step 2: Clicking 'Book Desk' button...")
            await booking_page.click_book_desk_button()

            # ================================================================
            # STEP 3: Open date picker
            # ================================================================
            print("\n📍 Step 3: Opening date picker...")
            await booking_page.open_date_picker()

            # ================================================================
            # STEP 4: Select date from calendar
            # ================================================================
            print(f"\n📍 Step 4: Selecting date ({date_str})...")
            await booking_page.select_date_from_calendar(days_ahead=days_ahead)

            # ================================================================
            # STEP 5: Click "Update" button
            # ================================================================
            print("\n📍 Step 5: Clicking 'Update' button...")
            await booking_page.click_update_button()

            # ================================================================
            # STEP 6: Wait for floor map to load
            # ================================================================
            print("\n📍 Step 6: Waiting for floor map to load...")
            await booking_page.wait_for_floor_map_to_load()

            # ================================================================
            # STEP 7: Click available desk on map
            # ================================================================
            print("\n📍 Step 7: Selecting available desk...")
            await booking_page.click_available_desk_on_map(desk_preference)

            # Verify popup appeared
            popup_appeared = await booking_page.verify_desk_popup_appeared()
            if not popup_appeared:
                print("\n❌ Desk information popup did not appear")
                await booking_page.capture_screenshot("no_popup")
                return False

            # Get desk info
            desk_info = await booking_page.get_desk_info_from_popup()
            if desk_info.get('desk_name'):
                print(f"   ℹ️  Selected: {desk_info['desk_name']}")

            # ================================================================
            # STEP 8: Click "Book Now" in popup
            # ================================================================
            print("\n📍 Step 8: Clicking 'Book Now'...")
            await booking_page.click_book_now_in_popup()

            # ================================================================
            # STEP 9: Verify booking success
            # ================================================================
            print("\n📍 Step 9: Verifying booking success...")
            success = await booking_page.verify_booking_success()

            if success:
                print("\n" + "=" * 70)
                print("✅ BOOKING SUCCESSFUL!")
                print("=" * 70)
                print(f"Building: {building}, Floor: {floor}")
                print(f"Date: {date_str}")
                if desk_info.get('desk_name'):
                    print(f"Desk: {desk_info['desk_name']}")
                print("=" * 70 + "\n")
                await booking_page.capture_screenshot("booking_success")
            else:
                print("\n" + "=" * 70)
                print("⚠️  BOOKING STATUS UNCLEAR")
                print("=" * 70)
                print("Please check the screenshot in screenshots/ folder")
                print("The booking may have succeeded but confirmation was not detected")
                print("=" * 70 + "\n")

            return success

        except Exception as e:
            print(f"\n❌ Error during booking workflow: {e}")
            if 'booking_page' in locals():
                await booking_page.capture_screenshot("workflow_error")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Clean up
            await self.session_manager.close()


async def quick_book_desk(
    building: str = "LC",
    floor: str = "2",
    days_ahead: int = 1,
    desk_preference: Optional[str] = None
) -> bool:
    """
    Quick helper function to book a desk.

    Args:
        building: Building code (default: LC)
        floor: Floor number (default: 2)
        days_ahead: Days from today (default: 1 = tomorrow)
        desk_preference: Optional specific desk ID

    Returns:
        True if successful

    Example:
        from src.workflows.spaceiq_desk_booking import quick_book_desk
        success = await quick_book_desk(days_ahead=1)
    """
    workflow = SpaceIQDeskBookingWorkflow()
    return await workflow.book_desk(
        building=building,
        floor=floor,
        days_ahead=days_ahead,
        desk_preference=desk_preference
    )
