"""
Database Models for Multi-User SpaceIQ Bot Platform
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User account model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    spaceiq_session = db.relationship('SpaceIQSession', backref='user', uselist=False, cascade='all, delete-orphan')
    bot_config = db.relationship('BotConfig', backref='user', uselist=False, cascade='all, delete-orphan')
    bot_instance = db.relationship('BotInstance', backref='user', uselist=False, cascade='all, delete-orphan')
    booking_history = db.relationship('BookingHistory', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class SpaceIQSession(db.Model):
    """Stores encrypted SpaceIQ authentication session"""
    __tablename__ = 'spaceiq_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    session_data = db.Column(db.Text, nullable=False)  # Encrypted JSON
    authenticated_as = db.Column(db.String(120))  # SpaceIQ username
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_valid = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<SpaceIQSession user={self.user_id} auth_as={self.authenticated_as}>'


class BotConfig(db.Model):
    """Per-user bot configuration"""
    __tablename__ = 'bot_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # SpaceIQ configuration
    building = db.Column(db.String(10), default='LC')
    floor = db.Column(db.String(10), default='2')

    # Desk preferences (stored as JSON)
    desk_preferences = db.Column(db.Text, nullable=False, default='{}')

    # Dates to try (stored as JSON array)
    dates_to_try = db.Column(db.Text, nullable=False, default='[]')

    # Booking days (stored as JSON)
    booking_days = db.Column(db.Text, nullable=False, default='{"weekdays": [2, 3]}')

    # Blacklist dates - dates to exclude from auto-calculation (stored as JSON array)
    # Supports individual dates and ranges: ["2025-12-25", "2025-01-01:2025-01-07"]
    blacklist_dates = db.Column(db.Text, nullable=False, default='[]')

    # Wait times (stored as JSON)
    wait_times = db.Column(db.Text, nullable=False, default='{}')

    # Browser restart configuration
    browser_restart = db.Column(db.Text, nullable=False, default='{"restart_every_n_rounds": 50}')

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_desk_preferences(self):
        """Get desk preferences as dict"""
        return json.loads(self.desk_preferences)

    def set_desk_preferences(self, prefs):
        """Set desk preferences from dict"""
        self.desk_preferences = json.dumps(prefs)

    def get_dates_to_try(self):
        """Get dates as list"""
        return json.loads(self.dates_to_try)

    def set_dates_to_try(self, dates):
        """Set dates from list"""
        self.dates_to_try = json.dumps(dates)

    def get_booking_days(self):
        """Get booking days as dict"""
        return json.loads(self.booking_days)

    def set_booking_days(self, days):
        """Set booking days from dict"""
        self.booking_days = json.dumps(days)

    def get_blacklist_dates(self):
        """Get blacklist dates as list"""
        return json.loads(self.blacklist_dates)

    def set_blacklist_dates(self, dates):
        """Set blacklist dates from list"""
        self.blacklist_dates = json.dumps(dates)

    def get_wait_times(self):
        """Get wait times as dict"""
        if self.wait_times:
            return json.loads(self.wait_times)
        return {
            "rounds_1_to_5": {"seconds": 60},
            "rounds_6_to_15": {"seconds": 120},
            "rounds_16_plus": {"seconds": 180}
        }

    def set_wait_times(self, times):
        """Set wait times from dict"""
        self.wait_times = json.dumps(times)

    def get_browser_restart(self):
        """Get browser restart config"""
        return json.loads(self.browser_restart)

    def set_browser_restart(self, config):
        """Set browser restart config"""
        self.browser_restart = json.dumps(config)

    def to_dict(self):
        """Convert to dictionary for JSON API"""
        return {
            'building': self.building,
            'floor': self.floor,
            'desk_preferences': self.get_desk_preferences(),
            'dates_to_try': self.get_dates_to_try(),
            'booking_days': self.get_booking_days(),
            'blacklist_dates': self.get_blacklist_dates(),
            'wait_times': self.get_wait_times(),
            'browser_restart': self.get_browser_restart()
        }

    def __repr__(self):
        return f'<BotConfig user={self.user_id}>'


class BotInstance(db.Model):
    """Tracks running bot instances"""
    __tablename__ = 'bot_instances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    status = db.Column(db.String(20), default='stopped')  # running, stopped, error
    started_at = db.Column(db.DateTime)
    stopped_at = db.Column(db.DateTime)

    # Runtime stats
    current_round = db.Column(db.Integer, default=0)
    successful_bookings = db.Column(db.Integer, default=0)
    failed_attempts = db.Column(db.Integer, default=0)
    current_activity = db.Column(db.String(200))  # e.g., "Booking 2025-11-13 - Attempt #1"

    # Process info
    pid = db.Column(db.Integer)

    # Error info
    error_message = db.Column(db.Text)

    # Logs (recent only, stored as JSON array)
    recent_logs = db.Column(db.Text, default='[]')

    def get_logs(self):
        """Get logs as list"""
        return json.loads(self.recent_logs)

    def add_log(self, message, level='info'):
        """Add a log entry"""
        logs = self.get_logs()
        logs.append({
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message
        })
        # Keep only last 100 logs
        if len(logs) > 100:
            logs = logs[-100:]
        self.recent_logs = json.dumps(logs)

    def clear_logs(self):
        """Clear all logs"""
        self.recent_logs = '[]'

    def set_activity(self, activity):
        """Set current activity"""
        self.current_activity = activity
        self.add_log(activity)

    def to_dict(self):
        """Convert to dictionary for JSON API"""
        uptime = None
        if self.started_at and self.status == 'running':
            uptime = int((datetime.utcnow() - self.started_at).total_seconds())

        return {
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'current_round': self.current_round,
            'successful_bookings': self.successful_bookings,
            'failed_attempts': self.failed_attempts,
            'current_activity': self.current_activity,
            'uptime': uptime,
            'error': self.error_message,
            'logs': self.get_logs()
        }

    def __repr__(self):
        return f'<BotInstance user={self.user_id} status={self.status}>'


class BookingHistory(db.Model):
    """Booking history for each user"""
    __tablename__ = 'booking_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    desk_number = db.Column(db.String(20))
    status = db.Column(db.String(20), nullable=False)  # success, failed, pending

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Additional info
    round_number = db.Column(db.Integer)
    error_message = db.Column(db.Text)

    def to_dict(self):
        """Convert to dictionary for JSON API"""
        return {
            'id': self.id,
            'date': self.date,
            'desk_number': self.desk_number,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'round_number': self.round_number,
            'error_message': self.error_message
        }

    def __repr__(self):
        return f'<BookingHistory user={self.user_id} date={self.date} status={self.status}>'


class VNCSession(db.Model):
    """Tracks active VNC sessions for SpaceIQ authentication"""
    __tablename__ = 'vnc_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    vnc_port = db.Column(db.Integer, nullable=False)
    websocket_port = db.Column(db.Integer, nullable=False)
    display_number = db.Column(db.Integer, nullable=False)

    status = db.Column(db.String(20), default='active')  # active, completed, failed

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Process IDs for cleanup
    xvfb_pid = db.Column(db.Integer)
    vnc_pid = db.Column(db.Integer)
    ws_pid = db.Column(db.Integer)
    browser_pid = db.Column(db.Integer)

    def __repr__(self):
        return f'<VNCSession user={self.user_id} port={self.websocket_port}>'
