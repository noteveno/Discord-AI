"""
Kamao AI Discord Bot - Main Entry Point
A powerful AI bot with per-user memory, multiple providers, and modern UI
"""
from dotenv import load_dotenv
load_dotenv()

import discord
import os
import json
import logging
from pathlib import Path

# Local imports
from src.bot import KamaoBot
from src.commands import setup_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Main')

# Load configurations
CONFIG_PATH = Path("config/config.json")
MODELS_PATH = Path("config/models.json")

if not CONFIG_PATH.exists():
    logger.error("config/config.json not found!")
    exit(1)

if not MODELS_PATH.exists():
    logger.error("config/models.json not found!")
    exit(1)

with open(CONFIG_PATH, encoding='utf-8') as f:
    config = json.load(f)

with open(MODELS_PATH, encoding='utf-8') as f:
    models_config = json.load(f)

# Create bot instance
bot = KamaoBot(config, models_config)

# Setup commands
setup_commands(bot)

@bot.event
async def on_ready():
    """Bot ready event with command syncing (FIXED: missing sync)"""
    logger.info(f'✅ {bot.user.name} (ID: {bot.user.id}) is now online!')
    logger.info(f'🌐 Connected to {len(bot.guilds)} guild(s)')
    
    channel_id = os.getenv('CHANNEL_ID')
    if channel_id:
        logger.info(f'📢 AI Channel ID: {channel_id}')
    else:
        logger.warning('⚠️ CHANNEL_ID not set in environment!')
    
    # Sync slash commands (FIXED: was missing)
    try:
        synced = await bot.tree.sync()
        logger.info(f'✅ Synced {len(synced)} slash command(s)')
        for cmd in synced:
            logger.info(f'  • /{cmd.name}')
    except Exception as e:
        logger.error(f'❌ Failed to sync commands: {e}')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="your messages | /help"
        ),
        status=discord.Status.online
    )
    
    logger.info('🚀 Bot is fully ready!')

@bot.event
async def on_message(message: discord.Message):
    """Message event handler"""
    if message.author == bot.user:
        return
    await bot.process_message(message)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    logger.error(f"Command error: {error}", exc_info=True)

# Start bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("❌ DISCORD_TOKEN not set in environment!")
        exit(1)
    
    channel_id = os.getenv('CHANNEL_ID')
    if not channel_id:
        logger.error("❌ CHANNEL_ID not set in environment!")
        exit(1)
    
    logger.info("🚀 Starting Kamao AI Bot...")
    
    import signal
    import sys
    
    def signal_handler(sig, frame):
        """Handle shutdown signals gracefully"""
        logger.info("🛑 Shutdown signal received, cleaning up...")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot.run(token, reconnect=True)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {e}", exc_info=True)
    finally:
        logger.info("✅ Bot shutdown complete")

