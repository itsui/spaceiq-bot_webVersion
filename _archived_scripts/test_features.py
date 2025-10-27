"""
Test Script for New Features

Tests:
1. Desk priority sorting
2. Headless mode compatibility (just checks config)
"""

import json
from pathlib import Path
from src.utils.desk_priority import (
    sort_desks_by_priority,
    explain_desk_priorities,
    get_desk_priority,
    is_desk_in_range
)
from config import Config


def test_priority_system():
    """Test desk priority sorting"""
    print("\n" + "=" * 70)
    print("         Testing Desk Priority System")
    print("=" * 70 + "\n")

    # Load config
    config_path = Path(__file__).parent / "config" / "booking_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)

    priority_config = config.get("desk_preferences", {}).get("priority_ranges", [])

    if not priority_config:
        print("[WARNING] No priority ranges configured in booking_config.json")
        print("Add priority_ranges to test this feature.")
        return False

    print(f"Loaded {len(priority_config)} priority ranges:")
    for p in priority_config:
        print(f"  Priority {p['priority']}: {p['range']} - {p['reason']}")

    # Test with sample desks
    sample_desks = [
        "2.24.05", "2.24.10", "2.24.22", "2.24.28",
        "2.24.35", "2.24.44", "2.24.60"
    ]

    print(f"\nTest desks (unsorted): {sample_desks}")

    # Sort by priority
    sorted_desks = sort_desks_by_priority(sample_desks, priority_config)

    print(f"\nSorted by priority:")
    for desk in sorted_desks:
        priority = get_desk_priority(desk, priority_config)
        priority_label = f"Priority {priority}" if priority < 999 else "No priority"
        print(f"  {desk} ({priority_label})")

    # Show detailed explanation
    print(f"\n{explain_desk_priorities(sorted_desks, priority_config)}")

    # Verify priorities are applied
    priorities = [get_desk_priority(d, priority_config) for d in sorted_desks]
    if priorities == sorted(priorities):
        print("\n[SUCCESS] Priority sorting works correctly!")
        return True
    else:
        print("\n[FAILED] Priority sorting failed!")
        print(f"Expected sorted: {sorted(priorities)}")
        print(f"Got: {priorities}")
        return False


def test_range_detection():
    """Test range detection logic"""
    print("\n" + "=" * 70)
    print("         Testing Range Detection")
    print("=" * 70 + "\n")

    test_cases = [
        ("2.24.25", "2.24.20-2.24.30", True),
        ("2.24.20", "2.24.20-2.24.30", True),
        ("2.24.30", "2.24.20-2.24.30", True),
        ("2.24.19", "2.24.20-2.24.30", False),
        ("2.24.31", "2.24.20-2.24.30", False),
    ]

    all_passed = True
    for desk, range_str, expected in test_cases:
        result = is_desk_in_range(desk, range_str)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} {desk} in {range_str}: {result} (expected {expected})")
        if result != expected:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All range detection tests passed!")
    else:
        print("\n[FAILED] Some range detection tests failed!")

    return all_passed


def test_headless_config():
    """Test headless mode configuration"""
    print("\n" + "=" * 70)
    print("         Testing Headless Mode Configuration")
    print("=" * 70 + "\n")

    print(f"Current HEADLESS setting: {Config.HEADLESS}")

    if Config.HEADLESS:
        print("[ENABLED] Headless mode is ON")
        print("   Bot will run in background (no browser window)")
    else:
        print("[DISABLED] Headless mode is OFF")
        print("   Bot will show browser window")

    print(f"\nTo change: Edit .env file and set HEADLESS=true or HEADLESS=false")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("         Feature Testing Suite")
    print("=" * 70)

    results = {}

    # Test priority system
    results['Range Detection'] = test_range_detection()
    results['Priority System'] = test_priority_system()
    results['Headless Config'] = test_headless_config()

    # Summary
    print("\n" + "=" * 70)
    print("         Test Summary")
    print("=" * 70 + "\n")

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n[SUCCESS] All tests passed! Features are ready to use.")
        print("\nNext steps:")
        print("1. Configure desk priorities in config/booking_config.json")
        print("2. Set HEADLESS=true in .env for background mode")
        print("3. Run: python multi_date_book.py --auto")
    else:
        print("\n[WARNING] Some tests failed. Please check the output above.")

    print("\n" + "=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
