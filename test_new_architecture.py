"""
Test script for the new architecture
Demonstrates both legacy and new interfaces working with the unified booking engine.
"""

import asyncio
import json
from pathlib import Path

from src.core.booking_engine import BookingEngine, BookingRequest, BookingConfig
from src.reporters.console_progress_reporter import ConsoleProgressReporter
from src.reporters.web_progress_reporter import WebProgressReporter
from src.adapters.unified_booking_adapter import UnifiedBookingAdapter
from src.workflows.multi_date_booking import run_multi_date_booking


async def test_legacy_interface():
    """Test the legacy interface (should work exactly like before)"""
    print("🧪 Testing Legacy Interface")
    print("=" * 50)

    try:
        # This should work exactly like the original bot
        results = await run_multi_date_booking(
            headless=True,  # Use headless for testing
            continuous_loop=False,  # Don't loop forever for testing
            refresh_interval=10,  # Shorter interval for testing
            max_attempts_per_date=1  # Only try once per date for testing
        )

        print(f"✅ Legacy interface completed successfully!")
        print(f"Results: {results}")
        return True

    except Exception as e:
        print(f"❌ Legacy interface failed: {e}")
        return False


async def test_new_interface():
    """Test the new unified interface"""
    print("\n🧪 Testing New Unified Interface")
    print("=" * 50)

    try:
        # Create console progress reporter
        console_reporter = ConsoleProgressReporter()

        # Create unified adapter
        adapter = UnifiedBookingAdapter(console_reporter)

        # Load config
        config_path = Path("config/booking_config.json")
        if config_path.exists():
            booking_config = BookingConfig.from_file(config_path)
        else:
            # Use default config for testing
            booking_config = BookingConfig()

        # Create booking request
        request = BookingRequest(
            user_id="test_user",
            config=booking_config
        )

        # Execute booking using new interface
        result = await adapter.execute_booking_request(request)

        print(f"✅ New interface completed successfully!")
        print(f"Booking ID: {result['booking_id']}")
        print(f"Success: {result['success']}")
        print(f"Successful bookings: {result['successful_bookings']}")
        print(f"Total attempts: {result['total_attempts']}")
        print(f"Duration: {result['duration']}")
        return True

    except Exception as e:
        print(f"❌ New interface failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_web_interface_simulation():
    """Test web interface simulation (without actual WebSocket)"""
    print("\n🧪 Testing Web Interface Simulation")
    print("=" * 50)

    try:
        # Create a mock web logger for testing
        class MockWebLogger:
            def __init__(self):
                self.logs = []

            def info(self, message):
                log = {"level": "INFO", "message": message}
                self.logs.append(log)
                print(f"[WEB INFO] {message}")

            def success(self, message):
                log = {"level": "SUCCESS", "message": message}
                self.logs.append(log)
                print(f"[WEB SUCCESS] {message}")

            def warning(self, message):
                log = {"level": "WARNING", "message": message}
                self.logs.append(log)
                print(f"[WEB WARNING] {message}")

            def error(self, message):
                log = {"level": "ERROR", "message": message}
                self.logs.append(log)
                print(f"[WEB ERROR] {message}")

        # Test with web logger
        mock_web_logger = MockWebLogger()

        results = await run_multi_date_booking(
            headless=True,
            continuous_loop=False,
            refresh_interval=10,
            max_attempts_per_date=1,
            web_logger=mock_web_logger
        )

        print(f"✅ Web interface simulation completed!")
        print(f"Total web logs: {len(mock_web_logger.logs)}")
        print(f"Results: {results}")
        return True

    except Exception as e:
        print(f"❌ Web interface simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_engine_usage():
    """Test direct usage of the booking engine"""
    print("\n🧪 Testing Direct Engine Usage")
    print("=" * 50)

    try:
        # Create a simple progress reporter for testing
        class TestProgressReporter:
            async def report_status(self, status):
                print(f"[STATUS] {status.state.value}: {status.message}")

            async def report_progress(self, update):
                print(f"[PROGRESS] {update.current}/{update.total}: {update.message}")

            async def report_error(self, error, details=None):
                print(f"[ERROR] {error}")
                if details:
                    print(f"[ERROR DETAILS] {details}")

            async def report_log(self, level, message, timestamp=None):
                print(f"[{level}] {message}")

            async def report_booking_result(self, date, success, desk_code=None):
                result = "SUCCESS" if success else "SKIPPED"
                desk_info = f" - Desk {desk_code}" if desk_code else ""
                print(f"[BOOKING] {date}: {result}{desk_info}")

        # Create booking engine with test reporter
        engine = BookingEngine(TestProgressReporter())

        # Create booking request
        config = BookingConfig(
            building="LC",
            floor="2",
            desk_prefix="2.24",
            headless=True,
            continuous_loop=False,  # Don't loop for testing
            refresh_interval=10
        )

        request = BookingRequest(
            user_id="direct_test_user",
            config=config
        )

        # Execute booking
        result = await engine.execute_booking(request)

        print(f"✅ Direct engine usage completed!")
        print(f"Success: {result.success}")
        print(f"Results: {result.results}")
        return True

    except Exception as e:
        print(f"❌ Direct engine usage failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🚀 Testing New SpaceIQ Bot Architecture")
    print("=" * 60)

    tests = [
        ("Legacy Interface", test_legacy_interface),
        ("New Unified Interface", test_new_interface),
        ("Web Interface Simulation", test_web_interface_simulation),
        ("Direct Engine Usage", test_direct_engine_usage),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print(f"\nSummary: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The new architecture is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    print("\n📋 Next Steps:")
    print("1. ✅ Phase 1 Complete: Pure booking engine extracted")
    print("2. 🔄 Phase 2 In Progress: Browser pool management system")
    print("3. ⏳ Phase 3 Pending: Bot service as controllable service")
    print("4. ⏳ Phase 4 Pending: FastAPI backend with WebSocket support")
    print("5. ⏳ Phase 5 Pending: Modern web frontend")


if __name__ == "__main__":
    # Check if config exists
    config_path = Path("config/booking_config.json")
    if not config_path.exists():
        print("⚠️  Warning: config/booking_config.json not found")
        print("   Creating a minimal config for testing...")

        # Create minimal config for testing
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)

        minimal_config = {
            "building": "LC",
            "floor": "2",
            "desk_preferences": {
                "prefix": "2.24"
            },
            "booking_days": {
                "weekdays": [2, 3]  # Wednesday, Thursday
            },
            "wait_times": {
                "rounds_1_to_5": {"seconds": 30}
            },
            "skip_validation": True  # Skip validation for testing
        }

        with open(config_path, 'w') as f:
            json.dump(minimal_config, f, indent=2)

        print(f"✅ Created minimal config at {config_path}")

    asyncio.run(main())