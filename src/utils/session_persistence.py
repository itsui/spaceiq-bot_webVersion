"""
Session Persistence Utility

Centralized session management for saving/loading SpaceIQ sessions.
Used by both web interface and standalone tools.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def save_session_to_database(user_id: int, session_data: dict) -> bool:
    """
    Save session data to database for a user.

    Handles:
    - Encryption of session data
    - Database connection
    - Flask app context

    Args:
        user_id: User ID to save session for
        session_data: Session data dict (cookies, localStorage, etc.)

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from app import app, db
        from models import SpaceIQSession
        from src.utils.auth_encryption import encrypt_data

        # Encrypt session data
        encrypted_data = encrypt_data(json.dumps(session_data))

        # Need Flask app context for database operations
        with app.app_context():
            # Get or create session record
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()
            if not spaceiq_session:
                spaceiq_session = SpaceIQSession(user_id=user_id)
                db.session.add(spaceiq_session)

            # Update session data
            spaceiq_session.session_data = encrypted_data
            spaceiq_session.is_valid = True
            spaceiq_session.created_at = datetime.utcnow()

            # Commit to database
            db.session.commit()

            logger.info(f"✓ Session saved to database for user {user_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to save session to database for user {user_id}: {e}", exc_info=True)
        return False


def load_session_from_database(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Load and decrypt session data from database.

    Args:
        user_id: User ID to load session for

    Returns:
        Decrypted session data dict, or None if not found/invalid
    """
    try:
        from app import app
        from models import SpaceIQSession
        from src.utils.auth_encryption import decrypt_data

        with app.app_context():
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()

            if not spaceiq_session:
                logger.warning(f"No session found in database for user {user_id}")
                return None

            if not spaceiq_session.is_valid:
                logger.warning(f"Session for user {user_id} is marked as invalid")
                return None

            if not spaceiq_session.session_data:
                logger.warning(f"Session data is empty for user {user_id}")
                return None

            # Decrypt session data
            decrypted_json = decrypt_data(spaceiq_session.session_data)
            session_data = json.loads(decrypted_json)

            logger.info(f"✓ Session loaded from database for user {user_id}")
            return session_data

    except Exception as e:
        logger.error(f"Failed to load session from database for user {user_id}: {e}", exc_info=True)
        return None


def mark_session_invalid(user_id: int) -> bool:
    """
    Mark a user's session as invalid without deleting it.

    Args:
        user_id: User ID to invalidate session for

    Returns:
        True if marked invalid, False otherwise
    """
    try:
        from app import app, db
        from models import SpaceIQSession

        with app.app_context():
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()

            if spaceiq_session:
                spaceiq_session.is_valid = False
                db.session.commit()
                logger.info(f"✓ Session marked as invalid for user {user_id}")
                return True
            else:
                logger.warning(f"No session found to invalidate for user {user_id}")
                return False

    except Exception as e:
        logger.error(f"Failed to mark session invalid for user {user_id}: {e}", exc_info=True)
        return False


def delete_session(user_id: int) -> bool:
    """
    Completely delete a user's session from database.

    Args:
        user_id: User ID to delete session for

    Returns:
        True if deleted, False otherwise
    """
    try:
        from app import app, db
        from models import SpaceIQSession

        with app.app_context():
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()

            if spaceiq_session:
                db.session.delete(spaceiq_session)
                db.session.commit()
                logger.info(f"✓ Session deleted from database for user {user_id}")
                return True
            else:
                logger.warning(f"No session found to delete for user {user_id}")
                return False

    except Exception as e:
        logger.error(f"Failed to delete session for user {user_id}: {e}", exc_info=True)
        return False


def session_exists(user_id: int) -> bool:
    """
    Check if a valid session exists for a user.

    Args:
        user_id: User ID to check

    Returns:
        True if valid session exists, False otherwise
    """
    try:
        from app import app
        from models import SpaceIQSession

        with app.app_context():
            spaceiq_session = SpaceIQSession.query.filter_by(
                user_id=user_id,
                is_valid=True
            ).first()

            return spaceiq_session is not None and spaceiq_session.session_data

    except Exception as e:
        logger.error(f"Failed to check session existence for user {user_id}: {e}")
        return False
