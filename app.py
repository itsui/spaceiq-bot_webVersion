"""
SpaceIQ Multi-User Bot Platform
Main Flask Application
"""

import os
import sys
import json
import secrets
from pathlib import Path
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Add root to path
sys.path.insert(0, str(Path(__file__).parent))

from models import db, User, BotConfig, SpaceIQSession, BotInstance, BookingHistory
from bot_manager import BotManager
from spaceiq_auth_capture import AuthCaptureManager
from src.utils.session_persistence import save_session_to_database

# Import migration manager
from migrate_database import run_all_migrations

# Initialize Flask app
app = Flask(__name__)

# Apply ProxyFix middleware for Cloudflare/reverse proxy support
# This ensures Flask correctly handles X-Forwarded-* headers from Cloudflare
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Trust 1 proxy for X-Forwarded-For
    x_proto=1,    # Trust 1 proxy for X-Forwarded-Proto (HTTPS detection)
    x_host=1,     # Trust 1 proxy for X-Forwarded-Host
    x_prefix=1    # Trust 1 proxy for X-Forwarded-Prefix
)

# Configuration
# Generate a strong secret key if not provided
# Run this to generate a key: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'change-this-to-a-random-secret-key':
    raise ValueError(
        "You must set a strong SECRET_KEY in .env file!\n"
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "Then add to .env file: SECRET_KEY=<generated_key>"
    )

app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spaceiq_multiuser.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session security configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)  # Sessions expire after 12 hours

# LOCAL_MODE: Allow HTTP cookies for localhost (set by _RUN_LOCAL.bat)
# When running locally, we don't have HTTPS so cookies must work over HTTP
local_mode = os.getenv('LOCAL_MODE', 'false').lower() == 'true'
app.config['SESSION_COOKIE_SECURE'] = not local_mode  # False for localhost, True for production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

if local_mode:
    # Relax rate limits for local use
    app.config['RATELIMIT_ENABLED'] = False

# Security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Initialize database
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Initialize Bot Manager
bot_manager = BotManager(app)

# Initialize Auth Capture Manager
auth_capture_manager = AuthCaptureManager(app)

# Setup logging
def setup_logging():
    """Setup application logging"""
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler with rotation
    log_file = logs_dir / 'app.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

setup_logging()
logger = logging.getLogger(__name__)

# Suppress flask-limiter INFO spam (only show warnings and errors)
logging.getLogger('flask-limiter').setLevel(logging.WARNING)


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))


