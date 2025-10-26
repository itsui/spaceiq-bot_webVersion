"""
Booking Page Object for SpaceIQ

This is an example/template Page Object that demonstrates the structure.
You will need to customize the selectors based on actual SpaceIQ UI elements.

TODO: Update selectors after inspecting the actual SpaceIQ application.
"""

from .base_page import BasePage
from playwright.async_api import Page
from typing import Optional


class BookingPage(BasePage):
    """
    Page Object for SpaceIQ booking interface.

    This class encapsulates all interactions with the booking page,
    following the resilient selector hierarchy.
    """

    def __init__(self, page: Page):
        super().__init__(page)

    async def navigate_to_booking(self):
        """Navigate to the booking section"""
        # TODO: Update with actual SpaceIQ URL structure
        await self.navigate(f"{Config.SPACEIQ_URL}/booking")

    # ============================================================================
    # EXAMPLE METHODS - Update these based on actual SpaceIQ UI
    # ============================================================================

    async def click_new_booking_button(self):
        """
        Example: Click the 'New Booking' or 'Book Now' button.

        Using Tier 1 selector (getByRole) - most resilient approach.
        """
        # Try to find by role and name (most stable)
        button = self.get_by_role('button', name='Book Now')

        # Alternative: if the above doesn't work, try by test ID
        # button = self.get_by_test_id('new-booking-btn')

        await self.click_element(button, "New Booking button")

    async def select_location(self, location_name: str):
        """
        Example: Select a location from a dropdown.

        Args:
            location_name: Name of the location to select
        """
        # Try label-based selector first (Tier 1)
        location_dropdown = self.get_by_label('Location')

        # Alternative approaches if needed:
        # location_dropdown = self.get_by_test_id('location-select')
        # location_dropdown = self.get_by_role('combobox', name='Location')

        await self.select_dropdown(location_dropdown, location_name, "Location dropdown")

    async def select_date(self, date: str):
        """
        Example: Select a booking date.

        Args:
            date: Date string (format depends on SpaceIQ's implementation)

        Note: If SpaceIQ uses a canvas-based calendar, this will need
        Phase 2 hybrid visual recognition.
        """
        # Try to find date input by label
        date_input = self.get_by_label('Date')

        # Alternative:
        # date_input = self.get_by_placeholder('Select date')
        # date_input = self.get_by_test_id('booking-date')

        await self.fill_input(date_input, date, "Date field")

    async def select_space_type(self, space_type: str):
        """
        Example: Select space type (desk, room, etc.)

        Args:
            space_type: Type of space to book (e.g., 'Desk', 'Meeting Room')
        """
        # Try role-based selector
        space_button = self.get_by_role('button', name=space_type)

        # Alternative:
        # space_button = self.get_by_text(space_type)

        await self.click_element(space_button, f"{space_type} button")

    async def search_available_spaces(self):
        """Example: Click search/find available spaces button"""
        search_button = self.get_by_role('button', name='Search')

        # Alternatives:
        # search_button = self.get_by_role('button', name='Find Available')
        # search_button = self.get_by_test_id('search-spaces-btn')

        await self.click_element(search_button, "Search button")

    async def select_specific_space(self, space_name: str):
        """
        Example: Select a specific space from search results.

        Args:
            space_name: Name or identifier of the space
        """
        # This might be a button or clickable element in search results
        space_element = self.get_by_role('button', name=space_name)

        # Alternative:
        # space_element = self.get_by_text(space_name)

        await self.click_element(space_element, f"Space: {space_name}")

    async def confirm_booking(self):
        """Example: Click the final confirm/submit booking button"""
        confirm_button = self.get_by_role('button', name='Confirm')

        # Alternatives:
        # confirm_button = self.get_by_role('button', name='Submit')
        # confirm_button = self.get_by_test_id('confirm-booking-btn')

        await self.click_element(confirm_button, "Confirm Booking button")

    async def verify_booking_success(self) -> bool:
        """
        Example: Verify that booking was successful.

        Returns:
            True if success message is visible, False otherwise
        """
        # Look for success message/confirmation
        success_message = self.get_by_text('Booking confirmed')

        # Alternative:
        # success_message = self.get_by_role('alert')
        # success_message = self.get_by_test_id('booking-success-msg')

        try:
            await self.wait_for_element(success_message, 'visible', 'Success message')
            return True
        except:
            await self.capture_screenshot('booking_verification_failed')
            return False

    # ============================================================================
    # Helper Methods for Complex Interactions
    # ============================================================================

    async def get_available_spaces_count(self) -> int:
        """
        Example: Count number of available spaces in search results.

        Returns:
            Number of available spaces
        """
        # This is an example - actual implementation depends on UI structure
        spaces = self.locator('[data-testid="space-card"]')  # Last resort CSS
        return await spaces.count()

    async def wait_for_search_results(self):
        """Example: Wait for search results to load"""
        # Wait for loading indicator to disappear
        loading = self.get_by_test_id('loading-spinner')
        await self.wait_for_element(loading, 'hidden', 'Loading spinner')

        # Or wait for results container to appear
        results = self.get_by_role('list', name='Available Spaces')
        await self.wait_for_element(results, 'visible', 'Search results')


# Import Config for URL construction
from config import Config
