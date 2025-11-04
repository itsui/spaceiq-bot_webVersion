"""
SpaceIQ Bot Web Interface
A simple web dashboard to control the SpaceIQ desk booking bot
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import logging

# Add the root directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.utils.auth_encryption import load_encrypted_session, save_encrypted_session

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Global variables for bot status
bot_status = {
    'running': False,
    'process': None,
    'started_at': None,
    'last_activity': None,
    'current_round': 0,
    'successful_bookings': 0,
    'failed_attempts': 0,
    'logs': [],
    'error': None
}

# Enhanced logging setup
def setup_logging():
    """Setup comprehensive logging for the web interface"""
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # Create web interface specific logger
    web_logger = logging.getLogger('web_interface')
    web_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    web_logger.handlers.clear()

    # File handler for web interface logs
    web_log_file = logs_dir / 'web_interface.log'
    file_handler = logging.FileHandler(web_log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

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
    web_logger.addHandler(file_handler)
    web_logger.addHandler(console_handler)

    # Log rotation for bot output
    bot_log_file = logs_dir / 'bot_output.log'
    return web_logger, web_log_file, bot_log_file

# Initialize logging
logger, web_log_file, bot_log_file = setup_logging()


class BotController:
    """Controls the bot process and manages its state"""

    def __init__(self):
        self.process = None
        self.output_thread = None
        self.running = False
        self.bot_log_file = None

    def start_bot(self, headless=True, auto_mode=True):
        """Start the bot process"""
        if self.process and self.process.poll() is None:
            logger.warning("Attempted to start bot but it's already running")
            return False, "Bot is already running"

        try:
            # Build command
            cmd = [sys.executable, 'multi_date_book.py']
            if auto_mode:
                cmd.append('--auto')
            if headless:
                cmd.append('--headless')
            cmd.append('--unattended')

            logger.info(f"Starting bot with command: {' '.join(cmd)}")
            logger.info(f"Bot parameters: headless={headless}, auto_mode={auto_mode}")

            # Create timestamped log file for this session
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_log_file = Path('logs') / f'bot_session_{timestamp}.log'

            # Set environment variables for proper Unicode handling
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '1'  # Fix Windows Unicode issues
            # Add browser stability settings
            env['PLAYWRIGHT_BROWSERS_PATH'] = '0'  # Use system browsers
            env['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

            # Start the process with comprehensive logging
            # Note: We use bytes mode to handle Unicode properly in the monitoring code
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,  # Use bytes mode to handle Unicode properly
                bufsize=0,  # Use unbuffered mode for binary
                env=env,  # Pass environment variables
                cwd=Path.cwd(),  # Ensure we're in the right directory
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0  # Better process management
            )

            self.running = True
            self.bot_log_file = session_log_file

            # Update bot status (don't include the process object - it's not JSON serializable)
            bot_status['running'] = True
            bot_status['started_at'] = datetime.now().isoformat()
            # bot_status['process'] = self.process  # Commented out - not JSON serializable
            bot_status['error'] = None
            bot_status['logs'] = []  # Clear previous logs
            bot_status['pid'] = self.process.pid if self.process else None  # Store PID instead

            # Log the start
            self._write_to_session_log(f"=== Bot Session Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            self._write_to_session_log(f"Command: {' '.join(cmd)}")
            self._write_to_session_log(f"Working Directory: {Path.cwd()}")
            self._write_to_session_log(f"Python Version: {sys.version}")
            self._write_to_session_log(f"Environment Variables: PYTHONIOENCODING={env.get('PYTHONIOENCODING')}, PYTHONLEGACYWINDOWSSTDIO={env.get('PYTHONLEGACYWINDOWSSTDIO')}")
            self._write_to_session_log(f"System Info: Platform={sys.platform}, Encoding={sys.getdefaultencoding()}")
            self._write_to_session_log(f"Process ID: {self.process.pid}")
            self._write_to_session_log(f"Parent Process ID: {os.getppid()}")
            self._write_to_session_log(f"User: {os.getenv('USERNAME', 'unknown')}")

            logger.info(f"Bot process started with PID: {self.process.pid}")
            logger.info(f"Session log file: {session_log_file}")
            logger.info(f"Unicode handling: UTF-8 -> latin-1 -> hex fallback")
            logger.info(f"Environment: PYTHONIOENCODING={env.get('PYTHONIOENCODING')}")

            # Start monitoring output
            self.output_thread = threading.Thread(target=self._monitor_output)
            self.output_thread.daemon = True
            self.output_thread.start()

            return True, "Bot started successfully"

        except Exception as e:
            error_msg = f"Failed to start bot: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._write_to_session_log(f"ERROR: {error_msg}")
            self._write_to_session_log(f"Traceback: {traceback.format_exc()}")
            return False, error_msg

    def stop_bot(self):
        """Stop the bot process"""
        if not self.process:
            logger.warning("Attempted to stop bot but it's not running")
            return False, "Bot is not running"

        try:
            pid = self.process.pid
            logger.info(f"Stopping bot process with PID: {pid}")
            self._write_to_session_log(f"=== Bot Stop Requested at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

            # Try graceful termination first
            self.process.terminate()
            self._write_to_session_log("Sent SIGTERM to bot process")

            try:
                # Wait up to 10 seconds for graceful shutdown
                self.process.wait(timeout=10)
                self._write_to_session_log("Bot process terminated gracefully")
                logger.info("Bot process terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self._write_to_session_log("Graceful shutdown failed, forcing termination...")
                self.process.kill()
                self.process.wait()
                self._write_to_session_log("Bot process killed forcefully")
                logger.warning("Bot process killed forcefully")

            # Finalize session
            self.running = False
            bot_status['running'] = False
            # bot_status['process'] = None  # Commented out - not JSON serializable
            bot_status['pid'] = None  # Clear PID
            bot_status['stopped_at'] = datetime.now().isoformat()

            # Close session log
            if self.bot_log_file:
                self._write_to_session_log(f"=== Bot Session Ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                self._write_to_session_log(f"Final Status: Stopped by user request")
                logger.info(f"Bot session log closed: {self.bot_log_file}")

            return True, "Bot stopped successfully"

        except Exception as e:
            error_msg = f"Failed to stop bot: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            if self.bot_log_file:
                self._write_to_session_log(f"ERROR during shutdown: {error_msg}")
                self._write_to_session_log(f"Traceback: {traceback.format_exc()}")
            return False, error_msg

    def _monitor_output(self):
        """Monitor bot output and update status"""
        if not self.process:
            logger.warning("Monitor output called but no process exists")
            return

        logger.info(f"Starting to monitor bot output for PID: {self.process.pid}")
        self._write_to_session_log("=== Starting Bot Output Monitoring ===")

        try:
            while True:
                # Read bytes line and handle Unicode properly
                line_bytes = self.process.stdout.readline()
                if not line_bytes:
                    break

                try:
                    # Try to decode as UTF-8 first
                    line = line_bytes.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        # Fallback to latin-1 (can decode any byte sequence)
                        line = line_bytes.decode('latin-1', errors='replace').strip()
                    except Exception:
                        # Last resort: represent as hex
                        line = f"[BINARY DATA: {line_bytes.hex()}]"

                timestamp = datetime.now().isoformat()

                # Add to web interface logs
                bot_status['logs'].append({
                    'timestamp': timestamp,
                    'message': line,
                    'type': self._classify_log_message(line)
                })

                # Keep only last 200 log lines for web display
                if len(bot_status['logs']) > 200:
                    bot_status['logs'] = bot_status['logs'][-200:]

                # Write to session log file (handle Unicode properly)
                try:
                    self._write_to_session_log(f"[{timestamp}] {line}")
                except UnicodeEncodeError:
                    # If we can't write the line as-is, write a safe version
                    safe_line = line.encode('ascii', errors='replace').decode('ascii')
                    self._write_to_session_log(f"[{timestamp}] {safe_line} [UNICODE HANDLED]")

                # Parse key information from logs
                self._parse_log_line(line)

                # Update activity timestamp
                bot_status['last_activity'] = timestamp

                # Check if process has ended
                if self.process.poll() is not None:
                    exit_code = self.process.returncode
                    logger.info(f"Bot process ended with exit code: {exit_code}")
                    self._write_to_session_log(f"=== Bot Process Ended ===")
                    self._write_to_session_log(f"Exit Code: {exit_code}")
                    self._write_to_session_log(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    self._write_to_session_log(f"Process Duration: {(datetime.now() - datetime.fromisoformat(bot_status['started_at'])).total_seconds():.2f} seconds")

                    # Add error analysis
                    if exit_code != 0:
                        self._write_to_session_log(f"=== ERROR ANALYSIS ===")
                        self._write_to_session_log(f"Process terminated with non-zero exit code: {exit_code}")

                        # Check for common error patterns in recent logs
                        recent_logs = bot_status['logs'][-10:]  # Last 10 log entries
                        for log_entry in recent_logs:
                            message = log_entry.get('message', '')
                            if 'UnicodeEncodeError' in message:
                                self._write_to_session_log("ERROR TYPE: Unicode Encoding Error")
                                self._write_to_session_log("SOLUTION: Environment variables PYTHONIOENCODING=utf-8 should fix this")
                            elif 'ModuleNotFoundError' in message:
                                self._write_to_session_log("ERROR TYPE: Missing Python Module")
                            elif 'Permission denied' in message:
                                self._write_to_session_log("ERROR TYPE: File Permission Issue")
                            elif 'Connection' in message and 'refused' in message:
                                self._write_to_session_log("ERROR TYPE: Network Connection Issue")
                            elif 'Target page, context or browser has' in message:
                                self._write_to_session_log("ERROR TYPE: Browser Context Lost")
                                self._write_to_session_log("SOLUTION: Browser context was lost - this is common in long-running sessions")
                                self._write_to_session_log("RECOMMENDATION: Restart the bot or try non-headless mode temporarily")
                            elif 'Page.goto' in message and 'Target page' in message:
                                self._write_to_session_log("ERROR TYPE: Navigation Failed")
                                self._write_to_session_log("SOLUTION: SpaceIQ website may be unavailable or blocked")
                            elif 'timeout' in message.lower():
                                self._write_to_session_log("ERROR TYPE: Timeout Issue")
                                self._write_to_session_log("SOLUTION: Network timeout or SpaceIQ response delay")

                        self._write_to_session_log(f"=== END ERROR ANALYSIS ===")

                    break

        except Exception as e:
            error_msg = f"Error monitoring bot output: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Enhanced error logging
            if self.bot_log_file:
                self._write_to_session_log(f"MONITOR ERROR: {error_msg}")
                self._write_to_session_log(f"Traceback: {traceback.format_exc()}")
                self._write_to_session_log(f"Process Status: {'running' if self.process and self.process.poll() is None else 'ended'}")
                if self.process:
                    self._write_to_session_log(f"Process Return Code: {self.process.returncode}")
                    self._write_to_session_log(f"Process PID: {self.process.pid}")
                self._write_to_session_log(f"Monitoring Thread ID: {threading.get_ident()}")

                # System state at time of error
                import psutil
                try:
                    process = psutil.Process()
                    self._write_to_session_log(f"Web Interface Memory Usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                    self._write_to_session_log(f"Web Interface CPU Usage: {process.cpu_percent():.1f}%")
                except:
                    self._write_to_session_log("Could not capture system stats (psutil not available)")

        finally:
            # Finalize bot status
            self.running = False
            bot_status['running'] = False
            # bot_status['process'] = None  # Commented out - not JSON serializable
            bot_status['pid'] = None  # Clear PID
            bot_status['stopped_at'] = datetime.now().isoformat()

            # Close session log if process ended unexpectedly
            if self.bot_log_file and self.process and self.process.returncode not in [0, None]:
                self._write_to_session_log(f"=== Bot Session Ended Unexpectedly ===")
                self._write_to_session_log(f"Exit Code: {self.process.returncode}")
                self._write_to_session_log(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self._write_to_session_log(f"Session Duration: {(datetime.now() - datetime.fromisoformat(bot_status['started_at'])).total_seconds():.2f} seconds")

                # Provide immediate help for common errors
                if self.process.returncode == 1:
                    self._write_to_session_log("=== IMMEDIATE HELP ===")
                    self._write_to_session_log("Exit Code 1 typically indicates:")
                    self._write_to_session_log("1. Unicode encoding issues (check logs for UnicodeEncodeError)")
                    self._write_to_session_log("2. Missing dependencies or import errors")
                    self._write_to_session_log("3. Configuration errors")
                    self._write_to_session_log("=== END IMMEDIATE HELP ===")

                logger.warning(f"Bot process ended unexpectedly with code {self.process.returncode}")

    def _classify_log_message(self, message):
        """Classify log message for display purposes"""
        msg_lower = message.lower()

        if any(keyword in msg_lower for keyword in ['error', 'failed', 'exception', 'traceback']):
            return 'error'
        elif any(keyword in msg_lower for keyword in ['warning', 'warn']):
            return 'warning'
        elif any(keyword in msg_lower for keyword in ['success', 'booked', 'completed', 'finished']):
            return 'success'
        else:
            return 'info'

    def _write_to_session_log(self, message):
        """Write message to session log file"""
        if self.bot_log_file:
            try:
                with open(self.bot_log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{message}\n")
            except Exception as e:
                logger.error(f"Failed to write to session log: {e}")

    def _parse_log_line(self, line):
        """Parse log lines to extract useful information"""
        line_lower = line.lower()

        # Check for successful bookings
        if 'success' in line_lower and 'book' in line_lower:
            bot_status['successful_bookings'] += 1

        # Check for failed attempts
        if 'failed' in line_lower or 'error' in line_lower:
            bot_status['failed_attempts'] += 1

        # Check for round information
        if 'round' in line_lower:
            try:
                # Try to extract round number
                import re
                round_match = re.search(r'round\s+(\d+)', line_lower)
                if round_match:
                    bot_status['current_round'] = int(round_match.group(1))
            except:
                pass


# Create global bot controller
bot_controller = BotController()


def load_booking_config():
    """Load booking configuration from JSON file"""
    try:
        config_path = Path('config/booking_config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Failed to load booking config: {e}")
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
        logger.error(f"Failed to save booking config: {e}")
        return False


def get_booking_history():
    """Get recent booking history from logs"""
    try:
        # Look for booking log files
        log_dir = Path('logs')
        if not log_dir.exists():
            return []

        # This is a simplified version - you could enhance this to parse actual log files
        history = []

        # Add some mock data for now
        history.extend([
            {
                'date': '2025-11-05',
                'desk': '2.24.15',
                'status': 'success',
                'time': '09:15:23'
            },
            {
                'date': '2025-10-29',
                'desk': '2.24.08',
                'status': 'success',
                'time': '09:12:45'
            }
        ])

        return history
    except Exception as e:
        logger.error(f"Failed to get booking history: {e}")
        return []


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current bot status"""
    try:
        # Ensure all data is JSON serializable
        status_copy = {
            'running': bot_status.get('running', False),
            'started_at': bot_status.get('started_at'),
            'last_activity': bot_status.get('last_activity'),
            'current_round': bot_status.get('current_round', 0),
            'successful_bookings': bot_status.get('successful_bookings', 0),
            'failed_attempts': bot_status.get('failed_attempts', 0),
            'logs': bot_status.get('logs', []),
            'error': bot_status.get('error'),
            'stopped_at': bot_status.get('stopped_at'),
            'pid': bot_status.get('pid')
        }
        return jsonify(status_copy)
    except Exception as e:
        logger.error(f"Error creating status response: {e}")
        # Return a safe status if there's an error
        return jsonify({
            'running': False,
            'error': f'Status error: {str(e)}',
            'logs': [],
            'current_round': 0,
            'successful_bookings': 0,
            'failed_attempts': 0
        })


