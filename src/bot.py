import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import logging
import asyncio

# Add the parent directory to Python path to import config and utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from app.bootstrap import build_application
from app.runtime import BotRuntime
from utils.crash_handler import create_crash_handler
from utils.bot_supervisor import create_supervised_bot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
# Slash-command bot: no message content intent required.
intents.message_content = False
intents.guilds = True
# Disable privileged intents that require explicit approval
intents.members = False
intents.presences = False

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# Initialize global crash handler
crash_handler = create_crash_handler(
    max_restart_attempts=Config.MAX_RESTART_ATTEMPTS,
    restart_delay_base=Config.RESTART_DELAY_BASE,
    emergency_channel_id=Config.get_emergency_channel_id(),
    emergency_token=Config.DISCORD_TOKEN
)
app_instance = build_application(
    config=Config,
    bot=bot,
    crash_handler=crash_handler,
    logger_factory=logging.getLogger,
)
runtime = BotRuntime(
    bot=bot,
    config=Config,
    app_instance=app_instance,
    logger=logger,
)

async def _graceful_shutdown():
    """Gracefully stop background tasks and close the Discord client."""
    try:
        await app_instance.stop_modules()
    finally:
        try:
            await bot.close()
        except Exception:
            pass

# Register graceful shutdown with crash handler
crash_handler.set_shutdown_callback(_graceful_shutdown)

@bot.event
async def on_ready():
    """Discord on_ready event delegated to runtime."""
    await runtime.on_ready()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for slash commands."""
    logger.error(f"Slash command error: {error}", exc_info=True)
    message = f"Error: {error}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        logger.exception("Failed to send slash command error response")



async def main():
    """Main function to run the bot (without crash recovery)"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validation passed")
        
        # Get bot token
        token = Config.DISCORD_TOKEN
        if not token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        
        logger.info("Starting Discord bot...")
        await bot.start(token)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure DISCORD_TOKEN is set.")
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        print(f"Failed to start bot: {e}")
        raise

async def main_supervised():
    """Main function to run the bot with crash recovery and auto-restart"""
    logger.info("Starting bot with crash recovery and auto-restart...")
    
    # Create supervised bot
    supervisor = create_supervised_bot(main)
    
    try:
        # Start the supervised bot
        await supervisor.start()
    except KeyboardInterrupt:
        logger.info("Bot supervisor stopped by user")
        print("Bot supervisor stopped by user")
    except Exception as e:
        logger.critical(f"Critical error in bot supervisor: {e}", exc_info=True)
        print(f"Critical supervisor error: {e}")
        raise
    finally:
        # Get final stats
        stats = supervisor.get_supervisor_stats()
        logger.info(f"Final supervisor stats: {stats}")
        print(f"Final run stats: {stats['successful_runs']} successful runs, "
              f"{stats['crash_handler_stats']['total_crashes']} crashes")


if __name__ == "__main__":
    # Check if we should run with supervision (default) or without
    run_supervised = os.getenv('RUN_SUPERVISED', 'true').lower() == 'true'
    
    if run_supervised:
        print("Starting bot with crash recovery and auto-restart...")
        asyncio.run(main_supervised())
    else:
        print("Starting bot WITHOUT crash recovery (not recommended for production)")
        asyncio.run(main())


