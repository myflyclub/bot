"""
Crash Handler and Error Tracking System

This module provides comprehensive crash detection, error tracking, and automatic
restart capabilities for the Oil Price Alert bot.
"""

import signal
import traceback
import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import discord

# Configure logging for crash handler
crash_logger = logging.getLogger(__name__)

@dataclass
class CrashEvent:
    """Data class for crash events"""
    timestamp: float
    timestamp_str: str
    error_type: str
    error_message: str
    stack_trace: str
    restart_count: int
    process_uptime: float
    context: Dict[str, Any]

class CrashHandler:
    """Comprehensive crash detection and recovery system"""
    
    def __init__(self, 
                 max_restart_attempts: int = 5,
                 restart_delay_base: int = 10,  # Base delay in seconds
                 restart_delay_max: int = 300,  # Maximum delay in seconds
                 emergency_channel_id: Optional[int] = None,
                 emergency_token: Optional[str] = None):
        
        self.max_restart_attempts = max_restart_attempts
        self.restart_delay_base = restart_delay_base
        self.restart_delay_max = restart_delay_max
        self.emergency_channel_id = emergency_channel_id
        self.emergency_token = emergency_token
        
        # Tracking state
        self.restart_count = 0
        self.start_time = time.time()
        self.last_crash_time: Optional[float] = None
        self.crash_history: list[CrashEvent] = []
        
        # Handlers
        self.restart_callback: Optional[Callable] = None
        self.shutdown_callback: Optional[Callable] = None
        
        # Install signal handlers
        self._install_signal_handlers()
        
        crash_logger.info("Crash handler initialized with max_attempts=%d", max_restart_attempts)
    
    def _install_signal_handlers(self):
        """Install signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            crash_logger.warning(f"Received signal {signum}, initiating graceful shutdown")
            # Ensure the async shutdown routine actually runs
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._handle_shutdown(f"Signal {signum} received"))
            except RuntimeError:
                # No running loop; run shutdown synchronously
                try:
                    asyncio.run(self._handle_shutdown(f"Signal {signum} received"))
                except Exception as e:
                    crash_logger.error(f"Error during synchronous shutdown: {e}")
        
        # Handle common termination signals
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, signal_handler)
            crash_logger.debug("Signal handlers installed successfully")
        except Exception as e:
            crash_logger.warning(f"Failed to install signal handlers: {e}")
    
    def set_restart_callback(self, callback: Callable):
        """Set callback function to be called on restart"""
        self.restart_callback = callback
        crash_logger.debug("Restart callback set")
    
    def set_shutdown_callback(self, callback: Callable):
        """Set callback function to be called on shutdown"""
        self.shutdown_callback = callback
        crash_logger.debug("Shutdown callback set")
    
    def _calculate_restart_delay(self) -> int:
        """Calculate restart delay with exponential backoff"""
        if self.restart_count == 0:
            return 0
        
        # Exponential backoff: base * (2 ^ (attempts - 1))
        delay = self.restart_delay_base * (2 ** (self.restart_count - 1))
        return min(delay, self.restart_delay_max)
    
    def _create_crash_event(self, error: Exception, context: Dict[str, Any] = None) -> CrashEvent:
        """Create a crash event from an exception"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        crash_event = CrashEvent(
            timestamp=current_time,
            timestamp_str=datetime.fromtimestamp(current_time, tz=timezone.utc).isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            restart_count=self.restart_count,
            process_uptime=uptime,
            context=context or {}
        )
        
        return crash_event
    
    async def _send_emergency_alert(self, crash_event: CrashEvent, is_final_crash: bool = False):
        """Send emergency Discord alert about crash"""
        if not self.emergency_channel_id or not self.emergency_token:
            crash_logger.warning("No emergency channel configured, skipping Discord alert")
            return
        
        try:
            # Create a minimal Discord client for emergency alerts
            intents = discord.Intents.default()
            intents.message_content = True
            emergency_bot = discord.Client(intents=intents)
            
            @emergency_bot.event
            async def on_ready():
                try:
                    channel = emergency_bot.get_channel(self.emergency_channel_id)
                    if not channel:
                        crash_logger.error(f"Emergency channel {self.emergency_channel_id} not found")
                        return
                    
                    # Create alert embed
                    embed = discord.Embed(
                        title="🚨 Bot Crash Alert",
                        description="Oil Price Alert Bot has crashed",
                        color=discord.Color.red() if is_final_crash else discord.Color.orange()
                    )
                    
                    embed.add_field(name="🔥 Error Type", value=crash_event.error_type, inline=True)
                    embed.add_field(name="📝 Error Message", value=crash_event.error_message[:1024], inline=False)
                    embed.add_field(name="🔄 Restart Attempt", value=f"{crash_event.restart_count}/{self.max_restart_attempts}", inline=True)
                    embed.add_field(name="⏱️ Uptime", value=f"{crash_event.process_uptime:.1f}s", inline=True)
                    embed.add_field(name="⏰ Crash Time", value=f"<t:{int(crash_event.timestamp)}:F>", inline=False)
                    
                    if is_final_crash:
                        embed.add_field(name="❌ Status", value="**MAX RESTARTS EXCEEDED - BOT STOPPED**", inline=False)
                        embed.add_field(name="🔧 Action Required", value="Manual intervention needed", inline=False)
                    else:
                        restart_delay = self._calculate_restart_delay()
                        embed.add_field(name="🔄 Next Action", value=f"Restarting in {restart_delay}s", inline=False)
                    
                    # Add stack trace as file if it's too long
                    if len(crash_event.stack_trace) > 1024:
                        # Create a file with the stack trace
                        import io
                        stack_file = discord.File(
                            io.StringIO(crash_event.stack_trace),
                            filename=f"crash_stack_trace_{int(crash_event.timestamp)}.txt"
                        )
                        await channel.send(embed=embed, file=stack_file)
                    else:
                        embed.add_field(name="📋 Stack Trace", value=f"```\n{crash_event.stack_trace[-1000:]}\n```", inline=False)
                        await channel.send(embed=embed)
                    
                    crash_logger.info("Emergency alert sent successfully")
                    
                except Exception as e:
                    crash_logger.error(f"Failed to send emergency alert: {e}")
                finally:
                    await emergency_bot.close()
            
            # Connect and send alert with timeout
            try:
                await asyncio.wait_for(emergency_bot.start(self.emergency_token), timeout=30)
            except asyncio.TimeoutError:
                crash_logger.error("Emergency alert timed out")
            except Exception as e:
                crash_logger.error(f"Emergency alert failed: {e}")
            
        except Exception as e:
            crash_logger.error(f"Critical error in emergency alert system: {e}")
    
    async def handle_crash(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """
        Handle a crash event and determine if restart should be attempted
        
        Returns:
            bool: True if restart should be attempted, False if bot should shutdown
        """
        crash_event = self._create_crash_event(error, context)
        self.crash_history.append(crash_event)
        self.last_crash_time = crash_event.timestamp
        
        crash_logger.error(f"CRASH DETECTED: {crash_event.error_type}: {crash_event.error_message}")
        crash_logger.error(f"Stack trace:\n{crash_event.stack_trace}")
        
        # Check if we should attempt restart
        if self.restart_count >= self.max_restart_attempts:
            crash_logger.critical(f"Max restart attempts ({self.max_restart_attempts}) exceeded, shutting down")
            await self._send_emergency_alert(crash_event, is_final_crash=True)
            await self._handle_shutdown("Maximum restart attempts exceeded")
            return False
        
        # Increment restart count
        self.restart_count += 1
        crash_logger.warning(f"Attempting restart {self.restart_count}/{self.max_restart_attempts}")
        
        # Send emergency alert
        await self._send_emergency_alert(crash_event, is_final_crash=False)
        
        # Calculate and apply restart delay
        restart_delay = self._calculate_restart_delay()
        if restart_delay > 0:
            crash_logger.info(f"Waiting {restart_delay} seconds before restart...")
            await asyncio.sleep(restart_delay)
        
        return True
    
    async def _handle_shutdown(self, reason: str):
        """Handle graceful shutdown"""
        crash_logger.warning(f"Initiating shutdown: {reason}")
        
        # Call shutdown callback if set
        if self.shutdown_callback:
            try:
                if asyncio.iscoroutinefunction(self.shutdown_callback):
                    await self.shutdown_callback()
                else:
                    self.shutdown_callback()
            except Exception as e:
                crash_logger.error(f"Error in shutdown callback: {e}")
        
        crash_logger.info("Shutdown completed")
        # Ensure the process exits so the terminal is released
        try:
            await asyncio.sleep(0)
        finally:
            raise SystemExit(0)
    
    def get_crash_stats(self) -> Dict[str, Any]:
        """Get crash statistics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            'restart_count': self.restart_count,
            'max_restart_attempts': self.max_restart_attempts,
            'current_uptime': uptime,
            'total_crashes': len(self.crash_history),
            'last_crash_time': self.last_crash_time,
            'start_time': self.start_time,
            'crash_history': [
                {
                    'timestamp': crash.timestamp,
                    'error_type': crash.error_type,
                    'error_message': crash.error_message,
                    'restart_count': crash.restart_count,
                    'uptime': crash.process_uptime
                }
                for crash in self.crash_history[-10:]  # Last 10 crashes only
            ]
        }
    
    def reset_restart_count(self):
        """Reset restart count (useful after successful long uptime)"""
        if self.restart_count > 0:
            crash_logger.info(f"Resetting restart count from {self.restart_count} to 0")
            self.restart_count = 0


def create_crash_handler(max_restart_attempts: int = 5,
                        restart_delay_base: int = 10,
                        emergency_channel_id: Optional[int] = None,
                        emergency_token: Optional[str] = None) -> CrashHandler:
    """Factory function to create a crash handler"""
    return CrashHandler(
        max_restart_attempts=max_restart_attempts,
        restart_delay_base=restart_delay_base,
        emergency_channel_id=emergency_channel_id,
        emergency_token=emergency_token
    )


# Global exception handler decorator
def with_crash_recovery(crash_handler: CrashHandler):
    """Decorator to wrap functions with crash recovery"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    crash_logger.error(f"Exception in {func.__name__}: {e}")
                    should_restart = await crash_handler.handle_crash(e, {
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    })
                    if not should_restart:
                        raise SystemExit("Maximum restart attempts exceeded")
                    return None
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    crash_logger.error(f"Exception in {func.__name__}: {e}")
                    # For sync functions, we can't await, so just log and re-raise
                    raise
            return sync_wrapper
    return decorator