def is_safe_url(target):
    """
    Validate that a redirect URL is safe (same host).

    Prevents open redirect vulnerabilities by ensuring the target
    URL is relative or points to the same host as the application.

    Args:
        target: URL to validate

    Returns:
        True if URL is safe to redirect to, False otherwise
    """
    from urllib.parse import urlparse, urljoin

    # Get the reference URL (our app)
    ref_url = urlparse(request.host_url)

    # Parse the target URL (make it absolute if relative)
    test_url = urlparse(urljoin(request.host_url, target))

    # Check: scheme must be http/https AND netloc must match (same host)
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=['POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return render_template('register.html')

        # Check for common weak passwords
        weak_passwords = ['password', '12345678', 'qwerty', 'admin', 'letmein']
        if password.lower() in weak_passwords:
            flash('Password is too common. Please choose a stronger password.', 'danger')
            return render_template('register.html')

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')

        # Create user (open registration - Supabase validation removed)
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Auto-generate dates for next 4 weeks (Tuesday and Wednesday)
        today = datetime.now().date()
        dates = []
        for i in range(28):  # 4 weeks
            date = today + timedelta(days=i)
            if date.weekday() in [1, 2]:  # Tuesday=1, Wednesday=2
                dates.append(date.strftime('%Y-%m-%d'))

        # Create default bot configuration with auto-generated dates
        bot_config = BotConfig(
            user_id=user.id,
            building='LC',
            floor='2',
            desk_preferences='{"prefix": "2.24", "priority_ranges": []}',
            dates_to_try=json.dumps(dates),
            booking_days='{"weekdays": [1, 2]}',
            wait_times='{"rounds_1_to_5": {"seconds": 60}, "rounds_6_to_15": {"seconds": 120}, "rounds_16_plus": {"seconds": 180}}',
            browser_restart='{"restart_every_n_rounds": 50}'
        )
        db.session.add(bot_config)

        # Create bot instance
        bot_instance = BotInstance(user_id=user.id, status='stopped')
        db.session.add(bot_instance)

        db.session.commit()

        logger.info(f"New user registered: {username}")
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=['POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter username and password', 'danger')
            return render_template('login_multi.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            logger.info(f"User logged in: {username}")

            # Validate redirect URL to prevent open redirect attacks
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login_multi.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logger.info(f"User logged out: {current_user.username}")
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# ============================================================================
# MAIN DASHBOARD ROUTES
# ============================================================================

@app.route('/')
def dashboard():
    """Main dashboard - no login required for local single-user mode"""
    return render_template('dashboard.html', user=current_user)


@app.route('/config')
@login_required
def config_page():
    """Configuration page"""
    return render_template('config_multi.html', user=current_user)


@app.route('/history')
@login_required
def history_page():
    """Booking history page"""
    return render_template('history_multi.html', user=current_user)


# ============================================================================
# API ENDPOINTS - BOT CONTROL
# ============================================================================

@app.route('/api/bot/start', methods=['POST'])
@login_required
@limiter.exempt
def api_start_bot():
    """Start bot for current user"""
    try:
        success, message = bot_manager.start_bot(current_user.id)
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error starting bot for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/bot/stop', methods=['POST'])
@login_required
@limiter.exempt
def api_stop_bot():
    """Stop bot for current user"""
    try:
        success, message = bot_manager.stop_bot(current_user.id)
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error stopping bot for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/bot/status')
@login_required
@limiter.exempt  # Exempt from rate limiting - used for real-time updates
def api_bot_status():
    """Get bot status for current user"""
    try:
        from src.utils.live_logger import get_live_logger

        # Get bot status from database
        status = bot_manager.get_bot_status(current_user.id)
        if status:
            # Replace database logs with live logs (which have the operational messages)
            live_logger = get_live_logger(current_user.id)
            live_logs = live_logger.get_recent_logs(limit=100)
            status['logs'] = live_logs
            return jsonify(status)
        else:
            # Return default stopped status
            return jsonify({
                'status': 'stopped',
                'started_at': None,
                'stopped_at': None,
                'current_round': 0,
                'successful_bookings': 0,
                'failed_attempts': 0,
                'uptime': None,
                'error': None,
                'logs': []
            })
    except Exception as e:
        logger.error(f"Error getting bot status for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ENDPOINTS - CONFIGURATION
# ============================================================================

@app.route('/api/config')
@login_required
@limiter.exempt
def api_get_config():
    """Get bot configuration for current user"""
    try:
        bot_config = BotConfig.query.filter_by(user_id=current_user.id).first()
        if bot_config:
            return jsonify(bot_config.to_dict())
        else:
            return jsonify({'error': 'Configuration not found'}), 404
    except Exception as e:
        logger.error(f"Error getting config for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/uk-holidays')
@login_required
@limiter.exempt
def api_get_uk_holidays():
    """Get UK bank holidays for the next 29 days"""
    try:
        from datetime import date, timedelta
        from src.utils.date_calculator import get_uk_bank_holidays

        today = date.today()
        end_date = today + timedelta(days=29)

        holidays = get_uk_bank_holidays(today, end_date)

        return jsonify({
            'success': True,
            'holidays': list(holidays)
        })
    except Exception as e:
        logger.error(f"Error getting UK holidays: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
@login_required
@limiter.exempt
def api_update_config():
    """Update bot configuration for current user"""
    try:
        data = request.get_json()

        bot_config = BotConfig.query.filter_by(user_id=current_user.id).first()
        if not bot_config:
            return jsonify({'success': False, 'message': 'Configuration not found'}), 404

        # Update configuration
        if 'building' in data:
            bot_config.building = data['building']
        if 'floor' in data:
            bot_config.floor = data['floor']
        if 'desk_preferences' in data:
            bot_config.set_desk_preferences(data['desk_preferences'])
        if 'dates_to_try' in data:
            bot_config.set_dates_to_try(data['dates_to_try'])
        if 'booking_days' in data:
            bot_config.set_booking_days(data['booking_days'])
        if 'blacklist_dates' in data:
            bot_config.set_blacklist_dates(data['blacklist_dates'])
        if 'locked_desks' in data:
            bot_config.set_locked_desks(data['locked_desks'])
        if 'auto_ignore_uk_holidays' in data:
            bot_config.auto_ignore_uk_holidays = data['auto_ignore_uk_holidays']
        if 'wait_times' in data:
            bot_config.set_wait_times(data['wait_times'])
        if 'browser_restart' in data:
            bot_config.set_browser_restart(data['browser_restart'])

        # ALWAYS recalculate dates to keep them fresh (preserves manual dates)
        updated_dates = None
        if True:  # Always recalculate
            from src.utils.date_calculator import update_user_dates
            updated_dates = update_user_dates(bot_config, preserve_manual=True)
            logger.info(f"Auto-calculated {len(updated_dates)} dates for user {current_user.username}")

        db.session.commit()

        logger.info(f"Configuration updated for user {current_user.username}")

        response = {
            'success': True,
            'message': 'Configuration updated successfully'
        }

        # Return updated dates if recalculated
        if updated_dates is not None:
            response['dates_to_try'] = updated_dates
            response['message'] += f' ({len(updated_dates)} dates auto-calculated)'

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error updating config for user {current_user.id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ============================================================================
# API ENDPOINTS - SPACEIQ AUTHENTICATION
# ============================================================================

@app.route('/api/spaceiq/auth/start', methods=['POST'])
@login_required
def api_start_spaceiq_auth():
    """Start SpaceIQ authentication for current user"""
    try:
        success, message = auth_capture_manager.start_capture(current_user.id)
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error starting SpaceIQ auth for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/spaceiq/auth/status')
@login_required
@limiter.exempt
def api_spaceiq_auth_status():
    """Get SpaceIQ authentication status for current user"""
    try:
        # Check if user has a valid persistent profile session
        from pathlib import Path
        profile_dir = Path("playwright") / ".auth" / "profiles" / f"user_{current_user.id}"

        # Check if persistent profile exists (has cookies)
        has_profile = profile_dir.exists() and any(profile_dir.iterdir())

        # Check database session
        spaceiq_session = SpaceIQSession.query.filter_by(user_id=current_user.id).first()
        has_db_session = spaceiq_session and spaceiq_session.is_valid

        # Verify that session data can actually be decrypted if it exists
        if has_db_session and spaceiq_session.session_data:
            try:
                from src.utils.auth_encryption import decrypt_data
                # Try to decrypt the session data to verify it's usable
                decrypted = decrypt_data(spaceiq_session.session_data)
                json.loads(decrypted)  # Verify it's valid JSON
            except Exception as e:
                # Decryption failed - mark session as invalid and clean up
                logger.warning(f"Session decryption failed for user {current_user.id}: {e}")
                spaceiq_session.is_valid = False
                db.session.commit()
                has_db_session = False

                # Also delete the persistent profile directory since session is corrupted
                if has_profile and profile_dir.exists():
                    try:
                        import shutil
                        shutil.rmtree(profile_dir)
                        logger.info(f"Deleted corrupted profile directory for user {current_user.id}")
                        has_profile = False
                    except Exception as cleanup_error:
                        logger.error(f"Failed to delete profile directory: {cleanup_error}")

        if has_profile and has_db_session:
            return jsonify({
                'is_authenticated': True,
                'authenticated': True,
                'status': 'valid',
                'authenticated_as': spaceiq_session.authenticated_as or current_user.username,
                'method': 'persistent_profile'
            })
        elif has_profile or has_db_session:
            return jsonify({
                'is_authenticated': True,
                'authenticated': True,
                'status': 'partial',
                'authenticated_as': spaceiq_session.authenticated_as if spaceiq_session else current_user.username,
                'message': 'Session may need refresh'
            })
        else:
            return jsonify({
                'is_authenticated': False,
                'authenticated': False,
                'status': 'none'
            })
    except Exception as e:
        logger.error(f"Error getting SpaceIQ auth status for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API ENDPOINTS - BOOKING HISTORY
# ============================================================================

@app.route('/api/history')
@login_required
@limiter.exempt
def api_get_history():
    """Get booking history for current user"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status_filter = request.args.get('status')

        # Build query
        query = BookingHistory.query.filter_by(user_id=current_user.id)

        if status_filter:
            query = query.filter_by(status=status_filter)

        # Get total count
        total = query.count()

        # Get paginated results
        history = query.order_by(BookingHistory.timestamp.desc()) \
                       .limit(limit) \
                       .offset(offset) \
                       .all()

        return jsonify({
            'total': total,
            'limit': limit,
            'offset': offset,
            'history': [h.to_dict() for h in history]
        })

    except Exception as e:
        logger.error(f"Error getting history for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/clear-failed', methods=['POST'])
@login_required
def api_clear_failed_history():
    """Clear old failed booking history entries for current user"""
    try:
        # Delete all failed entries for current user
        deleted_count = BookingHistory.query.filter_by(
            user_id=current_user.id,
            status='failed'
        ).delete()

        db.session.commit()

        logger.info(f"Cleared {deleted_count} failed history entries for user {current_user.id}")

        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} failed history entries',
            'deleted_count': deleted_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing history for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history/remove-duplicates', methods=['POST'])
@login_required
def api_remove_duplicate_history():
    """Remove duplicate booking history entries for current user"""
    try:
        # Get all bookings for current user
        all_bookings = BookingHistory.query.filter_by(user_id=current_user.id).order_by(BookingHistory.id.asc()).all()

        # Track seen combinations and IDs to delete
        seen = set()
        ids_to_delete = []

        for booking in all_bookings:
            # Create unique key from date + desk + status
            key = (booking.date, booking.desk_number, booking.status)

            if key in seen:
                # Duplicate found - mark for deletion
                ids_to_delete.append(booking.id)
            else:
                # First occurrence - keep it
                seen.add(key)

        # Delete duplicates
        if ids_to_delete:
            BookingHistory.query.filter(BookingHistory.id.in_(ids_to_delete)).delete(synchronize_session=False)
            db.session.commit()

        deleted_count = len(ids_to_delete)
        logger.info(f"Removed {deleted_count} duplicate history entries for user {current_user.id}")

        return jsonify({
            'success': True,
            'message': f'Removed {deleted_count} duplicate entries',
            'deleted_count': deleted_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing duplicates for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/live-logs')
@login_required
@limiter.exempt
def api_get_live_logs():
    """Get live logs for current user (UI logs only)"""
    try:
        from src.utils.live_logger import get_live_logger

        # Get query parameters
        limit = request.args.get('limit', 100, type=int)

        # Get live logger for current user
        live_logger = get_live_logger(current_user.id)

        # Get recent logs
        logs = live_logger.get_recent_logs(limit)

        return jsonify({
            'success': True,
            'logs': logs,
            'limit': limit,
            'total': len(logs)
        })

    except Exception as e:
        logger.error(f"Error fetching live logs for user {current_user.id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'logs': []
        }), 500


# ============================================================================
# BROWSER STREAMING FOR REMOTE AUTHENTICATION
# ============================================================================

from browser_stream_manager import stream_manager

@app.route('/auth/browser-stream')
@login_required
def browser_stream_page():
    """Display the browser streaming page for authentication"""
    return render_template('browser_stream.html')


@app.route('/auth/auto')
@login_required
def auto_auth_page():
    """Display the automated SSO authentication page (NEW - recommended method)"""
    return render_template('auto_auth.html')


@app.route('/api/auth/start-stream', methods=['POST'])
@login_required
def api_start_browser_stream():
    """Start a browser streaming session"""
    try:
        # Handle both JSON and form data
        if request.is_json:
            target_url = request.json.get('url', 'https://main.spaceiq.com/login')
        else:
            target_url = 'https://main.spaceiq.com/login'

        success = stream_manager.start_session(current_user.id, target_url)

        if success:
            return jsonify({
                'success': True,
                'stream_url': f'/api/auth/stream-viewport',
                'message': 'Browser stream started'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start browser stream'
            }), 500

    except Exception as e:
        logger.error(f"Error starting browser stream: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/auth/stream-viewport')
@login_required
def api_stream_viewport():
    """Stream browser viewport as HTML page with auto-refreshing screenshot"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            html, body {
                width: 100%;
                height: 100%;
                overflow: hidden;
                background: #1a1a1a;
            }
            #viewport {
                width: 100%;
                height: 100%;
                object-fit: contain;
                display: block;
            }
            #overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                cursor: crosshair;
            }
            .click-indicator {
                position: absolute;
                width: 40px;
                height: 40px;
                border: 3px solid #667eea;
                border-radius: 50%;
                pointer-events: none;
                animation: clickPulse 0.6s ease-out;
                transform: translate(-50%, -50%);
            }
            @keyframes clickPulse {
                0% {
                    transform: translate(-50%, -50%) scale(0.3);
                    opacity: 1;
                    border-width: 4px;
                }
                100% {
                    transform: translate(-50%, -50%) scale(1);
                    opacity: 0;
                    border-width: 1px;
                }
            }
            #status {
                position: absolute;
                bottom: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                font-family: monospace;
            }
        </style>
    </head>
    <body>
        <img id="viewport" alt="Browser viewport" />
        <div id="overlay"></div>
        <div id="status">Ready</div>
        <script>
            const viewport = document.getElementById('viewport');
            const overlay = document.getElementById('overlay');
            const statusDiv = document.getElementById('status');

            function setStatus(text, duration = 2000) {
                statusDiv.textContent = text;
                statusDiv.style.opacity = '1';
                if (duration > 0) {
                    setTimeout(() => {
                        statusDiv.style.opacity = '0.3';
                    }, duration);
                }
            }

            function showClickFeedback(x, y) {
                const indicator = document.createElement('div');
                indicator.className = 'click-indicator';
                indicator.style.left = x + 'px';
                indicator.style.top = y + 'px';
                document.body.appendChild(indicator);
                setTimeout(() => indicator.remove(), 600);
            }

            // Update screenshot with proper memory management and sequence tracking
            let isUpdating = false;
            let lastScreenshotHash = '';
            let requestSequence = 0;
            let lastAppliedSequence = 0;

            async function updateScreenshot() {
                // Prevent overlapping requests
                if (isUpdating) return;
                isUpdating = true;

                // Track this request's sequence number
                const thisSequence = ++requestSequence;

                try {
                    const response = await fetch('/api/auth/screenshot', {
                        cache: 'no-store'  // Prevent browser caching
                    });
                    if (!response.ok) {
                        console.error('Screenshot fetch failed:', response.status);
                        return;
                    }
                    const data = await response.json();

                    // Only apply screenshots that are newer than what we've already shown
                    // This prevents out-of-order screenshots from causing UI to jump backwards
                    if (thisSequence <= lastAppliedSequence) {
                        console.debug(`Ignoring out-of-order screenshot (seq ${thisSequence} <= ${lastAppliedSequence})`);
                        return;
                    }

                    if (data.success && data.screenshot) {
                        // Update sequence first to prevent gaps
                        lastAppliedSequence = thisSequence;

                        // Only update image if screenshot actually changed to reduce DOM operations
                        if (data.screenshot !== lastScreenshotHash) {
                            viewport.src = 'data:image/jpeg;base64,' + data.screenshot;
                            lastScreenshotHash = data.screenshot;
                        }
                    } else {
                        console.warn('No screenshot data:', data);
                    }
                } catch (e) {
                    console.error('Screenshot update failed:', e);
                } finally {
                    isUpdating = false;
                }
            }

            setInterval(updateScreenshot, 200);  // Update every 200ms for fast feedback
            updateScreenshot();
            setStatus('Stream active', 0);

            // Keystroke buffering for faster typing
            let typeBuffer = '';
            let typeTimeout = null;

            function flushTypeBuffer() {
                if (typeBuffer.length > 0) {
                    const textToSend = typeBuffer;
                    typeBuffer = '';
                    // Fire-and-forget - don't await
                    fetch('/api/auth/type', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: textToSend })
                    }).catch(e => console.error('Type error:', e));
                }
            }

            function bufferKeystroke(char) {
                typeBuffer += char;
                clearTimeout(typeTimeout);
                // Send buffered input after 30ms of no typing (or when buffer gets large)
                if (typeBuffer.length > 15) {
                    flushTypeBuffer();
                } else {
                    typeTimeout = setTimeout(flushTypeBuffer, 30);  // Faster feedback
                }
            }

            // Forward clicks with proper scaling - OPTIMIZED: fire-and-forget
            overlay.addEventListener('click', (e) => {
                const rect = viewport.getBoundingClientRect();

                // Show visual feedback immediately
                showClickFeedback(e.clientX, e.clientY);

                // Account for object-fit: contain scaling
                const imgAspect = 640 / 400;  // Browser viewport aspect ratio (low res for speed)
                const displayAspect = rect.width / rect.height;

                let displayWidth = rect.width;
                let displayHeight = rect.height;
                let offsetX = 0;
                let offsetY = 0;

                if (displayAspect > imgAspect) {
                    // Letterbox (black bars on sides)
                    displayWidth = rect.height * imgAspect;
                    offsetX = (rect.width - displayWidth) / 2;
                } else {
                    // Pillarbox (black bars on top/bottom)
                    displayHeight = rect.width / imgAspect;
                    offsetY = (rect.height - displayHeight) / 2;
                }

                const x = ((e.clientX - rect.left - offsetX) / displayWidth) * 640;
                const y = ((e.clientY - rect.top - offsetY) / displayHeight) * 400;

                // Only send click if within bounds
                if (x >= 0 && x <= 640 && y >= 0 && y <= 400) {
                    setStatus(`Click: (${Math.round(x)}, ${Math.round(y)})`, 800);
                    // Fire-and-forget - don't wait for response
                    fetch('/api/auth/click', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ x: Math.round(x), y: Math.round(y) })
                    }).then(response => {
                        if (response.ok) {
                            setStatus(`✓ Clicked`, 500);
                        }
                    }).catch(err => {
                        console.error('Click error:', err);
                    });
                } else {
                    setStatus('Click outside viewport', 1000);
                }
            });

            // Forward keyboard - OPTIMIZED: buffered typing
            document.addEventListener('keypress', (e) => {
                // Buffer regular characters for batched sending
                if (e.key.length === 1) {
                    bufferKeystroke(e.key);
                    setStatus(`Typing...`, 500);
                }
            });

            document.addEventListener('keydown', (e) => {
                // Special keys: flush buffer first, then send the special key
                if (e.key === 'Enter' || e.key === 'Tab' || e.key === 'Backspace') {
                    e.preventDefault();

                    // Flush any buffered text first
                    flushTypeBuffer();

                    // Then send special key (fire-and-forget)
                    setStatus(`Press: ${e.key}`, 500);
                    fetch('/api/auth/press', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: e.key })
                    }).catch(e => console.error('Press error:', e));
                }
            });
        </script>
    </body>
    </html>
    '''
    return html


@app.route('/api/auth/screenshot')
@login_required
@limiter.exempt
def api_get_screenshot():
    """Get current browser screenshot"""
    try:
        session = stream_manager.get_session(current_user.id)
        if not session:
            logger.warning(f"No session found for user {current_user.id}")
            return jsonify({'error': 'No active session', 'success': False}), 404

        screenshot = session.get_screenshot()

        if not screenshot:
            logger.warning(f"No screenshot returned for user {current_user.id}")
            return jsonify({'success': False, 'screenshot': None})

        return jsonify({
            'success': True,
            'screenshot': screenshot
        })

    except Exception as e:
        logger.error(f"Screenshot error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/click', methods=['POST'])
@login_required
def api_browser_click():
    """Forward click to browser"""
    try:
        data = request.json
        session = stream_manager.get_session(current_user.id)
        if session:
            session.click(int(data['x']), int(data['y']))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/type', methods=['POST'])
@login_required
def api_browser_type():
    """Forward typing to browser"""
    try:
        data = request.json
        session = stream_manager.get_session(current_user.id)
        if session:
            session.type_text(data['text'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/press', methods=['POST'])
@login_required
def api_browser_press():
    """Forward key press to browser"""
    try:
        data = request.json
        session = stream_manager.get_session(current_user.id)
        if session:
            session.press_key(data['key'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/check-stream-status')
@login_required
@limiter.exempt
def api_check_stream_status():
    """Check authentication status"""
    try:
        session = stream_manager.get_session(current_user.id)
        if not session:
            return jsonify({
                'authenticated': False,
                'url': None
            })

        return jsonify({
            'authenticated': session.authenticated,
            'url': session.current_url
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/stop-stream', methods=['POST'])
@login_required
def api_stop_browser_stream():
    """Stop browser streaming session"""
    try:
        session = stream_manager.get_session(current_user.id)

        # Save session if authenticated
        if session and session.authenticated:
            # Save to user's SpaceIQ session in database
            from src.utils.auth_encryption import encrypt_data
            import tempfile
            import os

            # Save to temp file first - use mkstemp to create file
            temp_fd, temp_path_str = tempfile.mkstemp(suffix='.json')
            os.close(temp_fd)  # Close fd, we'll use the path
            temp_path = Path(temp_path_str)

            success = session.save_session(str(temp_path))

            if not success:
                temp_path.unlink()
                logger.warning("Failed to save session on stop - session not saved to database")
                stream_manager.stop_session(current_user.id)
                return jsonify({
                    'success': True,
                    'message': 'Stream stopped but session was not saved (authentication may have failed)'
                })

            # Validate file has content
            file_size = temp_path.stat().st_size
            if file_size == 0:
                logger.error("Session file is empty on stop")
                temp_path.unlink()
                stream_manager.stop_session(current_user.id)
                return jsonify({
                    'success': True,
                    'message': 'Stream stopped but session is empty - please authenticate first'
                })

            # Read and save to database
            with open(temp_path, 'r') as f:
                session_data_json = f.read()

            # Parse JSON and save using shared utility
            session_data = json.loads(session_data_json)
            save_session_to_database(current_user.id, session_data)

            # Cleanup
            temp_path.unlink()

            logger.info(f"Session saved for user {current_user.id}")

        stream_manager.stop_session(current_user.id)

        return jsonify({
            'success': True,
            'message': 'Stream stopped and session saved' if session and session.authenticated else 'Stream stopped'
        })

    except Exception as e:
        logger.error(f"Error stopping stream: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/save-stream-session', methods=['POST'])
@login_required
def api_save_stream_session():
    """Save authenticated session from browser stream"""
    try:
        session = stream_manager.get_session(current_user.id)

        if not session:
            return jsonify({'success': False, 'error': 'No active session'}), 400

        if not session.authenticated:
            return jsonify({'success': False, 'error': 'Not authenticated yet'}), 400

        # Save session to database
        from src.utils.auth_encryption import encrypt_data
        import tempfile
        import os

        # Save to temp file first - use mkstemp to create file
        temp_fd, temp_path_str = tempfile.mkstemp(suffix='.json')
        os.close(temp_fd)  # Close fd, we'll use the path
        temp_path = Path(temp_path_str)

        success = session.save_session(str(temp_path))

        if not success:
            # Clean up temp file
            try:
                temp_path.unlink()
            except:
                pass
            return jsonify({'success': False, 'error': 'Failed to save session'}), 500

        # CRITICAL: Add retry logic with delays to ensure file is fully written
        # Playwright storage_state() may return before file is fully flushed to disk
        import time
        max_retries = 10
        retry_delay = 0.1  # 100ms
        file_size = 0

        for retry in range(max_retries):
            # Check if file exists
            if not temp_path.exists():
                if retry < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Session file was not created after {max_retries} retries")
                    return jsonify({'success': False, 'error': 'Session file was not created'}), 500

            # Check file size
            file_size = temp_path.stat().st_size

            if file_size > 0:
                # File exists and has content - success!
                logger.info(f"✓ Session file ready after {retry + 1} attempts: {file_size} bytes")
                break

            if retry < max_retries - 1:
                # File exists but empty - wait and retry
                logger.debug(f"Session file empty on attempt {retry + 1}, retrying...")
                time.sleep(retry_delay)
            else:
                # Final attempt - file is still empty
                logger.error(f"Session file is empty (0 bytes) after {max_retries} retries")
                temp_path.unlink()
                return jsonify({'success': False, 'error': 'Session file is empty - authentication may have failed'}), 500

        # Read and validate JSON
        try:
            with open(temp_path, 'r') as f:
                session_data_json = f.read()

            # Validate and parse JSON
            session_data = json.loads(session_data_json)
        except json.JSONDecodeError as e:
            logger.error(f"Session file contains invalid JSON: {e}")
            temp_path.unlink()
            return jsonify({'success': False, 'error': f'Invalid session data: {e}'}), 500

        # Save to database using shared utility
        save_session_to_database(current_user.id, session_data)

        # Cleanup
        temp_path.unlink()

        logger.info(f"✓✓✓ Session successfully saved to database for user {current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Session saved successfully'
        })

    except Exception as e:
        logger.error(f"Error saving stream session: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AUTOMATED SSO AUTHENTICATION (NO BROWSER STREAMING)
# ============================================================================

# Store active authentication sessions
_active_auth_sessions = {}

@app.route('/api/auth/auto-start', methods=['POST'])
@login_required
def api_auto_auth_start():
    """Start automated SSO authentication"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        # Run async function synchronously
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Clean up any existing session for this user
            if current_user.id in _active_auth_sessions:
                old_handler = _active_auth_sessions[current_user.id]
                try:
                    if hasattr(old_handler, 'cleanup'):
                        loop.run_until_complete(old_handler.cleanup())
                except:
                    pass  # Ignore cleanup errors

            # Create new authentication handler with PERSISTENT PROFILE
            from src.auth.persistent_browser_manager import AutoAuthWithPersistentProfile
            handler = AutoAuthWithPersistentProfile(current_user.id)
            _active_auth_sessions[current_user.id] = handler

            # Start authentication (uses headless=False for cookie persistence!)
            # Check if user has debug mode enabled
            debug_mode = current_user.debug_mode if hasattr(current_user, 'debug_mode') else False
            result = loop.run_until_complete(handler.authenticate(email, password, debug_mode=debug_mode))
        except Exception as e:
            loop.close()
            raise

        if result['status'] == 'success':
            # Clean up loop since we're done
            loop.close()
            # Authentication completed without MFA - save session
            session_data = result['session_data']

            # Save to database using shared utility
            save_session_to_database(current_user.id, session_data)

            # Clean up
            del _active_auth_sessions[current_user.id]

            logger.info(f"✓ Auto-authentication completed for user {current_user.id} (no MFA)")
            return jsonify({
                'success': True,
                'status': 'success',
                'message': 'Authentication successful'
            })

        elif result['status'] == 'mfa_required':
            # MFA required - DON'T close loop yet, background thread will use it
            logger.info(f"MFA required for user {current_user.id}, number: {result['mfa_number']}")

            # Store the loop in the handler so background thread can use it
            handler._event_loop = loop

            # Start background thread to wait for MFA completion
            handler.start_mfa_wait_background()

            return jsonify({
                'success': True,
                'status': 'mfa_required',
                'mfa_number': result['mfa_number'],
                'message': result['message']
            })

        else:
            # Error - close loop
            loop.close()
            if current_user.id in _active_auth_sessions:
                del _active_auth_sessions[current_user.id]

            # Check if it's a wrong password error (retriable)
            if result.get('error') == 'wrong_password':
                return jsonify({
                    'success': False,
                    'status': 'error',
                    'error': 'wrong_password',
                    'message': result.get('message', 'Incorrect password. Please try again.'),
                    'retry': True
                }), 401  # 401 Unauthorized for wrong password

            # Other errors
            return jsonify({
                'success': False,
                'status': 'error',
                'error': result.get('error', 'Authentication failed'),
                'message': result.get('message', 'Authentication failed')
            }), 500

    except Exception as e:
        logger.error(f"Auto-auth start error: {e}", exc_info=True)
        if current_user.id in _active_auth_sessions:
            del _active_auth_sessions[current_user.id]
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/auto-status')
@login_required
def api_auto_auth_status():
    """Poll authentication status (used when waiting for MFA)"""
    try:
        handler = _active_auth_sessions.get(current_user.id)
        if not handler:
            return jsonify({'status': 'no_session', 'error': 'No active authentication session'})

        # Get current status from handler (background thread updates this)
        status = handler.get_status()

        # If MFA completed successfully, save session and clean up
        if status['status'] == 'success' and status.get('session_data'):
            session_data = status['session_data']

            # Save to database using shared utility
            save_session_to_database(current_user.id, session_data)

            # Clean up
            del _active_auth_sessions[current_user.id]

            logger.info(f"✓ Auto-authentication completed for user {current_user.id} (with MFA)")
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful'
            })

        # Return current status (still waiting or error)
        return jsonify(status)

    except Exception as e:
        logger.error(f"Auto-auth status error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500


# ============================================================================
# DESK REMAPPING
# ============================================================================

# Track active remapping sessions
_active_remap_sessions = {}

@app.route('/tools/remap-desks')
@login_required
def remap_desks_page():
    """Desk remapping interface"""
    return render_template('remap_desks.html', user=current_user)


@app.route('/api/tools/remap-desks/start', methods=['POST'])
@login_required
def api_start_desk_remap():
    """Start desk remapping process"""
    try:
        # Check if already running (only block if status is 'running' or 'starting')
        if current_user.id in _active_remap_sessions:
            existing_status = _active_remap_sessions[current_user.id].get('status')
            if existing_status in ['running', 'starting']:
                return jsonify({
                    'success': False,
                    'error': 'Desk remapping is already in progress'
                }), 400
            else:
                # Clear old session (error or completed) so we can start a new one
                del _active_remap_sessions[current_user.id]

        # Check if user has valid SpaceIQ session
        spaceiq_session = SpaceIQSession.query.filter_by(user_id=current_user.id).first()
        if not spaceiq_session or not spaceiq_session.session_data or not spaceiq_session.is_valid:
            return jsonify({
                'success': False,
                'error': 'No valid SpaceIQ session found. Please authenticate first.',
                'needs_auth': True
            }), 401

        # Verify session can be decrypted
        try:
            from src.utils.auth_encryption import decrypt_data
            decrypted = decrypt_data(spaceiq_session.session_data)
            json.loads(decrypted)
        except Exception as e:
            logger.warning(f"Session decryption failed for user {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Session decryption failed. Please re-authenticate.',
                'needs_auth': True
            }), 401

        # Initialize remap session tracker
        _active_remap_sessions[current_user.id] = {
            'status': 'starting',
            'progress': [],
            'total_desks': 0,
            'permanent_desks': 0,
            'error': None
        }

        # Run remapping in background thread
        import threading
        thread = threading.Thread(
            target=_run_desk_remapping_background,
            args=(current_user.id,),
            daemon=True
        )
        thread.start()

        logger.info(f"Started desk remapping for user {current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Desk remapping started'
        })

    except Exception as e:
        logger.error(f"Failed to start desk remapping: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tools/remap-desks/status')
@login_required
def api_remap_desk_status():
    """Get desk remapping progress"""
    try:
        session = _active_remap_sessions.get(current_user.id)

        if not session:
            return jsonify({
                'status': 'not_started',
                'progress': []
            })

        return jsonify(session)

    except Exception as e:
        logger.error(f"Error getting remap status: {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500


def _run_desk_remapping_background(user_id: int):
    """Background task to run desk remapping"""
    try:
        import asyncio
        from map_desk_positions import map_desk_positions

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Update status
        _active_remap_sessions[user_id]['status'] = 'running'

        # Progress callback to update session tracker
        def progress_callback(message):
            """Add progress message to session tracker"""
            _active_remap_sessions[user_id]['progress'].append({
                'time': datetime.utcnow().isoformat(),
                'message': message
            })

        # Run the mapping function in web mode (raises exception on session expiry)
        result = loop.run_until_complete(
            map_desk_positions(user_id=user_id, web_mode=True, progress_callback=progress_callback)
        )

        _active_remap_sessions[user_id]['status'] = 'completed'
        _active_remap_sessions[user_id]['progress'].append({
            'time': datetime.utcnow().isoformat(),
            'message': 'Desk remapping completed successfully!'
        })

    except Exception as e:
        logger.error(f"Desk remapping background task error for user {user_id}: {e}", exc_info=True)
        if user_id in _active_remap_sessions:
            _active_remap_sessions[user_id]['status'] = 'error'
            _active_remap_sessions[user_id]['error'] = str(e)

            # Check if it's a session expiry error
            if "Session expired" in str(e) or "re-authenticate" in str(e):
                _active_remap_sessions[user_id]['needs_auth'] = True

            _active_remap_sessions[user_id]['progress'].append({
                'time': datetime.utcnow().isoformat(),
                'message': f'Error: {str(e)}'
            })


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

@app.cli.command()
def init_db():
    """Initialize the database with migrations"""
    print("🔄 Running database migrations...")
    if run_all_migrations():
        print("✅ Database initialized successfully with migrations")
    else:
        print("❌ Database initialization failed!")
        print("   Your original database has been restored from backup")
        return 1

@app.cli.command()
def migrate_db():
    """Run database migrations manually"""
    print("🔄 Running database migrations...")
    if run_all_migrations():
        print("✅ Database migrations completed successfully")
    else:
        print("❌ Database migrations failed!")
        print("   Your original database has been restored from backup")
        return 1


@app.cli.command()
def create_admin():
    """Create an admin user"""
    username = input("Username: ")
    email = input("Email: ")
    password = input("Password: ")

    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)

    # Create default config
    bot_config = BotConfig(user_id=user.id)
    db.session.add(bot_config)

    # Create bot instance
    bot_instance = BotInstance(user_id=user.id, status='stopped')
    db.session.add(bot_instance)

    db.session.commit()

    print(f"Admin user '{username}' created successfully!")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Ensure working directory is correct
    os.chdir(Path(__file__).parent)

    # Run database migrations (safely preserves user data)
    with app.app_context():
        print("🔄 Running database migrations...")
        if run_all_migrations():
            print("✅ Database migrations completed successfully")
        else:
            print("❌ Database migrations failed!")
            print("   Your original database has been restored from backup")
            print("   Please check the logs above for details")
            sys.exit(1)

        # Reset all bot instances and clear previous session data on startup
        from models import BotInstance
        from src.utils.live_logger import get_live_logger

        bot_instances = BotInstance.query.all()

        for bot_instance in bot_instances:
            # Reset statistics and status
            bot_instance.status = 'stopped'
            bot_instance.stopped_at = datetime.utcnow()
            bot_instance.current_round = 0
            bot_instance.successful_bookings = 0
            bot_instance.failed_attempts = 0
            bot_instance.current_activity = None
            bot_instance.error_message = None
            bot_instance.pid = None

            # Clear logs for fresh session
            bot_instance.clear_logs()

            # Clear live logs (UI logs) for fresh session
            live_logger = get_live_logger(bot_instance.user_id)
            live_logger.clear_logs()

        db.session.commit()
        print("Reset all bot instances and cleared session data")

    # Check environment mode
    flask_env = os.getenv('FLASK_ENV', 'development')
    debug_mode = os.getenv('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes')

    if flask_env == 'production':
        debug_mode = False  # Force debug off in production
        print("\n⚠️  Running in PRODUCTION mode - debug disabled")

    print("\n" + "=" * 60)
    print("SpaceIQ Multi-User Bot Platform")
    print("=" * 60)
    print(f"Environment: {flask_env}")
    print(f"Debug mode: {debug_mode}")
    print(f"Dashboard: http://localhost:5000")
    print(f"Logs: logs/app.log")
    print("=" * 60 + "\n")

    # Run the app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode
    )
