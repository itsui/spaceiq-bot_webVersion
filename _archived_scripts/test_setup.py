"""
Test script to verify SpaceIQ Bot setup

Checks all dependencies and configuration.
"""

import sys
from pathlib import Path


def check_python_version():
    """Check if Python version is adequate"""
    version = sys.version_info
    if version >= (3, 8):
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (3.8+ required)")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    required = ['playwright', 'dotenv', 'cv2', 'pyautogui']
    results = []

    for package in required:
        # Special handling for python-dotenv (imports as dotenv)
        import_name = 'dotenv' if package == 'python-dotenv' else package

        try:
            if import_name == 'cv2':
                import cv2
                results.append((package, True, cv2.__version__))
            elif import_name == 'dotenv':
                import dotenv
                results.append((package, True, "installed"))
            elif import_name == 'playwright':
                import playwright
                results.append((package, True, playwright.__version__))
            elif import_name == 'pyautogui':
                import pyautogui
                results.append((package, True, pyautogui.__version__))
        except ImportError:
            results.append((package, False, None))

    all_ok = True
    for package, installed, version in results:
        if installed:
            print(f"✅ {package}: {version}")
        else:
            print(f"❌ {package}: Not installed")
            all_ok = False

    return all_ok


def check_files():
    """Check if required files exist"""
    files_to_check = {
        '.env': 'Configuration file',
        'config.py': 'Config module',
        'main.py': 'Main entry point',
        'src/auth/capture_session.py': 'Session capture script',
        'src/auth/session_manager.py': 'Session manager',
        'src/pages/base_page.py': 'Base page object',
        'src/pages/booking_page.py': 'Booking page object',
        'src/workflows/desk_booking.py': 'Desk booking workflow',
    }

    all_ok = True
    for file_path, description in files_to_check.items():
        if Path(file_path).exists():
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description}: {file_path} not found")
            all_ok = False

    return all_ok


def check_directories():
    """Check if required directories exist"""
    dirs_to_check = [
        'playwright/.auth',
        'screenshots',
        'src',
        'src/auth',
        'src/pages',
        'src/workflows',
        'src/utils',
    ]

    all_ok = True
    for dir_path in dirs_to_check:
        if Path(dir_path).exists():
            print(f"✅ Directory: {dir_path}")
        else:
            print(f"❌ Directory: {dir_path} not found")
            all_ok = False

    return all_ok


def check_configuration():
    """Check if configuration is valid"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config import Config

        print(f"✅ Config loaded")
        print(f"   SpaceIQ URL: {Config.SPACEIQ_URL}")
        print(f"   CDP Port: {Config.CDP_PORT}")
        print(f"   Headless: {Config.HEADLESS}")
        print(f"   Timeout: {Config.TIMEOUT}ms")

        # Check if URL is configured
        if Config.SPACEIQ_URL == "https://your-spaceiq-instance.com":
            print(f"⚠️  SPACEIQ_URL not configured in .env")
            return False

        return True

    except Exception as e:
        print(f"❌ Config error: {e}")
        return False


def check_auth_file():
    """Check if authentication file exists"""
    sys.path.insert(0, str(Path(__file__).parent))
    from config import Config

    if Config.AUTH_STATE_FILE.exists():
        print(f"✅ Authentication file exists: {Config.AUTH_STATE_FILE}")
        return True
    else:
        print(f"⚠️  Authentication file not found: {Config.AUTH_STATE_FILE}")
        print(f"   Run: python src/auth/capture_session.py")
        return False


def main():
    """Main test function"""

    print("\n" + "=" * 70)
    print("SpaceIQ Bot - Setup Verification")
    print("=" * 70 + "\n")

    results = []

    print("🔍 Checking Python version...")
    results.append(("Python version", check_python_version()))

    print("\n🔍 Checking dependencies...")
    results.append(("Dependencies", check_dependencies()))

    print("\n🔍 Checking files...")
    results.append(("Files", check_files()))

    print("\n🔍 Checking directories...")
    results.append(("Directories", check_directories()))

    print("\n🔍 Checking configuration...")
    results.append(("Configuration", check_configuration()))

    print("\n🔍 Checking authentication...")
    auth_ok = check_auth_file()
    results.append(("Authentication", auth_ok))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    all_passed = all(result[1] for result in results)

    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")

    print("=" * 70)

    if all_passed:
        print("\n✅ All checks passed! Bot is ready to use.")
        print("\nRun: python main.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nIf dependencies are missing, run: python setup.py")

    print("\n" + "=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
