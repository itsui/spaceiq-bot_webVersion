"""
Quick Status Checker

Shows current setup status and what steps are complete.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config


def check_status():
    """Check current setup status"""

    print("\n" + "=" * 70)
    print("SpaceIQ Bot - Status Check")
    print("=" * 70 + "\n")

    steps = []

    # Step 1: Dependencies
    try:
        import playwright
        import cv2
        import pyautogui
        steps.append(("Step 1: Dependencies installed", True))
    except ImportError:
        steps.append(("Step 1: Dependencies installed", False))

    # Step 2: Configuration
    configured = Config.SPACEIQ_URL != "https://your-spaceiq-instance.com"
    if configured:
        steps.append((f"Step 2: SpaceIQ URL configured", True))
        print(f"   ✅ URL: {Config.SPACEIQ_URL}")
    else:
        steps.append(("Step 2: SpaceIQ URL configured", False))

    # Step 3: Authentication
    auth_exists = Config.AUTH_STATE_FILE.exists()
    steps.append(("Step 3: Authentication captured", auth_exists))
    if auth_exists:
        import os
        size = os.path.getsize(Config.AUTH_STATE_FILE)
        print(f"   ✅ Auth file: {Config.AUTH_STATE_FILE} ({size} bytes)")

    # Step 4: Workflow recording
    inspector_dir = Path("inspector_output")
    has_recordings = inspector_dir.exists() and any(inspector_dir.glob("*.json"))
    steps.append(("Step 4: Workflow recorded", has_recordings))
    if has_recordings:
        recordings = list(inspector_dir.glob("recorded_clicks_*.json"))
        print(f"   ✅ Recordings: {len(recordings)} file(s)")

    # Print summary
    print("\n" + "=" * 70)
    print("Setup Status")
    print("=" * 70 + "\n")

    all_complete = True
    for step_name, complete in steps:
        status = "✅" if complete else "⏳"
        print(f"{status} {step_name}")
        if not complete:
            all_complete = False

    print("\n" + "=" * 70)

    if all_complete:
        print("✅ ALL STEPS COMPLETE!")
        print("\nYou're ready to run: python main.py")
    else:
        print("⏳ SETUP IN PROGRESS")
        print("\nNext steps:")

        # Suggest next action
        if not steps[0][1]:  # Dependencies
            print("   → Run: python setup.py")
        elif not steps[1][1]:  # Config
            print("   → Edit .env and set SPACEIQ_URL")
        elif not steps[2][1]:  # Auth
            print("   → Run: python src/auth/capture_session.py")
        elif not steps[3][1]:  # Recording
            print("   → Run: python inspect_and_record.py")
            print("   → Then describe your workflow")

    print("=" * 70 + "\n")

    # Additional info
    if auth_exists and configured:
        print("💡 Tips:")
        print("   • Run workflow recorder: python inspect_and_record.py")
        print("   • Test setup: python test_setup.py")
        print("   • Check this status: python check_status.py")
        print("\n")


if __name__ == "__main__":
    check_status()
