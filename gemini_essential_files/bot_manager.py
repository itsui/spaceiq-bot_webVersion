"""
Multi-User Bot Manager
Manages bot instances for multiple users running simultaneously
"""

import asyncio
import threading
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import logging

from models import db, User, BotInstance, BotConfig, SpaceIQSession, BookingHistory
from src.utils.auth_encryption import load_encrypted_session
from src.utils.live_logger import get_live_logger
from src.workflows.multi_date_booking import run_multi_date_booking

logger = logging.getLogger('bot_manager')

class BotWorker(threading.Thread):
    """Worker thread that runs a bot for a specific user"""

    def __init__(self, user_id: int, app_context):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.app_context = app_context
        self.running = True
        self.loop = None
        self.logged_bookings = set()  # Track bookings already logged to prevent duplicates

    def run(self):
        """Run the bot in a separate thread"""
        try:
            # Set up asyncio loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Run the bot
            self.loop.run_until_complete(self._run_bot())

        except Exception as e:
            logger.error(f"Bot worker error for user {self.user_id}: {e}", exc_info=True)
            with self.app_context:
                bot_instance = BotInstance.query.filter_by(user_id=self.user_id).first()
                if bot_instance:
                    bot_instance.status = 'error'
                    bot_instance.error_message = str(e)
                    bot_instance.stopped_at = datetime.utcnow()
                    db.session.commit()
        finally:
            if self.loop:
                self.loop.close()

    async def _run_bot(self):
        """Actually run the bot workflow"""
        with self.app_context:
            # Load user configuration
            bot_config = BotConfig.query.filter_by(user_id=self.user_id).first()
            if not bot_config:
                raise Exception("Bot configuration not found")

            # Load SpaceIQ session
            spaceiq_session = SpaceIQSession.query.filter_by(user_id=self.user_id).first()
            if not spaceiq_session or not spaceiq_session.is_valid:
                raise Exception("Valid SpaceIQ session not found")

            # Check if session data exists
            if not spaceiq_session.session_data:
                raise Exception("Session data is empty - please authenticate again")

            # Decrypt session data
            try:
                session_data = json.loads(spaceiq_session.session_data)
            except json.JSONDecodeError:
                # Session data is encrypted, decrypt it first
                from src.utils.auth_encryption import decrypt_data
                decrypted = decrypt_data(spaceiq_session.session_data)
                session_data = json.loads(decrypted)

            # Prepare configuration
            config = bot_config.to_dict()

            # Save session data to temporary file for the workflow to use
            import tempfile
            session_file = Path(tempfile.gettempdir()) / f"spaceiq_session_{self.user_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f)

            # Set auth file path in config
            config['auth_file'] = str(session_file)

            # Set user-specific screenshot directory for multiuser isolation
            from config import Config
            user = User.query.get(self.user_id)
            config['screenshots_dir'] = str(Config.get_user_screenshots_dir(user.username))

            logger.info(f"Starting bot for user {self.user_id}")

            # Update bot instance
            bot_instance = BotInstance.query.filter_by(user_id=self.user_id).first()
            bot_instance.add_log(f"Starting bot for building {config['building']}, floor {config['floor']}")
            db.session.commit()

        # Run the booking workflow
        try:
            # Create a callback to update status
            async def update_callback(event_type, data):
                with self.app_context:
                    bot_instance = BotInstance.query.filter_by(user_id=self.user_id).first()
                    if not bot_instance:
                        return

                    # Always update status to running when any callback is received
                    bot_instance.status = 'running'
                    if not bot_instance.started_at:
                        bot_instance.started_at = datetime.utcnow()

                    # Get live logger for UI
                    live_logger = get_live_logger(self.user_id)

                    if event_type == 'round_start':
                        bot_instance.current_round = data.get('round', 0)
                        round_msg = f"🔁 Round {data.get('round')} started"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(round_msg, 'info', round=data.get('round'), activity='Starting booking attempts')
                        bot_instance.set_activity(f"Round {data.get('round')} - Starting booking attempts")

                    elif event_type == 'operation':
                        # Detailed operation updates
                        operation = data.get('operation', '')
                        details = data.get('details', '')
                        op_msg = f"🔧 {operation}{' - ' + details if details else ''}"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(op_msg, 'info', operation=operation, details=details)
                        bot_instance.set_activity(f"{operation}{' - ' + details if details else ''}")

                    elif event_type == 'progress':
                        # Progress updates for current round
                        current = data.get('current', 0)
                        total = data.get('total', 0)
                        progress_msg = f"📊 Progress: {current}/{total} dates processed"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(progress_msg, 'info', current=current, total=total, activity='Processing dates')
                        bot_instance.set_activity(f"Processing dates: {current}/{total}")

                    elif event_type == 'booking_success':
                        bot_instance.successful_bookings += 1
                        desk = data.get('desk', 'Unknown')
                        date = data.get('date', 'Unknown')
                        round_num = data.get('round', bot_instance.current_round)
                        success_msg = f"✅ SUCCESS: Booked desk {desk} for {date}"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(success_msg, 'success', date=date, desk=desk, round=round_num,
                                         activity=f"Successfully booked desk {desk} for {date}")
                        bot_instance.set_activity(f"Successfully booked desk {desk} for {date}")

                        # Use in-memory tracking to prevent duplicates (more reliable than database check)
                        booking_key = (date, desk, 'success')
                        if booking_key not in self.logged_bookings:
                            self.logged_bookings.add(booking_key)
                            # Add to history only if not already logged
                            history = BookingHistory(
                                user_id=self.user_id,
                                date=date,
                                desk_number=desk,
                                status='success',
                                round_number=round_num
                            )
                            db.session.add(history)

                    elif event_type == 'booking_failed':
                        bot_instance.failed_attempts += 1
                        date = data.get('date', 'Unknown')
                        reason = data.get('reason', 'Unknown error')
                        round_num = data.get('round', bot_instance.current_round)
                        failed_msg = f"❌ FAILED: Could not book for {date} - {reason}"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(failed_msg, 'error', date=date, reason=reason, round=round_num,
                                         activity=f"Failed to book for {date} - {reason}")
                        bot_instance.set_activity(f"Failed to book for {date} - {reason}")

                        # Add to history
                        history = BookingHistory(
                            user_id=self.user_id,
                            date=date,
                            status='failed',
                            round_number=round_num,
                            error_message=reason
                        )
                        db.session.add(history)

                    elif event_type == 'booking_attempt':
                        date = data.get('date', 'Unknown')
                        desk = data.get('desk', 'Unknown desk')
                        attempt = data.get('attempt', 1)
                        attempt_msg = f"🎯 Attempt {attempt}: Trying to book {desk} for {date}"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(attempt_msg, 'info', date=date, desk=desk, attempt=attempt,
                                         activity=f"Attempting to book {desk} for {date}")
                        bot_instance.set_activity(f"Attempting to book {desk} for {date}")

                    elif event_type == 'checking_bookings':
                        check_msg = "🔍 Checking existing bookings..."
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(check_msg, 'info', activity="Checking existing bookings")
                        bot_instance.set_activity("Checking existing bookings")

                    elif event_type == 'found_existing':
                        date = data.get('date', 'Unknown')
                        exist_msg = f"✓ Already booked for {date}"
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(exist_msg, 'warning', date=date, activity=f"Found existing booking for {date}")
                        bot_instance.set_activity(f"Found existing booking for {date}")

                    elif event_type == 'navigating':
                        location = data.get('location', 'SpaceIQ')
                        nav_msg = f"🌐 Navigating to {location}..."
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(nav_msg, 'info', location=location, activity=f"Navigating to {location}")
                        bot_instance.set_activity(f"Navigating to {location}")

                    elif event_type == 'waiting':
                        action = data.get('action', 'refresh')
                        seconds = data.get('seconds', 30)
                        wait_msg = f"⏳ Waiting {seconds}s before {action}..."
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(wait_msg, 'info', action=action, seconds=seconds,
                                         activity=f"Waiting {seconds} seconds before {action}")
                        bot_instance.set_activity(f"Waiting {seconds} seconds before {action}")

                    elif event_type == 'browser_restart':
                        round_num = data.get('round', 0)
                        restart_msg = f"🔄 Restarting browser (round {round_num})..."
                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(restart_msg, 'warning', round=round_num,
                                         activity=f"Restarting browser to prevent timeouts")
                        bot_instance.set_activity(f"Restarting browser to prevent timeouts")

                    elif event_type == 'log':
                        level = data.get('level', 'info')
                        message = data.get('message', '')
                        # Add emoji based on level for better visibility
                        if level == 'success':
                            message = f"✅ {message}"
                            # Check if this is a booking success message
                            if 'successfully booked' in message.lower() or 'booking verified' in message.lower():
                                bot_instance.successful_bookings += 1
                        elif level == 'error':
                            message = f"❌ {message}"
                            # Check if this is a booking failure message
                            if 'booking verification failed' in message.lower() or 'could not locate desk' in message.lower():
                                bot_instance.failed_attempts += 1
                        elif level == 'warning':
                            message = f"⚠️ {message}"
                        elif level == 'info':
                            message = f"ℹ️ {message}"
                            # Extract progress from info messages
                            if 'attempting booking for' in message.lower() and '(' in message:
                                import re
                                match = re.search(r'\((\d+)\/(\d+)\)', message)
                                if match:
                                    bot_instance.current_round = max(bot_instance.current_round, int(match.group(1)))

                        # Only log to live logger - no more duplicate database logging
                        live_logger.add_log(message, level)

                    db.session.commit()

            # Run the original workflow with UI capture
            results = await self._run_original_workflow_with_callback(config, update_callback)

            # Bot completed successfully
            with self.app_context:
                bot_instance = BotInstance.query.filter_by(user_id=self.user_id).first()
                bot_instance.status = 'stopped'
                bot_instance.stopped_at = datetime.utcnow()
                bot_instance.add_log("Bot completed successfully", 'success')
                db.session.commit()

            logger.info(f"Bot completed for user {self.user_id}")

        except Exception as e:
            logger.error(f"Bot execution error for user {self.user_id}: {e}", exc_info=True)
            with self.app_context:
                bot_instance = BotInstance.query.filter_by(user_id=self.user_id).first()
                bot_instance.status = 'error'
                bot_instance.error_message = str(e)
                bot_instance.stopped_at = datetime.utcnow()
                bot_instance.add_log(f"Error: {str(e)}", 'error')
                db.session.commit()

    async def _run_original_workflow_with_callback(self, config: dict, callback):
        """
        Run the original booking workflow with enhanced logging for web interface
        """
        try:
            await callback('operation', {'operation': 'Starting bot', 'details': f'Building {config["building"]}, Floor {config["floor"]}'})

            # Import the original workflow
            from src.workflows.multi_date_booking import MultiDateBookingWorkflow

            # Create a wrapper logger that forwards to callback
            class CallbackLogger:
                def __init__(self, callback):
                    self.callback = callback

                def info(self, message):
                    # Forward to callback in a non-blocking way
                    try:
                        asyncio.create_task(self.callback('log', {'message': message, 'level': 'info'}))
                    except Exception as e:
                        print(f"Error in CallbackLogger.info: {e}")

                def error(self, message):
                    try:
                        asyncio.create_task(self.callback('log', {'message': message, 'level': 'error'}))
                    except Exception as e:
                        print(f"Error in CallbackLogger.error: {e}")

                def warning(self, message):
                    try:
                        asyncio.create_task(self.callback('log', {'message': message, 'level': 'warning'}))
                    except Exception as e:
                        print(f"Error in CallbackLogger.warning: {e}")

                def success(self, message):
                    try:
                        asyncio.create_task(self.callback('log', {'message': message, 'level': 'success'}))
                    except Exception as e:
                        print(f"Error in CallbackLogger.success: {e}")

                def _update_activity_from_message(self, message, call_callback=True):
                    """Extract meaningful activity from log messages"""
                    try:
                        message_lower = message.lower()

                        # Only skip callback if explicitly requested (to avoid duplicates)
                        # For operational messages, we want to allow callbacks
                        if not call_callback:
                            return

                        # Check for booking success/failure first (most important for history)
                        if any(keyword in message_lower for keyword in [
                            'successfully booked', 'booking verified', 'success: booked'
                        ]):
                            # Extract date and desk from success message
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
                            desk_match = re.search(r'desk\s+([A-Z0-9.-]+)', message_lower) or re.search(r'([A-Z0-9.-]+\s*desk)', message_lower)

                            if date_match:
                                date = date_match.group(1)
                                desk = desk_match.group(1) if desk_match else 'Unknown'

                                # Trigger booking success event
                                asyncio.create_task(self.callback('booking_success', {
                                    'date': date,
                                    'desk': desk
                                }))

                        elif any(keyword in message_lower for keyword in [
                            'booking failed', 'booking verification failed', 'could not locate desk'
                        ]):
                            # Extract date from failure message
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)

                            if date_match:
                                date = date_match.group(1)
                                reason = 'Booking failed'

                                # Trigger booking failed event
                                asyncio.create_task(self.callback('booking_failed', {
                                    'date': date,
                                    'reason': reason
                                }))

                        # Process essential operational events so user can see what's happening
                        elif 'attempting booking for' in message_lower:
                            # Extract date and progress from message like "Attempting booking for 2025-11-25 (2/5)"
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
                            progress_match = re.search(r'\((\d+)\/(\d+)\)', message)

                            if date_match:
                                date = date_match.group(1)
                                # Trigger booking attempt event
                                asyncio.create_task(self.callback('booking_attempt', {
                                    'date': date,
                                    'attempt': 1
                                }))

                                # Also trigger operation event so user sees current activity
                                if progress_match:
                                    current = int(progress_match.group(1))
                                    total = int(progress_match.group(2))
                                    asyncio.create_task(self.callback('operation', {
                                        'operation': f'Trying to book {date}',
                                        'details': f'Progress: {current}/{total}'
                                    }))
                                else:
                                    asyncio.create_task(self.callback('operation', {
                                        'operation': f'Trying to book {date}',
                                        'details': 'Checking availability'
                                    }))

                        elif 'loading floor map for' in message_lower:
                            # Extract date from message like "Loading floor map for 2025-11-25..."
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
                            if date_match:
                                date = date_match.group(1)
                                asyncio.create_task(self.callback('operation', {
                                    'operation': f'Loading floor map for {date}',
                                    'details': 'Checking desk availability'
                                }))

                        elif 'checking available' in message_lower and 'desks' in message_lower:
                            asyncio.create_task(self.callback('operation', {
                                'operation': 'Scanning for available desks',
                                'details': 'Checking which desks are free'
                            }))

                        elif 'found' in message_lower and 'available desks' in message_lower:
                            import re
                            count_match = re.search(r'found (\d+) available desks', message_lower)
                            count = count_match.group(1) if count_match else 'some'
                            asyncio.create_task(self.callback('operation', {
                                'operation': f'Found {count} available desks',
                                'details': 'Attempting to book the best one'
                            }))

                        elif 'no available desks' in message_lower:
                            # Extract date if available
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
                            date_str = f" for {date_match.group(1)}" if date_match else ""
                            asyncio.create_task(self.callback('operation', {
                                'operation': f'No available desks{date_str}',
                                'details': 'Will try next date or wait for next round'
                            }))

                        elif 'successfully booked' in message_lower or 'booking verified' in message_lower:
                            # This is handled by the booking success callback above
                            pass

                        elif 'starting round' in message_lower:
                            import re
                            round_match = re.search(r'round (\d+)', message_lower)
                            round_num = round_match.group(1) if round_match else 'unknown'
                            asyncio.create_task(self.callback('round_start', {
                                'round': int(round_num) if round_num.isdigit() else 1
                            }))

                        elif 'bot stopped' in message_lower:
                            asyncio.create_task(self.callback('operation', {
                                'operation': 'Bot stopped',
                                'details': 'Bot process terminated'
                            }))

                    except:
                        # Don't let activity updates break the logging
                        pass

            # Update status to show we're running the workflow
            await callback('operation', {'operation': 'Running booking workflow', 'details': 'Starting automated booking process'})

            # Import and use the web mode workflow which accepts config
            from src.workflows.multi_date_booking import run_multi_date_booking_web_mode

            # Run the original workflow designed for web mode
            results = await run_multi_date_booking_web_mode(
                config=config,
                web_logger=CallbackLogger(callback),
                headless=True,
                continuous_loop=True,  # Keep trying until all dates are booked
                skip_validation=True,
                app_context=self.app_context,  # Pass app context for database updates
                user_id=self.user_id  # Pass user_id to allow config reloading
            )

            await callback('log', {'message': f'Workflow completed. Booked {len([k for k, v in results.items() if v])} dates.', 'level': 'success'})
            return results

        except Exception as e:
            await callback('log', {'message': f'Workflow error: {str(e)}', 'level': 'error'})
            raise

    def stop(self):
        """Stop the bot gracefully"""
        logger.info(f"Stopping bot for user {self.user_id}")
        self.running = False

        # Set a timeout for graceful shutdown
        shutdown_timeout = 5.0  # 5 seconds

        # Cancel the asyncio event loop gracefully
        if self.loop and not self.loop.is_closed():
            # Create a shutdown task with timeout
            async def shutdown_gracefully():
                try:
                    # Cancel all running tasks except this one
                    tasks = [task for task in asyncio.all_tasks(self.loop)
                            if not task.done() and task != asyncio.current_task()]

                    # Wait for tasks to cancel gracefully
                    if tasks:
                        await asyncio.wait_for(
                            asyncio.gather(*[task.cancel() for task in tasks], return_exceptions=True),
                            timeout=shutdown_timeout
                        )

                    # Stop the loop
                    self.loop.stop()
                except asyncio.TimeoutError:
                    logger.warning(f"Bot shutdown timed out for user {self.user_id}")
                    # Force stop
                    self.loop.stop()
                except Exception as e:
                    logger.error(f"Error during bot shutdown for user {self.user_id}: {e}")
                    self.loop.stop()

            # Schedule shutdown task
            if self.loop.is_running():
                asyncio.run_coroutine_threadsafe(shutdown_gracefully(), self.loop)
            else:
                # Loop not running, just stop it
                self.loop.stop()

        logger.info(f"Bot stop signal sent for user {self.user_id}")


