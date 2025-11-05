"""
Authentication File Encryption Utility

Transparently encrypts/decrypts auth.json using Fernet encryption.
Key is derived from: username + machine ID + hardcoded salt

This provides basic protection against:
- Casual file copying between machines (won't decrypt on different machine)
- Session file tampering (integrity check)
- Plain-text credential exposure

Note: This is security through obscurity and not meant for high-security scenarios.
"""

import json
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
import base64


# Hardcoded salt for key derivation
ENCRYPTION_SALT = "spaceiq_bot_v1_secure"


def get_machine_id() -> str:
    """
    Get unique machine identifier.

    Returns:
        Machine ID as hex string
    """
    return hex(uuid.getnode())


def extract_username_from_session(session_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract username from Playwright storage state JSON.

    Tries multiple common locations where username might be stored:
    - cookies (email/username fields)
    - localStorage (user data)
    - origins data

    Args:
        session_data: Parsed JSON from storage_state

    Returns:
        Username/email if found, None otherwise
    """
    # Try to find username in cookies
    if 'cookies' in session_data:
        for cookie in session_data.get('cookies', []):
            name = cookie.get('name', '')
            value = cookie.get('value', '')

            # Check for specific username cookie (SpaceIQ/Okta uses 'ln' for login name)
            if name == 'ln' and value:
                return value

            # Common cookie names that contain username/email
            if any(x in name.lower() for x in ['email', 'user', 'username', 'login']):
                if value and '@' in value:  # Looks like an email
                    return value
                elif value and len(value) > 2:  # Non-empty username
                    return value

    # Try to find in localStorage
    if 'origins' in session_data:
        for origin in session_data.get('origins', []):
            for item in origin.get('localStorage', []):
                name = item.get('name', '').lower()
                value = item.get('value', '')

                # Look for user data in localStorage
                if any(x in name for x in ['email', 'user', 'username']):
                    # Try to parse if it's JSON
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            for key in ['email', 'username', 'user', 'login']:
                                if key in parsed and parsed[key]:
                                    return parsed[key]
                    except:
                        if '@' in value:
                            return value
                        elif value and len(value) > 2:
                            return value

    return None


def derive_encryption_key(username: str) -> bytes:
    """
    Derive Fernet encryption key from username + machine ID + salt.

    Args:
        username: User's email/username

    Returns:
        32-byte Fernet-compatible key
    """
    machine_id = get_machine_id()

    # Combine all components
    key_material = f"{username}:{machine_id}:{ENCRYPTION_SALT}"

    # Hash to get consistent 32-byte key
    key_hash = hashlib.sha256(key_material.encode()).digest()

    # Fernet requires base64-encoded 32-byte key
    return base64.urlsafe_b64encode(key_hash)


def encrypt_auth_file(file_path: Path, username: str) -> bool:
    """
    Encrypt auth.json file in-place.

    Args:
        file_path: Path to auth.json
        username: Username for key derivation

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if file exists
        if not file_path.exists():
            return False

        # Read the file
        with open(file_path, 'rb') as f:
            data = f.read()

        # Skip if already encrypted (starts with 'gAAAAA' - Fernet signature)
        if data.startswith(b'gAAAAA'):
            # Already encrypted
            return True

        # Derive encryption key
        key = derive_encryption_key(username)
        cipher = Fernet(key)

        # Encrypt
        encrypted_data = cipher.encrypt(data)

        # Write back
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

        return True

    except Exception as e:
        print(f"[ERROR] Failed to encrypt auth file: {e}")
        return False


def decrypt_auth_file(file_path: Path, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Decrypt auth.json file and return parsed JSON.

    Args:
        file_path: Path to auth.json
        username: Username for key derivation (if None, tries to detect from file)

    Returns:
        Decrypted session data as dict, or None if decryption fails
    """
    try:
        # Check if file exists
        if not file_path.exists():
            return None

        # Read the file
        with open(file_path, 'rb') as f:
            data = f.read()

        # Check if file is encrypted (Fernet signature)
        if not data.startswith(b'gAAAAA'):
            # Not encrypted - just parse as JSON
            try:
                return json.loads(data.decode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Failed to parse unencrypted auth file: {e}")
                return None

        # File is encrypted - need username to decrypt
        if username:
            # Try with provided username
            try:
                key = derive_encryption_key(username)
                cipher = Fernet(key)
                decrypted_data = cipher.decrypt(data)
                return json.loads(decrypted_data.decode('utf-8'))
            except InvalidToken:
                print(f"[ERROR] Failed to decrypt auth file with username '{username}'")
                print("[ERROR] This could mean:")
                print("  - File was created on a different machine")
                print("  - File has been tampered with")
                print("  - Username has changed")
                print("\n[SOLUTION] Delete the auth file and login again:")
                filename = file_path.name
                print(f"  rm {filename}")
                print("  python auto_warm_session.py")
                return None
            except Exception as e:
                print(f"[ERROR] Decryption failed: {e}")
                return None
        else:
            # No username provided - can't decrypt
            # Try to read as plain JSON first (backward compatibility)
            print("[ERROR] Encrypted auth file found but no username provided")
            print("[ERROR] Cannot decrypt without username")
            print("\n[SOLUTION] Delete the auth file and login again:")
            filename = file_path.name
            print(f"  rm {filename}")
            print("  python auto_warm_session.py")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to decrypt auth file: {e}")
        return None


def get_username_from_encrypted_file(file_path: Path) -> Optional[str]:
    """
    Try to extract username from encrypted file.
    This requires decrypting, which means we need the username - catch-22!

    For now, this returns None. In practice, username should be stored separately
    or the app should prompt for it.

    Args:
        file_path: Path to encrypted auth.json

    Returns:
        Username if extractable, None otherwise
    """
    # This is a chicken-and-egg problem - we need username to decrypt,
    # but username is inside the encrypted file
    #
    # Solution: Store username in a separate unencrypted file or config
    return None


def save_encrypted_session(file_path: Path, session_data: Dict[str, Any]) -> bool:
    """
    Save session data with automatic encryption.

    Args:
        file_path: Path to save auth.json
        username: Username for key derivation
        session_data: Session state from Playwright

    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract username from session
        username = extract_username_from_session(session_data)

        if not username:
            print("[WARNING] Could not extract username from session")
            print("[WARNING] Session will be saved unencrypted")
            # Save unencrypted as fallback
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            return True

        # Save as JSON first
        json_data = json.dumps(session_data, indent=2).encode('utf-8')

        # Encrypt
        key = derive_encryption_key(username)
        cipher = Fernet(key)
        encrypted_data = cipher.encrypt(json_data)

        # Write encrypted data
        with open(file_path, 'wb') as f:
            f.write(encrypted_data)

        # Also save username to a separate file for future decryption
        username_file = file_path.parent / '.auth_username'
        with open(username_file, 'w', encoding='utf-8') as f:
            f.write(username)

        print(f"[INFO] Session encrypted for user: {username}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to save encrypted session: {e}")
        return False


def load_encrypted_session(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and decrypt session data automatically.

    Args:
        file_path: Path to auth.json

    Returns:
        Decrypted session data, or None if failed
    """
    try:
        # Try to load username from separate file
        username_file = file_path.parent / '.auth_username'
        username = None

        if username_file.exists():
            with open(username_file, 'r', encoding='utf-8') as f:
                username = f.read().strip()

        # Decrypt and load
        session_data = decrypt_auth_file(file_path, username)

        if session_data:
            print(f"[INFO] Session loaded successfully")
            if username:
                print(f"[INFO] Authenticated as: {username}")

        return session_data

    except Exception as e:
        print(f"[ERROR] Failed to load encrypted session: {e}")
        return None


def encrypt_data(data: str) -> str:
    """
    Encrypt string data using machine-specific key.
    Used for database storage of session data.

    Args:
        data: String data to encrypt

    Returns:
        Base64-encoded encrypted data
    """
    try:
        # Validate input
        if not data or len(data.strip()) == 0:
            raise ValueError("Cannot encrypt empty data - session data must not be empty")

        # Use machine ID as username for generic encryption
        machine_id = get_machine_id()
        key = derive_encryption_key(machine_id)
        cipher = Fernet(key)

        encrypted = cipher.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')

    except Exception as e:
        print(f"[ERROR] Failed to encrypt data: {e}")
        raise


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt string data using machine-specific key.
    Used for database retrieval of session data.

    Args:
        encrypted_data: Base64-encoded encrypted data

    Returns:
        Decrypted string data
    """
    try:
        # Validate input
        if not encrypted_data or len(encrypted_data.strip()) == 0:
            raise ValueError("Encrypted data is empty or None")

        # Use machine ID as username for generic decryption
        machine_id = get_machine_id()
        key = derive_encryption_key(machine_id)
        cipher = Fernet(key)

        # Decrypt
        decrypted = cipher.decrypt(encrypted_data.encode('utf-8'))
        decrypted_str = decrypted.decode('utf-8')

        # Validate output
        if not decrypted_str or len(decrypted_str.strip()) == 0:
            raise ValueError("Decryption resulted in empty data - original data may have been empty or corrupted")

        return decrypted_str

    except InvalidToken as e:
        print(f"[ERROR] Invalid encryption token - data may be corrupted or from different machine")
        raise ValueError(f"Failed to decrypt session data - it may be corrupted or from a different machine: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to decrypt data: {e}")
        raise
