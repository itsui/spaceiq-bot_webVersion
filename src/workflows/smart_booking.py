"""
Smart Booking Workflow

Reads booking_config.json and tries to book desks for multiple dates
with desk prefix filtering. Stops on first successful booking.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

from src.pages.spaceiq_booking_page import SpaceIQBookingPage
from src.auth.session_manager import SessionManager


class SmartBookingWorkflow:
    """
    Intelligent booking workflow that:
    - Tries multiple dates in sequence
    - Filters desks by prefix
    - Stops on first successful booking
    """

    def __init__(self, config_path: str = "booking_config.json"):
        self.config_path = Path(config_path)
        self.session_manager = SessionManager()
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please create booking_config.json with your booking preferences."
            )

        with open(self.config_path, 'r') as f:
            config = json.load(f)

        # Validate required fields
        required_fields = ['building', 'floor', 'dates_to_try']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in config: {field}")

        return config

    async def run(self) -> Dict:
        """
        Execute smart booking workflow.

        Returns:
            Dictionary with results:
            {
                "success": bool,
                "booked_date": str or None,
                "booked_desk": str or None,
                "attempts": int,
                "failed_dates": list
            }
        """

        building = self.config['building']
        floor = self.config['floor']
        dates = self.config['dates_to_try']
        desk_prefix = self.config.get('desk_preferences', {}).get('prefix')
        stop_on_success = self.config.get('stop_on_first_success', True)

        print("\n" + "=" * 70)
        print("Smart Booking Workflow")
        print("=" * 70)
        print(f"Building: {building}, Floor: {floor}")
        print(f"Dates to try: {len(dates)}")
        if desk_prefix:
            print(f"Desk filter: {desk_prefix}.*")
        print(f"Stop on first success: {stop_on_success}")
        print("=" * 70 + "\n")

        results = {
            "success": False,
            "booked_date": None,
            "booked_desk": None,
            "attempts": 0,
            "failed_dates": [],
            "successful_bookings": []
        }

        try:
            # Initialize authenticated session
            context = await self.session_manager.initialize()
            page = await context.new_page()
            booking_page = SpaceIQBookingPage(page)

            # Try each date
            for date_str in dates:
                results['attempts'] += 1

                print("\n" + "-" * 70)
                print(f"Attempt {results['attempts']}/{len(dates)}: Trying date {date_str}")
                print("-" * 70 + "\n")

                # Parse date
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    print(f"❌ Invalid date format: {date_str} (use YYYY-MM-DD)")
                    results['failed_dates'].append({
                        "date": date_str,
                        "reason": "Invalid date format"
                    })
                    continue

                # Calculate days ahead
                days_ahead = (target_date.date() - datetime.now().date()).days

                if days_ahead < 0:
                    print(f"⚠️  Date {date_str} is in the past, skipping...")
                    results['failed_dates'].append({
                        "date": date_str,
                        "reason": "Date in the past"
                    })
                    continue

                # Try booking for this date
                success = await self._try_book_single_date(
                    booking_page=booking_page,
                    building=building,
                    floor=floor,
                    days_ahead=days_ahead,
                    date_str=date_str,
                    desk_prefix=desk_prefix
                )

                if success:
                    # Get desk info from popup before confirming
                    desk_info = await booking_page.get_desk_info_from_popup()
                    desk_name = desk_info.get('desk_name', 'Unknown desk')

                    results['successful_bookings'].append({
                        "date": date_str,
                        "desk": desk_name
                    })

                    if stop_on_success:
                        results['success'] = True
                        results['booked_date'] = date_str
                        results['booked_desk'] = desk_name

                        print("\n" + "=" * 70)
                        print("✅ BOOKING SUCCESSFUL!")
                        print("=" * 70)
                        print(f"Date: {date_str}")
                        print(f"Desk: {desk_name}")
                        print(f"Attempts: {results['attempts']}")
                        print("=" * 70 + "\n")

                        break  # Stop on first success
                else:
                    results['failed_dates'].append({
                        "date": date_str,
                        "reason": "No available desks or booking failed"
                    })
                    print(f"⚠️  Could not book for {date_str}, trying next date...\n")

            # Final summary
            if not results['success'] and results['successful_bookings']:
                # Multiple bookings mode (stop_on_first_success = false)
                results['success'] = True

            await self._print_summary(results)

        except Exception as e:
            print(f"\n❌ Error during smart booking: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.session_manager.close()

        return results

    async def _try_book_single_date(
        self,
        booking_page: SpaceIQBookingPage,
        building: str,
        floor: str,
        days_ahead: int,
        date_str: str,
        desk_prefix: Optional[str] = None
    ) -> bool:
        """
        Try to book a desk for a single date.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Navigate
            print("📍 Step 1: Navigating to floor view...")
            await booking_page.navigate_to_floor_view(building, floor)

            # Step 2: Click Book Desk
            print("📍 Step 2: Clicking 'Book Desk' button...")
            await booking_page.click_book_desk_button()

            # Step 3: Open date picker
            print("📍 Step 3: Opening date picker...")
            await booking_page.open_date_picker()

            # Step 4: Select date
            print(f"📍 Step 4: Selecting date ({date_str})...")
            await booking_page.select_date_from_calendar(days_ahead=days_ahead)

            # Step 5: Click Update
            print("📍 Step 5: Clicking 'Update' button...")
            await booking_page.click_update_button()

            # Step 6: Wait for floor map
            print("📍 Step 6: Waiting for floor map...")
            await booking_page.wait_for_floor_map_to_load()

            # Step 7: Click available desk (with prefix filter)
            print("📍 Step 7: Selecting available desk...")
            await booking_page.click_available_desk_on_map(desk_prefix=desk_prefix)

            # Verify popup appeared
            if not await booking_page.verify_desk_popup_appeared():
                print("❌ Desk popup did not appear")
                await booking_page.capture_screenshot(f"no_popup_{date_str}", force=True)
                return False

            # Step 8: Click Book Now
            print("📍 Step 8: Clicking 'Book Now'...")
            await booking_page.click_book_now_in_popup()

            # Step 9: Verify success
            print("📍 Step 9: Verifying booking...")
            success = await booking_page.verify_booking_success()

            return success

        except Exception as e:
            print(f"❌ Error booking for {date_str}: {e}")
            await booking_page.capture_screenshot(f"error_{date_str}", force=True)
            return False

    def _print_summary(self, results: Dict):
        """Print final booking summary"""
        print("\n" + "=" * 70)
        print("SMART BOOKING SUMMARY")
        print("=" * 70)
        print(f"Total attempts: {results['attempts']}")
        print(f"Successful bookings: {len(results['successful_bookings'])}")
        print(f"Failed dates: {len(results['failed_dates'])}")

        if results['successful_bookings']:
            print("\n✅ Successful Bookings:")
            for booking in results['successful_bookings']:
                print(f"   • {booking['date']}: {booking['desk']}")

        if results['failed_dates']:
            print("\n❌ Failed Dates:")
            for failed in results['failed_dates']:
                print(f"   • {failed['date']}: {failed['reason']}")

        print("=" * 70 + "\n")


async def run_smart_booking(config_path: str = "booking_config.json") -> Dict:
    """
    Quick helper to run smart booking.

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Results dictionary

    Example:
        from src.workflows.smart_booking import run_smart_booking
        results = await run_smart_booking()
    """
    workflow = SmartBookingWorkflow(config_path)
    return await workflow.run()
