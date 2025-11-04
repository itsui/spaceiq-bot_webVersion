#!/usr/bin/env python
"""
Pre-flight check script for SpaceIQ Multi-User Bot Platform
Verifies all dependencies and files are in place before starting
"""

import sys
import os
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_check(name, status, details=""):
    icon = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"  # Green or Red
    reset = "\033[0m"
    print(f"{color}{icon}{reset} {name}")
    if details:
        print(f"  → {details}")

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    version = sys.version_info
    is_ok = version.major == 3 and version.minor >= 9
    return is_ok, f"Python {version.major}.{version.minor}.{version.micro}"

def check_module(module_name, import_name=None):
    """Check if a Python module is installed"""
    if import_name is None:
        import_name = module_name
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def check_file(filepath):
    """Check if a file exists"""
    return Path(filepath).exists()

def main():
    print_header("SpaceIQ Multi-User Platform - Pre-Flight Check")

    all_ok = True

    # Check Python version
    print("\n📌 Python Environment:")
    is_ok, details = check_python_version()
    print_check("Python version (>= 3.9)", is_ok, details)
    if not is_ok:
        all_ok = False

    # Check required modules
    print("\n📌 Required Python Packages:")
    modules = {
        'Flask': 'flask',
        'Flask-SQLAlchemy': 'flask_sqlalchemy',
        'Flask-Login': 'flask_login',
        'SQLAlchemy': 'sqlalchemy',
        'Werkzeug': 'werkzeug',
        'Cryptography': 'cryptography',
        'Bcrypt': 'bcrypt',
        'Playwright': 'playwright',
        'Python-dotenv': 'dotenv',
    }

    missing_modules = []
    for name, import_name in modules.items():
        is_ok = check_module(name, import_name)
        print_check(name, is_ok)
        if not is_ok:
            missing_modules.append(name)
            all_ok = False

    # Check core files
    print("\n📌 Core Application Files:")
    core_files = [
        ('app.py', 'Main application'),
        ('models.py', 'Database models'),
        ('bot_manager.py', 'Bot manager'),
        ('spaceiq_auth_capture.py', 'Auth capture'),
        ('config.py', 'Configuration'),
    ]

    for filepath, description in core_files:
        is_ok = check_file(filepath)
        print_check(f"{filepath} - {description}", is_ok)
        if not is_ok:
            all_ok = False

    # Check templates
    print("\n📌 Web Templates:")
    templates = [
        'templates/base_multi.html',
        'templates/login_multi.html',
        'templates/register.html',
        'templates/dashboard.html',
        'templates/config_multi.html',
        'templates/history_multi.html',
    ]

    for template in templates:
        is_ok = check_file(template)
        print_check(template, is_ok)
        if not is_ok:
            all_ok = False

    # Check directories
    print("\n📌 Required Directories:")
    directories = ['templates', 'static', 'logs', 'config']

    for directory in directories:
        is_ok = Path(directory).is_dir()
        print_check(f"{directory}/", is_ok)
        if not is_ok:
            # Try to create it
            try:
                Path(directory).mkdir(exist_ok=True)
                print(f"  → Created directory: {directory}/")
            except Exception as e:
                print(f"  → Failed to create: {e}")
                all_ok = False

    # Check Playwright browsers
    print("\n📌 Playwright Browsers:")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print_check("Chromium browser", True, "Installed and working")
            except Exception as e:
                print_check("Chromium browser", False, f"Error: {str(e)}")
                print("  → Run: python -m playwright install chromium")
                all_ok = False
    except ImportError:
        print_check("Playwright", False, "Not installed")
        all_ok = False

    # Summary
    print_header("Summary")

    if all_ok:
        print("\n✅ All checks passed! You're ready to start the platform.")
        print("\nTo start:")
        print("  1. Run: python app.py")
        print("  2. Open: http://localhost:5000")
        print("  3. Follow TESTING_GUIDE.md for next steps")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")

        if missing_modules:
            print("\n📦 To install missing packages:")
            print("  pip install -r requirements_multiuser.txt")

        print("\n📖 See TESTING_GUIDE.md for detailed setup instructions")

    print("\n" + "="*60 + "\n")

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
