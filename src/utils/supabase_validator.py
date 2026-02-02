"""
Supabase User Validation - DISABLED

Validation has been removed to allow open registration.
All validation functions now return True.
"""

from typing import Tuple


def validate_user_and_log(username: str, skip_validation: bool = False) -> Tuple[bool, str]:
    """
    Validation disabled - always returns True.

    Args:
        username: Username (ignored)
        skip_validation: Skip validation flag (ignored)

    Returns:
        Always (True, "")
    """
    return (True, "")


def validate_user_from_auth_file(skip_validation: bool = False, user_id: int = None) -> Tuple[bool, str]:
    """
    Validation disabled - always returns True.

    Args:
        skip_validation: Skip validation flag (ignored)
        user_id: User ID (ignored)

    Returns:
        Always (True, "")
    """
    return (True, "")


def check_supabase_connection() -> bool:
    """
    Supabase validation disabled - always returns True.

    Returns:
        Always True
    """
    return True
