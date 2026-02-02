"""
Helper script to check auth session status for map_desk_positions.py

This script checks if you have a valid session in the database for running the desk position mapper.
"""

import json
from pathlib import Path

def check_database_sessions():
    """
    Check for active sessions in the database.

    Returns:
        True if sessions found, False otherwise
    """
    try:
        from app import app
        from models import SpaceIQSession, User
        from src.utils.auth_encryption import decrypt_data

        with app.app_context():
            sessions = SpaceIQSession.query.all()

            if not sessions:
                print("\n[ERROR] No sessions found in database!")
                print("\nPlease authenticate via the web interface:")
                print("  1. Run: start_spaceiq.bat")
                print("  2. Open: http://localhost:5000/")
                print("  3. Click 'Authenticate' and complete MFA\n")
                return False

            print(f"\n[OK] Found {len(sessions)} session(s) in database:\n")

            for session in sessions:
                user = User.query.filter_by(id=session.user_id).first()
                username = user.username if user else "Unknown"

                # Try to decrypt to verify it's valid
                decrypted_json = decrypt_data(session.session_data)
                if decrypted_json:
                    session_data = json.loads(decrypted_json)
                    cookies = session_data.get('cookies', [])
                    status = f"✓ Valid ({len(cookies)} cookies)"
                else:
                    status = "❌ Decryption failed"

                print(f"  User ID {session.user_id} ({username}): {status}")

            print("\n[OK] You can now run the desk position mapper:")
            print("     remap_seat_coordinates.bat")
            print("\n     Or manually with a specific user:")
            print("     python map_desk_positions.py --user-id 1\n")

            return True

    except Exception as e:
        print(f"\n[ERROR] Failed to check database sessions: {e}\n")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Auth Session Status Checker (Multi-User)")
    print("=" * 70 + "\n")

    check_database_sessions()
