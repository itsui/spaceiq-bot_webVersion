"""
Multi-Date Booking Runner - Web Interface Compatible Version
Designed to work with the web interface without Rich console output
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Any

# Add the root directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.utils.auth_encryption import load_encrypted_session
from src.workflows.multi_date_booking import run_multi_date_booking

class WebBotLogger:
    """Logger designed for web interface instead of Rich console output"""

    def __init__(self):
        self.logs = []
        self.max_logs = 500

    def info(self, message: str):
        """Log info message"""
        self._log("INFO", message)

    def success(self, message: str):
        """Log success message"""
        self._log("SUCCESS", message)

    def error(self, message: str):
        """Log error message"""
        self._log("ERROR", message)

    def warning(self, message: str):
        """Log warning message"""
        self._log("WARNING", message)

    def _log(self, level: str, message: str):
        """Internal logging method"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }

        self.logs.append(log_entry)

        # Keep only the last N logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

        # Also print to console for debugging
        print(f"[{timestamp}] [{level}] {message}")

    def get_logs(self) -> List[Dict]:
        """Get all logs"""
        return self.logs.copy()

def generate_wednesday_thursday_dates(weeks_ahead: int = 4, extra_days: int = 1) -> List[str]:
    """Generate all Wednesday and Thursday dates from (today + weeks_ahead*7 + extra_days) down to today."""
    today = datetime.now().date()
    furthest_date = today + timedelta(weeks=weeks_ahead, days=extra_days)

    dates = []
    current_date = today

    # Generate all dates from today to furthest_date
    while current_date <= furthest_date:
        if current_date.weekday() in [2, 3]:  # Wednesday (2) or Thursday (3)
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    # Sort from furthest to closest (so latest dates get tried first)
    dates.sort(reverse=True)
    return dates

def load_booking_config():
    """Load booking configuration from JSON file"""
    try:
        config_path = Path('config/booking_config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Failed to load booking config: {e}")
        return {}

def save_booking_config(config_data):
    """Save booking configuration to JSON file"""
    try:
        config_path = Path('config/booking_config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save booking config: {e}")
        return False

def update_bot_status(status: Dict[str, Any]):
    """Update bot status for web interface"""
    # This would be called by the web interface to update status
    # For now, just print it
    print(f"STATUS_UPDATE: {status}")

async def run_web_mode():
    """Run the bot in web-compatible mode"""
    logger = WebBotLogger()

    try:
        logger.info("Starting SpaceIQ Multi-Date Booking Bot (Web Mode)")
        logger.info(f"Mode: Auto + Headless + Unattended")
        logger.info(f"Working Directory: {Path.cwd()}")

        # Load configuration
        config = load_booking_config()
        if not config:
            logger.error("No configuration found. Please configure your bot first.")
            return False

        # Get user-specific auth file if available
        user_auth_file = os.getenv('USER_AUTH_FILE')
        if user_auth_file and Path(user_auth_file).exists():
            # Copy user-specific auth to default location
            import shutil
            shutil.copy2(user_auth_file, Config.AUTH_STATE_FILE)
            logger.info(f"Using user authentication file: {user_auth_file}")

        # Check for existing session
        auth_exists = Config.AUTH_STATE_FILE.exists()
        if not auth_exists:
            logger.error("No authentication session found. Please authenticate first.")
            return False

        # Load and decrypt session
        session_data = load_encrypted_session(Config.AUTH_STATE_FILE)
        if not session_data:
            logger.error("Could not load/decrypt authentication session.")
            return False

        logger.info("Authentication session loaded successfully")

        # Run the booking workflow
        logger.info("Starting booking workflow...")

        # Pass the logger to the booking workflow instead of Rich
        results = await run_multi_date_booking(
            config=config,
            auto_mode=True,
            headless=True,
            unattended=True,
            web_logger=logger
        )

        if results:
            logger.info(f"Booking completed. Results: {results}")

            # Update configuration with results if dates were processed
            if results.get('dates_processed'):
                save_booking_config(config)
                logger.info("Configuration updated with processed dates")

        return results

    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def generate_auto_dates() -> List[str]:
    """Generate dates automatically for next few weeks"""
    return generate_wednesday_thursday_dates(weeks_ahead=4, extra_days=1)

async def main():
    """Main entry point"""
    # Check command line arguments
    auto_mode = '--auto' in sys.argv
    headless_mode = '--headless' in sys.argv
    unattended_mode = '--unattended' in sys.argv

    # For web interface, always run in web mode
    logger = WebBotLogger()
    logger.info("SpaceIQ Multi-Date Booking Bot - Web Interface Mode")

    try:
        if auto_mode:
            # Generate dates automatically for auto mode
            config = load_booking_config()

            if not config.get('dates_to_try'):
                # If no dates configured, generate them automatically
                auto_dates = generate_auto_dates()
                config['dates_to_try'] = auto_dates
                save_booking_config(config)
                logger.info(f"Generated {len(auto_dates)} dates automatically")

            return await run_web_mode()
        else:
            # Manual mode
            return await run_web_mode()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return False
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    exit_code = 0 if asyncio.run(main()) else 1
    sys.exit(exit_code)