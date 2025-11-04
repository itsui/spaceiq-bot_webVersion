#!/usr/bin/env python3
"""
Pre-Deployment Checklist Script
Verifies that your SpaceIQ Bot is ready for remote testing
"""

import os
import sys
import subprocess
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{text}{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")

def check_pass(message):
    """Print a passing check"""
    print(f"{GREEN}✓{RESET} {message}")

def check_warning(message):
    """Print a warning check"""
    print(f"{YELLOW}⚠{RESET} {message}")

def check_fail(message):
    """Print a failing check"""
    print(f"{RED}✗{RESET} {message}")

def check_info(message):
    """Print an info message"""
    print(f"{BLUE}ℹ{RESET} {message}")

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        check_pass(f"Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        check_fail(f"Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path('.env')

    if not env_path.exists():
        check_fail(".env file not found")
        check_info("Run: cp .env.example .env")
        return False

    check_pass(".env file exists")

    # Check for required variables
    from dotenv import load_dotenv
    load_dotenv()

    issues = []

    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'change-this-to-a-random-secret-key':
        issues.append("SECRET_KEY not set or using default")
        check_fail("SECRET_KEY is not properly configured")
        check_info("Generate with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    else:
        check_pass("SECRET_KEY is configured")

    # Check Flask environment
    flask_env = os.getenv('FLASK_ENV', 'development')
    if flask_env == 'production':
        check_pass("FLASK_ENV=production")
    else:
        check_warning(f"FLASK_ENV={flask_env} (should be 'production' for remote testing)")

    # Check Flask debug
    flask_debug = os.getenv('FLASK_DEBUG', '1')
    if flask_debug.lower() in ('0', 'false', 'no'):
        check_pass("FLASK_DEBUG=0 (debug disabled)")
    else:
        check_warning("FLASK_DEBUG enabled (should be disabled for remote testing)")

    # Check Supabase configuration
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if supabase_url and supabase_url != 'https://yourproject.supabase.co':
        check_pass("SUPABASE_URL is configured")
    else:
        check_warning("SUPABASE_URL not configured (whitelist validation will fail)")

    if supabase_key and supabase_key != 'your-anon-key-here':
        check_pass("SUPABASE_ANON_KEY is configured")
    else:
        check_warning("SUPABASE_ANON_KEY not configured (whitelist validation will fail)")

    return len(issues) == 0

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        check_pass(f"Flask {flask.__version__} installed")
    except ImportError:
        check_fail("Flask not installed")
        return False

    try:
        import flask_login
        check_pass(f"Flask-Login installed")
    except ImportError:
        check_fail("Flask-Login not installed")
        return False

    try:
        import flask_limiter
        check_pass(f"Flask-Limiter installed")
    except ImportError:
        check_fail("Flask-Limiter not installed")
        check_info("Run: pip install Flask-Limiter")
        return False

    try:
        import playwright
        check_pass(f"Playwright installed")
    except ImportError:
        check_fail("Playwright not installed")
        return False

    try:
        import dotenv
        check_pass(f"python-dotenv installed")
    except ImportError:
        check_fail("python-dotenv not installed")
        return False

    return True

def check_database():
    """Check if database exists"""
    db_path = Path('spaceiq_multiuser.db')

    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        check_pass(f"Database exists (size: {size_mb:.2f} MB)")
        return True
    else:
        check_warning("Database not found (will be created on first run)")
        return True

def check_cloudflared():
    """Check if cloudflared is installed"""
    try:
        result = subprocess.run(
            ['cloudflared', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            check_pass(f"cloudflared installed ({version})")
            return True
        else:
            check_fail("cloudflared not working properly")
            return False
    except FileNotFoundError:
        check_fail("cloudflared not installed")
        check_info("Install with:")
        check_info("  - Windows: winget install Cloudflare.cloudflared")
        check_info("  - Mac: brew install cloudflared")
        check_info("  - Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/")
        return False
    except subprocess.TimeoutExpired:
        check_fail("cloudflared command timed out")
        return False

def check_port_5000():
    """Check if port 5000 is available"""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 5000))
    sock.close()

    if result == 0:
        check_warning("Port 5000 is already in use (Flask app may be running)")
        return True
    else:
        check_pass("Port 5000 is available")
        return True

def check_app_file():
    """Check if main app file exists"""
    app_path = Path('app.py')

    if app_path.exists():
        check_pass("app.py exists")
        return True
    else:
        check_fail("app.py not found")
        return False

def main():
    """Run all checks"""
    print_header("SpaceIQ Bot - Production Readiness Checklist")

    all_passed = True

    # Python version
    print_header("1. Python Environment")
    if not check_python_version():
        all_passed = False

    # Dependencies
    print_header("2. Dependencies")
    if not check_dependencies():
        all_passed = False
        check_info("Run: pip install -r requirements_production.txt")

    # Environment file
    print_header("3. Environment Configuration")
    if not check_env_file():
        all_passed = False

    # Application files
    print_header("4. Application Files")
    if not check_app_file():
        all_passed = False

    # Database
    print_header("5. Database")
    check_database()

    # Network
    print_header("6. Network")
    check_port_5000()

    # Cloudflare
    print_header("7. Cloudflare Tunnel")
    if not check_cloudflared():
        all_passed = False

    # Final summary
    print_header("Summary")

    if all_passed:
        print(f"{GREEN}{BOLD}✓ All critical checks passed!{RESET}")
        print(f"\nYou are ready for remote testing. Next steps:")
        print(f"  1. Run: python app.py (or start_app_production.bat/sh)")
        print(f"  2. Run: cloudflared tunnel --url http://localhost:5000")
        print(f"  3. Share the generated URL with your friend")
    else:
        print(f"{RED}{BOLD}✗ Some checks failed!{RESET}")
        print(f"\nPlease fix the issues above before deploying.")
        print(f"Refer to REMOTE_TESTING_GUIDE.md for detailed instructions.")
        sys.exit(1)

    print()

if __name__ == '__main__':
    main()
