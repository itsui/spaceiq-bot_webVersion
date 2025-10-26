"""
Direct API-based booking using GraphQL mutations.
Bypasses UI interactions entirely - more reliable and faster.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from playwright.async_api import Page


class BookingAPI:
    """Direct API interface for SpaceIQ bookings"""

    def __init__(self, page: Page):
        self.page = page
        self.api_url = "https://api.spaceiq.com/queries"

        # Hardcoded spaceIds for known desks (from HAR analysis)
        self.desk_space_ids = {
            "2.24.20": "U3BhY2UtU3BhY2UuMjY3MmIyMDMtMWE0MS00ZDY1LWIzOWItZTcyMmIzZTNjN2I3OjQ3YjY1ZWE3LTUwMjctNDJhYy04OGMyLWIwMGE1NzRhNDI1Zg==",
            "2.24.28": "U3BhY2UtU3BhY2UuY2FjMTEzN2EtOGVhMy00YjJmLThkYzgtMzcyZTVkYzU5NjdlOjQ3YjY1ZWE3LTUwMjctNDJhYy04OGMyLWIwMGE1NzRhNDI1Zg==",
        }

    async def get_desk_by_code(self, desk_code: str, floor_code: str = "2", building_code: str = "LC") -> Optional[Dict]:
        """
        Find desk details by desk code using GraphQL query.

        Args:
            desk_code: Desk code like "2.24.28"
            floor_code: Floor code like "2"
            building_code: Building code like "LC"

        Returns:
            Dict with desk details including spaceId, or None if not found
        """
        # GraphQL query to find desk by external ID
        query = """
        query findDesk($externalId: String!) {
          spaces(externalId: $externalId) {
            edges {
              node {
                id
                code
                externalId
                x
                y
              }
            }
          }
        }
        """

        external_id = f"{building_code}-{floor_code}-{desk_code}"

        response = await self.page.request.post(
            self.api_url,
            data={
                "query": query,
                "variables": {"externalId": external_id}
            }
        )

        data = await response.json()

        if data.get("data", {}).get("spaces", {}).get("edges"):
            return data["data"]["spaces"]["edges"][0]["node"]

        return None

    async def create_booking(
        self,
        space_id: str,
        employee_id: str,
        date: str,
        start_time: str = "09:00:00",
        end_time: str = "18:00:00"
    ) -> Dict:
        """
        Create a booking using GraphQL mutation.

        Args:
            space_id: Encoded space ID (e.g., "U3BhY2UtU3BhY2U...")
            employee_id: Encoded employee ID (e.g., "RW1wbG95ZWUtRW1wbG95ZWU...")
            date: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM:SS format
            end_time: End time in HH:MM:SS format

        Returns:
            Dict with booking details from API response
        """
        mutation = """mutation createBooking($input: CreateBookingInput!) {
  createBooking(input: $input) {
    booking {
      id
      date
      startDate
      endDate
      space {
        id
        externalId
        code
      }
      employee {
        id
        name
        email
      }
    }
  }
}"""

        start_datetime = f"{date} {start_time} UTC"
        end_datetime = f"{date} {end_time} UTC"

        import json
        payload = json.dumps({
            "query": mutation,
            "variables": {
                "input": {
                    "spaceId": space_id,
                    "employeeId": employee_id,
                    "startDate": start_datetime,
                    "endDate": end_datetime,
                    "note": ""
                }
            }
        })

        print(f"       Making POST to {self.api_url}")
        print(f"       Payload: {payload[:150]}...")

        response = await self.page.request.post(
            self.api_url,
            headers={
                "content-type": "application/json",
                "accept": "application/json"
            },
            data=payload
        )

        print(f"       Response status: {response.status}")
        data = await response.json()
        return data

    async def book_desk_by_code(
        self,
        desk_code: str,
        employee_id: str,
        date: str,
        floor_code: str = "2",
        building_code: str = "LC"
    ) -> bool:
        """
        Book a desk by its code (uses hardcoded spaceIds for speed).

        Args:
            desk_code: Desk code like "2.24.28"
            employee_id: Encoded employee ID
            date: Date in YYYY-MM-DD format
            floor_code: Floor code
            building_code: Building code

        Returns:
            True if successful, False otherwise
        """
        # Use hardcoded spaceId if available
        if desk_code in self.desk_space_ids:
            space_id = self.desk_space_ids[desk_code]
            print(f"       Using cached spaceId for {desk_code}")
        else:
            print(f"       [FAILED] No spaceId cached for desk {desk_code}")
            print(f"       Available desks: {list(self.desk_space_ids.keys())}")
            return False

        # Create booking
        try:
            print(f"       Calling createBooking mutation...")
            result = await self.create_booking(space_id, employee_id, date)
            print(f"       Got API response: {str(result)[:200]}")

            if result.get("data", {}).get("createBooking", {}).get("booking"):
                booking = result["data"]["createBooking"]["booking"]
                print(f"       [SUCCESS] Booked {booking['space']['externalId']} for {booking['date']}")
                return True
            elif "errors" in result:
                print(f"       [FAILED] API errors: {result['errors']}")
                return False
            else:
                print(f"       [FAILED] Unexpected response: {result}")
                return False
        except Exception as e:
            print(f"       [FAILED] Exception during booking: {e}")
            import traceback
            traceback.print_exc()
            return False
