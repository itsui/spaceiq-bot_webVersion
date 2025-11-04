"""
Supabase User Validation and Usage Logging

Validates users against whitelist in Supabase and logs usage.
Transparent integration - users don't need to know about Supabase.
"""

import uuid
from datetime import datetime
from typing import Optional, Tuple
from config import Config


def get_machine_id() -> str:
    """Get unique machine identifier"""
    return hex(uuid.getnode())


def validate_user_and_log(username: str, skip_validation: bool = False) -> Tuple[bool, str]:
    """
    Validate user against Supabase whitelist and log usage.

    Args:
        username: Username extracted from encrypted auth file
        skip_validation: If True, skips validation (REQUIRES DEV_MODE=true in .env)

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, "error message")
    """

    # Skip validation only if DEV_MODE is enabled (prevents users from bypassing whitelist)
    if skip_validation:
        import os
        dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

        if not dev_mode:
            print("[ERROR] --skip-validation requires DEV_MODE=true in .env file")
            print("[ERROR] This flag is for development/testing only")
            return (False, "Access denied - DEV_MODE not enabled")

        print("[WARNING] DEV MODE: Validation skipped (--skip-validation flag)")
        return (True, "")

    # Check if Supabase is configured
    if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
        print("[WARNING] Supabase not configured - skipping validation")
        print("[WARNING] Set SUPABASE_URL and SUPABASE_ANON_KEY in .env file")
        return (True, "")

    try:
        from supabase import create_client, Client

        # Initialize Supabase client
        supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)

        # Check if user is in whitelist
        print(f"[INFO] Validating user: {username}")

        response = supabase.table('allowed_users').select('username, is_active').eq('username', username).execute()

        # Check if user exists
        if not response.data or len(response.data) == 0:
            # User not in whitelist
            error_msg = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          ACCESS DENIED                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

User '{username}' is not authorized to use this bot.

To request access, please contact the administrator and provide:
  - Username: {username}
  - Machine ID: {get_machine_id()}

Administrator: Add this user to the 'allowed_users' table in Supabase.

╔══════════════════════════════════════════════════════════════════════════════╗
"""
            print(error_msg)
            return (False, "Access denied - user not in whitelist")

        user = response.data[0]

        # Check if user is active
        if not user.get('is_active', False):
            error_msg = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       ACCOUNT DEACTIVATED                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

User '{username}' account has been deactivated.

To reactivate access, please contact the administrator.

╔══════════════════════════════════════════════════════════════════════════════╗
"""
            print(error_msg)
            return (False, "Access denied - account deactivated")

        # User is valid - log usage
        print(f"[SUCCESS] User '{username}' validated successfully")

        try:
            # Log usage to Supabase
            log_data = {
                'username': username,
                'machine_id': get_machine_id(),
                'action': 'bot_startup',
                'timestamp': datetime.utcnow().isoformat(),
                'details': {
                    'version': '1.0',
                    'encrypted_auth': True
                }
            }

            supabase.table('usage_logs').insert(log_data).execute()
            print(f"[INFO] Usage logged to Supabase")

        except Exception as log_error:
            # Don't fail if logging fails - just warn
            print(f"[WARNING] Could not log usage to Supabase: {log_error}")

        return (True, "")

    except ImportError:
        print("[WARNING] Supabase library not installed - skipping validation")
        print("[WARNING] Run: pip install supabase")
        return (True, "")

    except Exception as e:
        # Don't fail on network errors - allow offline use
        print(f"[WARNING] Supabase validation failed: {e}")
        print("[WARNING] Continuing without validation (offline mode)")
        return (True, "")


def validate_user_from_auth_file(skip_validation: bool = False) -> Tuple[bool, str]:
    """
    Load encrypted auth file, extract username, and validate.

    Args:
        skip_validation: If True, skips validation (for testing)

    Returns:
        Tuple of (is_valid, error_message)
    """

    # Check if auth file exists
    if not Config.AUTH_STATE_FILE.exists():
        return (False, "No auth file found - please run session warmer first")

    try:
        from src.utils.auth_encryption import load_encrypted_session, extract_username_from_session

        # Load and decrypt session
        session_data = load_encrypted_session(Config.AUTH_STATE_FILE)

        if not session_data:
            return (False, "Could not load/decrypt auth file")

        # Extract username from decrypted session
        username_from_session = extract_username_from_session(session_data)

        if not username_from_session:
            print("[WARNING] Could not extract username from session")
            print("[WARNING] Skipping user validation")
            return (True, "")

        # Security check: Verify .auth_username matches session username
        # This prevents users from editing .auth_username to impersonate others
        username_file = Config.AUTH_STATE_FILE.parent / '.auth_username'
        if username_file.exists():
            stored_username = open(username_file, 'r').read().strip()
            if stored_username != username_from_session:
                error_msg = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       SECURITY VIOLATION DETECTED                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Username mismatch detected:
  - .auth_username file: {stored_username}
  - Session cookie username: {username_from_session}

This indicates file tampering. Please delete both files and re-run session warmer:
  1. Delete: {Config.AUTH_STATE_FILE}
  2. Delete: {username_file}
  3. Run: python auto_warm_session.py

╔══════════════════════════════════════════════════════════════════════════════╗
"""
                print(error_msg)
                return (False, "Security violation - username mismatch")

        # Validate against Supabase
        return validate_user_and_log(username_from_session, skip_validation)

    except Exception as e:
        print(f"[ERROR] Failed to validate user: {e}")
        return (False, f"Validation error: {e}")


def check_supabase_connection() -> bool:
    """
    Test Supabase connection (for debugging).

    Returns:
        True if connection works, False otherwise
    """

    if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
        print("[ERROR] Supabase not configured")
        return False

    try:
        from supabase import create_client

        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)

        # Try to query allowed_users table
        response = supabase.table('allowed_users').select('count').execute()

        print(f"[SUCCESS] Supabase connection OK - {len(response.data)} users in whitelist")
        return True

    except Exception as e:
        print(f"[ERROR] Supabase connection failed: {e}")
        return False
