"""
Bot Supervisor - Automatic Restart and Recovery System

This module provides a supervisor that manages the bot lifecycle with automatic
restart capabilities and comprehensive crash recovery.
"""

import asyncio
import logging
import sys
import os
import time
from typing import Optional, Callable

# Add the parent directory to Python path to import config and utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from utils.crash_handler import create_crash_handler, CrashHandler

# Configure logging
supervisor_logger = logging.getLogger(__name__)

class BotSupervisor:
    """Supervisor that manages bot lifecycle with automatic restart"""
    
    def __init__(self, bot_main_func: Callable, crash_handler: Optional[CrashHandler] = None):
        self.bot_main_func = bot_main_func
        self.crash_handler = crash_handler or create_crash_handler(
            max_restart_attempts=Config.MAX_RESTART_ATTEMPTS,
            restart_delay_base=Config.RESTART_DELAY_BASE,
            emergency_channel_id=Config.get_emergency_channel_id(),
            emergency_token=Config.DISCORD_TOKEN
        )
        
        self.is_running = False
        self.should_stop = False
        self.successful_runs = 0
        self.supervisor_start_time = time.time()
        
        # Set up crash handler callbacks
        self.crash_handler.set_shutdown_callback(self._on_final_shutdown)
        
        supervisor_logger.info("Bot supervisor initialized")
    
    async def _on_final_shutdown(self):
        """Called when max restarts exceeded"""
        supervisor_logger.critical("Final shutdown initiated by crash handler")
        self.should_stop = True
        self.is_running = False
    
    async def _run_bot_with_recovery(self):
        """Run the bot with crash recovery"""
        while not self.should_stop:
            try:
                supervisor_logger.info(f"Starting bot (attempt {self.crash_handler.restart_count + 1})")
                self.is_running = True
                
                # Reset restart count if we've had a successful long run
                current_uptime = time.time() - self.crash_handler.start_time
                if current_uptime > 3600 and self.crash_handler.restart_count > 0:  # 1 hour
                    supervisor_logger.info("Bot has been stable for 1 hour, resetting restart count")
                    self.crash_handler.reset_restart_count()
                
                # Run the main bot function
                await self.bot_main_func()
                
                # If we reach here, the bot stopped normally
                supervisor_logger.info("Bot stopped normally")
                self.successful_runs += 1
                break
                
            except KeyboardInterrupt:
                supervisor_logger.info("Keyboard interrupt received, stopping supervisor")
                self.should_stop = True
                break
                
            except SystemExit as e:
                supervisor_logger.warning(f"SystemExit received: {e}")
                if "Maximum restart attempts exceeded" in str(e):
                    self.should_stop = True
                break
                
            except Exception as e:
                supervisor_logger.error(f"Bot crashed with exception: {e}")
                
                # Handle the crash
                should_restart = await self.crash_handler.handle_crash(e, {
                    'supervisor_uptime': time.time() - self.supervisor_start_time,
                    'successful_runs': self.successful_runs,
                    'restart_attempt': self.crash_handler.restart_count + 1
                })
                
                if not should_restart:
                    supervisor_logger.critical("Crash handler decided not to restart, stopping supervisor")
                    self.should_stop = True
                    break
                
                supervisor_logger.warning("Preparing to restart bot...")
                
                # Brief pause before restart attempt
                await asyncio.sleep(1)
        
        self.is_running = False
        supervisor_logger.info("Bot supervisor stopped")
    
    async def start(self):
        """Start the supervised bot"""
        if self.is_running:
            supervisor_logger.warning("Supervisor is already running")
            return
        
        supervisor_logger.info("Starting bot supervisor...")
        
        try:
            await self._run_bot_with_recovery()
        except Exception as e:
            supervisor_logger.critical(f"Critical error in supervisor: {e}", exc_info=True)
            raise
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the supervised bot"""
        supervisor_logger.info("Stopping bot supervisor...")
        self.should_stop = True
    
    def get_supervisor_stats(self):
        """Get supervisor statistics"""
        current_time = time.time()
        supervisor_uptime = current_time - self.supervisor_start_time
        
        crash_stats = self.crash_handler.get_crash_stats()
        
        return {
            'supervisor_uptime': supervisor_uptime,
            'successful_runs': self.successful_runs,
            'is_running': self.is_running,
            'should_stop': self.should_stop,
            'supervisor_start_time': self.supervisor_start_time,
            'crash_handler_stats': crash_stats
        }


def create_supervised_bot(bot_main_func: Callable, 
                         max_restart_attempts: Optional[int] = None,
                         restart_delay_base: Optional[int] = None) -> BotSupervisor:
    """Factory function to create a supervised bot"""
    
    # Use config values or provided overrides
    max_attempts = max_restart_attempts or Config.MAX_RESTART_ATTEMPTS
    delay_base = restart_delay_base or Config.RESTART_DELAY_BASE
    
    # Create crash handler
    crash_handler = create_crash_handler(
        max_restart_attempts=max_attempts,
        restart_delay_base=delay_base,
        emergency_channel_id=Config.get_emergency_channel_id(),
        emergency_token=Config.DISCORD_TOKEN
    )
    
    return BotSupervisor(bot_main_func, crash_handler)
