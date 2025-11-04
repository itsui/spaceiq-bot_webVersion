"""
Configuration management for SpaceIQ Bot
Loads environment variables and provides centralized config access
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class"""

    # Base paths
    BASE_DIR = Path(__file__).parent
    AUTH_DIR = BASE_DIR / "playwright" / ".auth"
    SCREENSHOTS_DIR = BASE_DIR / "screenshots"

    @classmethod
    def get_user_screenshots_dir(cls, username: str) -> Path:
        """Get screenshots directory for a specific user (multiuser isolation)"""
        # Sanitize username for filesystem (remove special chars)
        safe_username = "".join(c if c.isalnum() or c in "-_" else "_" for c in username)
        user_dir = cls.SCREENSHOTS_DIR / safe_username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    # SpaceIQ Configuration
    SPACEIQ_URL = os.getenv("SPACEIQ_URL", "https://your-spaceiq-instance.com")
    EMPLOYEE_ID = os.getenv("EMPLOYEE_ID", "RW1wbG95ZWUtRW1wbG95ZWUuMmQ0ZjY0YTMtYWFkMi00NzE2LWFmM2MtMGRiMjFmZjRjMzYw")

    # Browser Configuration
    CDP_PORT = int(os.getenv("CDP_PORT", "9222"))
    HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"
    TIMEOUT = int(os.getenv("TIMEOUT", "30000"))  # milliseconds

    # Booking Configuration
    # Only attempt to book today's date if current time is before this hour
    # Format: 24-hour time (e.g., 9 for 9:00 AM, 14 for 2:00 PM)
    # After this time, assumes you don't need a desk for today
    BOOKING_TODAY_CUTOFF_HOUR = int(os.getenv("BOOKING_TODAY_CUTOFF_HOUR", "9"))
    BOOKING_TODAY_CUTOFF_MINUTE = int(os.getenv("BOOKING_TODAY_CUTOFF_MINUTE", "30"))

    # Logging Configuration
    # Enable/disable console logging (captures all UI output to file)
    # Console logs can get large due to UI refreshes - disable if not needed
    ENABLE_CONSOLE_LOGGING = os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() == "true"
    # Strip ANSI color codes from console logs to reduce file size
    STRIP_ANSI_FROM_LOGS = os.getenv("STRIP_ANSI_FROM_LOGS", "true").lower() == "true"
    # Maximum log file sizes (prevents multi-GB logs during long runs)
    MAX_CONSOLE_LOG_SIZE_MB = int(os.getenv("MAX_CONSOLE_LOG_SIZE_MB", "100"))  # Console log max size
    MAX_BOOKING_LOG_SIZE_MB = int(os.getenv("MAX_BOOKING_LOG_SIZE_MB", "50"))   # Booking log max size
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))                  # Number of rotated backups to keep

    # Screenshot Configuration
    # Enable debug mode to save screenshots for every step (useful for debugging)
    # When disabled, only saves screenshots on actual failures/errors
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    # Number of recent screenshot sessions to keep (1 = current session only)
    SCREENSHOT_RETENTION = int(os.getenv("SCREENSHOT_RETENTION", "1"))

    # Supabase Configuration (User Whitelisting & Usage Tracking)
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

    # Authentication
    AUTH_STATE_FILE = AUTH_DIR / "auth.json"

    # Selector Strategy Priority
    # Following research recommendations: Role > TestId > Text > CSS (last resort)
    SELECTOR_PRIORITY = ["role", "testid", "text", "css"]

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.AUTH_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        if cls.SPACEIQ_URL == "https://your-spaceiq-instance.com":
            raise ValueError(
                "Please configure SPACEIQ_URL in .env file. "
                "Copy .env.example to .env and update the URL."
            )
        return True

# Create directories on import
Config.ensure_directories()
