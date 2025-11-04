"""
Desk Booking Workflow

This module demonstrates a complete end-to-end booking workflow
following Phase 1 best practices:
- Test isolation
- Clear step-by-step logic
- Comprehensive error handling
- Auto-waiting (no manual sleeps)
"""

from playwright.async_api import Page
from src.pages.booking_page import BookingPage
from src.auth.session_manager import SessionManager
from datetime import datetime, timedelta
from typing import Dict, Optional


class DeskBookingWorkflow:
    """
    Complete workflow for booking a desk in SpaceIQ.

    This is a template/example - you'll need to customize based on
    the actual SpaceIQ UI flow.
    """

    def __init__(self):
        self.session_manager = SessionManager()

    async def book_desk(
        self,
        location: str,
        date: Optional[str] = None,
        space_preferences: Optional[Dict] = None
    ) -> bool:
        """
        Execute complete desk booking workflow.

        Args:
            location: Location name (e.g., "New York Office")
            date: Booking date in format 'YYYY-MM-DD'. If None, books for tomorrow.
            space_preferences: Optional dict with preferences like {'floor': '5', 'features': ['window']}

        Returns:
            True if booking successful, False otherwise

        Example:
            workflow = DeskBookingWorkflow()
            success = await workflow.book_desk(
                location="San Francisco Office",
                date="2025-10-30"
            )
        """

        # Default to tomorrow if no date provided
        if date is None:
            tomorrow = datetime.now() + timedelta(days=1)
            date = tomorrow.strftime('%Y-%m-%d')

        print("\n" + "=" * 70)
        print(f"Starting Desk Booking Workflow")
        print("=" * 70)
        print(f"Location: {location}")
        print(f"Date: {date}")
        if space_preferences:
            print(f"Preferences: {space_preferences}")
        print("=" * 70 + "\n")

        try:
            # Initialize authenticated session
            context = await self.session_manager.initialize()
            page = await context.new_page()

            # Create page object
            booking_page = BookingPage(page)

            # Step 1: Navigate to booking page
            print("\n📍 Step 1: Navigating to booking page...")
            await booking_page.navigate_to_booking()

            # Step 2: Initiate new booking
            print("\n📍 Step 2: Initiating new booking...")
            await booking_page.click_new_booking_button()

            # Step 3: Select location
            print("\n📍 Step 3: Selecting location...")
            await booking_page.select_location(location)

            # Step 4: Select date
            print("\n📍 Step 4: Selecting date...")
            await booking_page.select_date(date)

            # Step 5: Select space type (Desk)
            print("\n📍 Step 5: Selecting space type (Desk)...")
            await booking_page.select_space_type("Desk")

            # Step 6: Search for available spaces
            print("\n📍 Step 6: Searching for available spaces...")
            await booking_page.search_available_spaces()

            # Step 7: Wait for results
            print("\n📍 Step 7: Waiting for search results...")
            await booking_page.wait_for_search_results()

            # Step 8: Check available spaces
            available_count = await booking_page.get_available_spaces_count()
            print(f"   Found {available_count} available spaces")

            if available_count == 0:
                print("\n❌ No available spaces found for this date/location")
                await booking_page.capture_screenshot("no_spaces_available", force=True)
                return False

            # Step 9: Select first available space (or apply preferences)
            print("\n📍 Step 9: Selecting space...")
            # TODO: Implement preference-based selection if needed
            # For now, we'll assume we're selecting a specific space
            # This logic will vary based on your actual needs
            await booking_page.select_specific_space("Any Available Desk")

            # Step 10: Confirm booking
            print("\n📍 Step 10: Confirming booking...")
            await booking_page.confirm_booking()

            # Step 11: Verify success
            print("\n📍 Step 11: Verifying booking confirmation...")
            success = await booking_page.verify_booking_success()

            if success:
                print("\n" + "=" * 70)
                print("✅ BOOKING SUCCESSFUL!")
                print("=" * 70)
                print(f"Location: {location}")
                print(f"Date: {date}")
                print("=" * 70 + "\n")
            else:
                print("\n" + "=" * 70)
                print("❌ BOOKING FAILED")
                print("=" * 70)
                print("Could not verify booking confirmation.")
                print("=" * 70 + "\n")

            return success

        except Exception as e:
            print(f"\n❌ Error during booking workflow: {e}")
            if 'booking_page' in locals():
                await booking_page.capture_screenshot("workflow_error", force=True)
            return False

        finally:
            # Clean up
            await self.session_manager.close()


async def quick_book_desk(location: str, date: Optional[str] = None) -> bool:
    """
    Quick helper function to book a desk.

    Args:
        location: Location name
        date: Optional date string (YYYY-MM-DD)

    Returns:
        True if successful

    Example:
        from src.workflows.desk_booking import quick_book_desk
        success = await quick_book_desk("New York Office", "2025-10-30")
    """
    workflow = DeskBookingWorkflow()
    return await workflow.book_desk(location=location, date=date)