class BotManager:
    """Manages multiple bot instances for different users"""

    def __init__(self, app):
        self.app = app
        self.running_bots: Dict[int, BotWorker] = {}
        self.lock = threading.Lock()

    def start_bot(self, user_id: int) -> tuple[bool, str]:
        """Start a bot for a specific user"""
        with self.lock:
            # Check if already running
            if user_id in self.running_bots:
                worker = self.running_bots[user_id]
                if worker.is_alive():
                    return False, "Bot is already running"
                else:
                    # Clean up dead thread
                    del self.running_bots[user_id]

            with self.app.app_context():
                # Check if user exists
                user = User.query.get(user_id)
                if not user:
                    return False, "User not found"

                # Check if configuration exists
                bot_config = BotConfig.query.filter_by(user_id=user_id).first()
                if not bot_config:
                    return False, "Bot configuration not found. Please configure your bot first."

                # Check if SpaceIQ session exists
                spaceiq_session = SpaceIQSession.query.filter_by(user_id=user_id).first()
                if not spaceiq_session or not spaceiq_session.is_valid:
                    return False, "Valid SpaceIQ session not found. Please authenticate with SpaceIQ first."

                # Get or create bot instance
                bot_instance = BotInstance.query.filter_by(user_id=user_id).first()
                if not bot_instance:
                    bot_instance = BotInstance(user_id=user_id)
                    db.session.add(bot_instance)

                # Reset bot instance
                bot_instance.status = 'running'
                bot_instance.started_at = datetime.utcnow()
                bot_instance.stopped_at = None
                bot_instance.current_round = 0
                bot_instance.successful_bookings = 0
                bot_instance.failed_attempts = 0
                bot_instance.error_message = None
                bot_instance.clear_logs()
                bot_instance.add_log("Bot starting...")

                db.session.commit()

            # Start worker thread
            worker = BotWorker(user_id, self.app.app_context())
            worker.start()

            self.running_bots[user_id] = worker

            logger.info(f"Started bot for user {user_id}")
            return True, "Bot started successfully"

    def stop_bot(self, user_id: int) -> tuple[bool, str]:
        """Stop a bot for a specific user"""
        with self.lock:
            if user_id not in self.running_bots:
                return False, "Bot is not running"

            worker = self.running_bots[user_id]

            # Update database first (in case bot doesn't respond)
            with self.app.app_context():
                from src.utils.live_logger import get_live_logger

                bot_instance = BotInstance.query.filter_by(user_id=user_id).first()
                if bot_instance:
                    bot_instance.status = 'stopped'
                    bot_instance.stopped_at = datetime.utcnow()
                    bot_instance.add_log("Bot stop requested by user")

                    # Clear live logs for next session
                    live_logger = get_live_logger(user_id)
                    live_logger.clear_logs()

                    db.session.commit()

            # Stop the worker
            worker.stop()

            # Wait a moment for graceful shutdown
            import time
            time.sleep(1)

            # Force remove from running bots (even if thread doesn't stop immediately)
            if user_id in self.running_bots:
                del self.running_bots[user_id]

            logger.info(f"Stopped bot for user {user_id}")
            return True, "Bot stopped successfully"

    def get_bot_status(self, user_id: int) -> Optional[dict]:
        """Get bot status for a specific user"""
        with self.app.app_context():
            bot_instance = BotInstance.query.filter_by(user_id=user_id).first()
            if bot_instance:
                return bot_instance.to_dict()
            return None

    def is_bot_running(self, user_id: int) -> bool:
        """Check if bot is running for a user"""
        with self.lock:
            if user_id in self.running_bots:
                worker = self.running_bots[user_id]
                return worker.is_alive()
            return False

    def cleanup_dead_threads(self):
        """Remove dead threads from running bots"""
        with self.lock:
            dead_bots = []
            for user_id, worker in self.running_bots.items():
                if not worker.is_alive():
                    dead_bots.append(user_id)

            for user_id in dead_bots:
                del self.running_bots[user_id]
                logger.info(f"Cleaned up dead bot worker for user {user_id}")

    def stop_all_bots(self):
        """Stop all running bots (for shutdown)"""
        with self.lock:
            for user_id in list(self.running_bots.keys()):
                self.stop_bot(user_id)