@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the bot"""
    data = request.get_json() or {}
    headless = data.get('headless', True)
    auto_mode = data.get('auto_mode', True)

    success, message = bot_controller.start_bot(headless=headless, auto_mode=auto_mode)

    return jsonify({
        'success': success,
        'message': message
    })


@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the bot"""
    success, message = bot_controller.stop_bot()

    return jsonify({
        'success': success,
        'message': message
    })


@app.route('/api/config')
def get_config():
    """Get booking configuration"""
    config = load_booking_config()
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update booking configuration"""
    try:
        config_data = request.get_json()

        # Validate required fields
        if not config_data:
            return jsonify({
                'success': False,
                'message': 'No configuration data provided'
            })

        success = save_booking_config(config_data)

        return jsonify({
            'success': success,
            'message': 'Configuration updated successfully' if success else 'Failed to save configuration'
        })

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to update configuration: {str(e)}'
        })


@app.route('/api/history')
def get_history():
    """Get booking history"""
    history = get_booking_history()
    return jsonify(history)


@app.route('/api/logs')
def get_logs():
    """Get available log files"""
    try:
        logs_dir = Path('logs')
        if not logs_dir.exists():
            return jsonify({'logs': []})

        # Get all log files with their info
        log_files = []
        for log_file in logs_dir.glob('*.log'):
            stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'type': 'session' if 'session' in log_file.name else
                       'web' if 'web_interface' in log_file.name else 'other'
            })

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x['modified'], reverse=True)

        return jsonify({'logs': log_files})

    except Exception as e:
        logger.error(f"Failed to get log files: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/<filename>')
def download_log(filename):
    """Download a specific log file"""
    try:
        # Security: Ensure filename is just a basename, not a path
        safe_filename = Path(filename).name
        log_path = Path('logs') / safe_filename

        if not log_path.exists():
            return jsonify({'error': 'Log file not found'}), 404

        # Ensure it's a .log file
        if not safe_filename.endswith('.log'):
            return jsonify({'error': 'Invalid file type'}), 400

        return send_file(
            log_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='text/plain'
        )

    except Exception as e:
        logger.error(f"Failed to download log {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/<filename>/view')
def view_log(filename):
    """View content of a specific log file"""
    try:
        # Security: Ensure filename is just a basename, not a path
        safe_filename = Path(filename).name
        log_path = Path('logs') / safe_filename

        if not log_path.exists():
            return jsonify({'error': 'Log file not found'}), 404

        # Ensure it's a .log file
        if not safe_filename.endswith('.log'):
            return jsonify({'error': 'Invalid file type'}), 400

        # Read last N lines to avoid sending huge files
        max_lines = 1000
        lines = []

        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read all lines and take the last max_lines
                all_lines = f.readlines()
                lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
        except UnicodeDecodeError:
            # Try with different encoding
            with open(log_path, 'r', encoding='latin-1', errors='replace') as f:
                all_lines = f.readlines()
                lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

        return jsonify({
            'filename': safe_filename,
            'content': ''.join(lines),
            'total_lines': len(lines),
            'truncated': len(all_lines) > max_lines
        })

    except Exception as e:
        logger.error(f"Failed to view log {filename}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/cleanup', methods=['POST'])
def cleanup_logs():
    """Clean up old log files"""
    try:
        logs_dir = Path('logs')
        if not logs_dir.exists():
            return jsonify({'success': False, 'message': 'Logs directory not found'})

        # Remove log files older than 7 days
        import time
        cutoff_time = time.time() - (7 * 24 * 60 * 60)  # 7 days ago
        removed_count = 0

        for log_file in logs_dir.glob('*.log'):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old log file: {log_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove {log_file.name}: {e}")

        return jsonify({
            'success': True,
            'message': f'Cleaned up {removed_count} old log files',
            'removed_count': removed_count
        })

    except Exception as e:
        logger.error(f"Failed to cleanup logs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/config')
def config_page():
    """Configuration page"""
    return render_template('config.html')


@app.route('/history')
def history_page():
    """Booking history page"""
    return render_template('history.html')


@app.route('/logs')
def logs_page():
    """Logs management page"""
    return render_template('logs.html')


if __name__ == '__main__':
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("Starting SpaceIQ Bot Web Interface...")
    print(f"Dashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the web interface")

    app.run(debug=True, host='0.0.0.0', port=5000)