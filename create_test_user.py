#!/usr/bin/env python
"""
Create a test user for testing the bot functionality
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import app, db
from models import User, BotConfig, BotInstance

def create_test_user():
    """Create a test user with default configuration"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            print("Test user 'testuser' already exists")
            return existing_user

        # Create test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')

        db.session.add(user)
        db.session.flush()  # Get the user ID

        # Create default bot configuration with some test dates
        from datetime import datetime, timedelta
        today = datetime.now().date()
        dates = []
        for i in range(14):  # 2 weeks
            date = today + timedelta(days=i)
            if date.weekday() in [2, 3]:  # Wednesday=2, Thursday=3
                dates.append(date.strftime('%Y-%m-%d'))

        bot_config = BotConfig(
            user_id=user.id,
            building='LC',
            floor='2',
            desk_preferences='{"prefix": "2.24", "priority_ranges": []}',
            dates_to_try=str(dates).replace("'", '"'),  # Convert to JSON-like string
            booking_days='{"weekdays": [2, 3]}',  # Wednesday=2, Thursday=3
            wait_times='{"rounds_1_to_5": {"seconds": 60}, "rounds_6_to_15": {"seconds": 120}, "rounds_16_plus": {"seconds": 180}}',
            browser_restart='{"restart_every_n_rounds": 50}'
        )
        db.session.add(bot_config)

        # Create bot instance
        bot_instance = BotInstance(user_id=user.id, status='stopped')
        db.session.add(bot_instance)

        db.session.commit()

        print(f"Test user 'testuser' created successfully!")
        print(f"Username: testuser")
        print(f"Password: testpass123")
        print(f"Dates configured: {len(dates)} dates")
        print(f"Building: LC, Floor: 2, Desk prefix: 2.24")

        return user

if __name__ == '__main__':
    create_test_user()