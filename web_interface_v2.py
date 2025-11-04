"""
SpaceIQ Bot Web Interface V2
Multi-user web dashboard with integrated authentication
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import logging
from playwright.async_api import async_playwright

# Add the root directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.utils.auth_encryption import load_encrypted_session, save_encrypted_session

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Configure session for multi-user support
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'spaceiq_bot:'

# Enhanced logging setup
def setup_logging():
    """Setup comprehensive logging for the web interface"""
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    web_logger = logging.getLogger('web_interface_v2')
    web_logger.setLevel(logging.DEBUG)

    web_logger.handlers.clear()

    # File handler for web interface logs
    web_log_file = logs_dir / 'web_interface_v2.log'
    file_handler = logging.FileHandler(web_log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(username)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    web_logger.addHandler(file_handler)
    web_logger.addHandler(console_handler)

    return web_logger

logger = setup_logging()

# Multi-user session management
@dataclass
class UserSession:
    """User session data"""
    user_id: str
    username: str
    email: str
    auth_file: Path
    authenticated: bool = False
    bot_process: Optional[subprocess.Popen] = None
    bot_status: Dict = None
    created_at: datetime = None
    last_activity: datetime = None

# Active user sessions (in production, use Redis or database)
user_sessions: Dict[str, UserSession] = {}

class BotManager:
    """Manages bot processes for multiple users"""

    @staticmethod
    def start_bot_for_user(user_session: UserSession, config: Dict) -> bool:
        """Start a bot process for a specific user"""
        try:
            # Create user-specific auth file
            user_auth_dir = Path('sessions') / user_session.user_id
            user_auth_dir.mkdir(parents=True, exist_ok=True)
            user_auth_file = user_auth_dir / 'auth.json'

            # Check if user has existing session
            if user_auth_file.exists():
                logger.info(f"User {user_session.username} has existing session")
                return True

            # Start browser for authentication
            logger.info(f"Starting authentication for user {user_session.username}")
            # This will be handled by the authentication endpoint

            return True

        except Exception as e:
            logger.error(f"Failed to start bot for user {user_session.username}: {e}")
            return False

    @staticmethod
    def stop_bot_for_user(user_session: UserSession) -> bool:
        """Stop bot process for a specific user"""
        try:
            if user_session.bot_process and user_session.bot_process.poll() is None:
                user_session.bot_process.terminate()
                try:
                    user_session.bot_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    user_session.bot_process.kill()

                user_session.bot_process = None
                logger.info(f"Bot stopped for user {user_session.username}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to stop bot for user {user_session.username}: {e}")
            return False

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication handling"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html', error="Please enter username and password")

        # For SpaceIQ SSO, username is typically the email
        email = username if '@' in username else f"{username}@company.com"

        # Create user session
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email

        user_session = UserSession(
            user_id=user_id,
            username=username,
            email=email,
            auth_file=Path('sessions') / user_id / 'auth.json',
            bot_status={'running': False, 'logs': [], 'error': None},
            created_at=datetime.now(),
            last_activity=datetime.now()
        )

        user_sessions[user_id] = user_session

        logger.info(f"User {username} logged in with ID {user_id}")

        # Redirect to authentication (browser will open for SSO)
        return redirect(url_for('authenticate'))

    return render_template('login.html')

@app.route('/authenticate')
def authenticate():
    """Handle SSO authentication - opens browser for SpaceIQ login"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return redirect(url_for('login'))

    user_session = user_sessions[user_id]

    return render_template('authenticate.html',
                         username=user_session.username,
                         user_id=user_id)

@app.route('/api/auth/start', methods=['POST'])
def start_authentication():
    """Start the authentication process - opens browser for SSO"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'success': False, 'message': 'Not logged in'})

    user_session = user_sessions[user_id]

    try:
        # Start authentication in background thread
        def auth_thread():
            asyncio.run(perform_authentication(user_session))

        thread = threading.Thread(target=auth_thread, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Authentication started - browser will open for SpaceIQ SSO login'
        })

    except Exception as e:
        logger.error(f"Failed to start authentication for {user_session.username}: {e}")
        return jsonify({'success': False, 'message': str(e)})

async def perform_authentication(user_session: UserSession):
    """Perform SpaceIQ SSO authentication"""
    try:
        target_url = f"{Config.SPACEIQ_URL.rstrip('/')}/finder/building/LC/floor/2"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Open browser for SSO
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            page = await context.new_page()
            await page.goto(target_url)

            # Wait for user to complete SSO login
            logger.info(f"Waiting for SSO login completion for {user_session.username}")

            try:
                await page.wait_for_url(
                    lambda url: "/login" not in url and "/finder/building/" in url,
                    timeout=300000  # 5 minutes
                )

                # Save authentication state
                await context.storage_state(path=str(user_session.auth_file))

                # Encrypt the session
                import json
                with open(user_session.auth_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                if save_encrypted_session(user_session.auth_file, session_data):
                    user_session.authenticated = True
                    logger.info(f"Authentication completed for {user_session.username}")
                else:
                    logger.error(f"Failed to encrypt session for {user_session.username}")

            except Exception as e:
                logger.error(f"Authentication failed for {user_session.username}: {e}")

            await browser.close()

    except Exception as e:
        logger.error(f"Authentication error for {user_session.username}: {e}")

@app.route('/api/auth/check')
def check_authentication():
    """Check if authentication is complete"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'success': False, 'message': 'Not logged in'})

    user_session = user_sessions[user_id]

    # Check if auth file exists and is valid
    if user_session.auth_file.exists():
        return jsonify({
            'success': True,
            'authenticated': True,
            'message': 'Authentication successful'
        })
    else:
        return jsonify({
            'success': True,
            'authenticated': False,
            'message': 'Waiting for authentication to complete'
        })

