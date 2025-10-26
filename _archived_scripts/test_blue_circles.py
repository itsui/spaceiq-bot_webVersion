#!/usr/bin/env python3
"""
Quick test to verify the blue circle approach works
"""

import asyncio
from datetime import datetime, timedelta
from src.workflows.polling_booking import PollingBookingWorkflow

async def main():
    # Test configuration
    target_date = datetime.now() + timedelta(days=19)  # Nov 12 (assuming today is Oct 24)
    date_str = target_date.strftime('%Y-%m-%d')
    desk_prefix = "2.24"

    print("=" * 70)
    print("Testing Blue Circle Approach")
    print("=" * 70)
    print(f"Target Date: {date_str}")
    print(f"Desk Prefix: {desk_prefix}")
    print("=" * 70)
    print()

    # Create workflow
    workflow = PollingBookingWorkflow(
        building="LC",
        floor="2",
        date_str=date_str,
        desk_prefix=desk_prefix,
        refresh_interval=30,  # 30 seconds between attempts
        max_attempts=2  # Only try twice for testing
    )

    # Run the workflow
    await workflow.run()

    print()
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