@app.route('/logout')
def logout():
    """Logout and clean up user session"""
    user_id = session.get('user_id')
    if user_id and user_id in user_sessions:
        user_session = user_sessions[user_id]

        # Stop bot if running
        if user_session.bot_status.get('running'):
            BotManager.stop_bot_for_user(user_session)

        # Clean up user session
        del user_sessions[user_id]

        logger.info(f"User {user_session.username} logged out")

    session.clear()
    return redirect(url_for('login'))

# Bot control routes
@app.route('/')
def index():
    """Main dashboard"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return redirect(url_for('login'))

    return render_template('dashboard_v2.html')

@app.route('/api/status')
def get_status():
    """Get current bot status for the logged-in user"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'error': 'Not logged in'}), 401

    user_session = user_sessions[user_id]
    return jsonify(user_session.bot_status)

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the bot for the logged-in user"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'error': 'Not logged in'}), 401

    user_session = user_sessions[user_id]

    # Check if user is authenticated
    if not user_session.auth_file.exists():
        return jsonify({
            'success': False,
            'message': 'Please authenticate first'
        })

    try:
        # Load configuration
        config = load_booking_config()

        # Start bot process
        cmd = [sys.executable, 'multi_date_book_web.py', '--auto', '--headless', '--unattended']

        # Set user-specific environment
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        env['USER_AUTH_FILE'] = str(user_session.auth_file)

        user_session.bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=Path.cwd()
        )

        # Update status
        user_session.bot_status = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'logs': [],
            'error': None,
            'current_round': 0,
            'successful_bookings': 0,
            'failed_attempts': 0
        }

        # Start monitoring
        def monitor_thread():
            monitor_bot_output(user_session)

        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()

        logger.info(f"Bot started for user {user_session.username}")

        return jsonify({
            'success': True,
            'message': 'Bot started successfully'
        })

    except Exception as e:
        logger.error(f"Failed to start bot for {user_session.username}: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to start bot: {str(e)}'
        })

def monitor_bot_output(user_session: UserSession):
    """Monitor bot output and update status"""
    try:
        while user_session.bot_process and user_session.bot_process.poll() is None:
            line = user_session.bot_process.stdout.readline()
            if line:
                line = line.strip()
                timestamp = datetime.now().isoformat()

                user_session.bot_status['logs'].append({
                    'timestamp': timestamp,
                    'message': line,
                    'type': 'info'
                })

                # Keep only last 100 log lines
                if len(user_session.bot_status['logs']) > 100:
                    user_session.bot_status['logs'] = user_session.bot_status['logs'][-100:]

                # Parse bot status
                parse_bot_status(line, user_session.bot_status)

                user_session.bot_status['last_activity'] = timestamp

        # Bot has ended
        if user_session.bot_process:
            exit_code = user_session.bot_process.returncode
            user_session.bot_status['running'] = False
            user_session.bot_status['stopped_at'] = datetime.now().isoformat()

            logger.info(f"Bot ended for user {user_session.username} with exit code {exit_code}")

    except Exception as e:
        logger.error(f"Error monitoring bot for {user_session.username}: {e}")
        user_session.bot_status['error'] = str(e)
        user_session.bot_status['running'] = False

def parse_bot_status(line: str, status: Dict):
    """Parse bot output to extract status information"""
    line_lower = line.lower()

    if 'success' in line_lower and 'book' in line_lower:
        status['successful_bookings'] = status.get('successful_bookings', 0) + 1
    elif 'failed' in line_lower or 'error' in line_lower:
        status['failed_attempts'] = status.get('failed_attempts', 0) + 1
    elif 'round' in line_lower:
        try:
            import re
            round_match = re.search(r'round\s+(\d+)', line_lower)
            if round_match:
                status['current_round'] = int(round_match.group(1))
        except:
            pass

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the bot for the logged-in user"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'error': 'Not logged in'}), 401

    user_session = user_sessions[user_id]

    success = BotManager.stop_bot_for_user(user_session)

    if success:
        user_session.bot_status['running'] = False
        logger.info(f"Bot stopped for user {user_session.username}")
        return jsonify({
            'success': True,
            'message': 'Bot stopped successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Bot is not running'
        })

# Configuration routes
def load_booking_config():
    """Load booking configuration"""
    try:
        config_path = Path('config/booking_config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Failed to load booking config: {e}")
        return {}

@app.route('/api/config')
def get_config():
    """Get booking configuration"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'error': 'Not logged in'}), 401

    config = load_booking_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update booking configuration"""
    user_id = session.get('user_id')
    if not user_id or user_id not in user_sessions:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({
                'success': False,
                'message': 'No configuration data provided'
            })

        config_path = Path('config/booking_config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Configuration updated by user {user_sessions[user_id].username}")

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        })

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to update configuration: {str(e)}'
        })

# Session cleanup
def cleanup_expired_sessions():
    """Clean up expired user sessions"""
    current_time = datetime.now()
    expired_sessions = []

    for user_id, user_session in user_sessions.items():
        # Remove sessions inactive for more than 1 hour
        if (current_time - user_session.last_activity).seconds > 3600:
            expired_sessions.append(user_id)

            # Stop bot if running
            if user_session.bot_status.get('running'):
                BotManager.stop_bot_for_user(user_session)

            logger.info(f"Cleaned up expired session for {user_session.username}")

    for user_id in expired_sessions:
        del user_sessions[user_id]

if __name__ == '__main__':
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Create necessary directories
    Path('sessions').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    print("Starting SpaceIQ Bot Web Interface V2...")
    print("Dashboard will be available at: http://localhost:5001")
    print("Multi-user support enabled with individual bot instances")

    app.run(debug=True, host='0.0.0.0', port=5001)