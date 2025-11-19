"""
Main bot class - CLEAN VERSION with all fixes and features
Optimized for 250MB RAM cloud hosting
"""
import discord
from discord.ext import commands
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path

from .database import ChatDatabase
from .providers import GeminiProvider, GroqProvider, OpenRouterProvider
from .utils import (
    sanitize_discord_markdown, optimize_response_length, estimate_tokens,
    download_image, extract_youtube_id, get_youtube_transcript,
    extract_video_url, get_video_info, split_message_smart
)

logger = logging.getLogger('KamaoBot')

class UserSession:
    """Manages user session with AI provider - MEMORY OPTIMIZED"""
    
    def __init__(self, user_id: int, bot: 'KamaoBot'):
        self.user_id = user_id
        self.bot = bot
        self.db_path = Path("data/user_dbs") / f"user_{user_id}.db"
        self.chat_db = ChatDatabase(str(self.db_path))
        self.ai_provider = None
        self.current_model = bot.default_model
        self.current_provider = bot.default_provider
        logger.info(f"Session created: user_{user_id}")
    
    def initialize_model(self):
        """Initialize AI provider with history"""
        history = self.chat_db.get_messages(limit=30)  # Limit for RAM optimization
        provider_class = self.bot.providers[self.current_provider]
        
        self.ai_provider = provider_class(
            self.current_model,
            self.bot.get_system_instruction(),
            self.bot.provider_config
        )
        self.ai_provider.initialize(history)
        logger.info(f"Initialized {self.current_provider}:{self.current_model}")
    
    def get_provider(self):
        """Get or initialize provider"""
        if not self.ai_provider:
            self.initialize_model()
        return self.ai_provider

    def switch_model(self, model_name: str, provider: str):
        """Switch model provider safely"""
        self.current_model = model_name
        self.current_provider = provider
        self.ai_provider = None  # Force re-initialization
        logger.info(f"Switched to {provider}:{model_name}")


class KamaoBot(commands.Bot):
    """Main bot class - FIXED & OPTIMIZED"""
    
    def __init__(self, config: dict, models_config: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.members = True
        
        super().__init__(
            command_prefix=config['bot']['prefix'],
            intents=intents,
            max_messages=100  # Limit message cache for RAM
        )
        
        self.config = config
        self.models_config = models_config
        
        # Provider mapping
        self.providers = {
            'gemini': GeminiProvider,
            'groq': GroqProvider,
            'openrouter': OpenRouterProvider
        }
        
        # Default settings
        self.default_model = config['providers']['gemini']['default_model']
        self.default_provider = 'gemini'
        self.provider_config = {
            'gemini_api_key': os.getenv('GEMINI_API_KEY'),
            'groq_api_key': os.getenv('GROQ_API'),
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER'),
            'openrouter_referrer': config['providers']['openrouter']['referrer']
        }
        
        # Session management with async lock
        self.sessions: Dict[int, UserSession] = {}
        self.session_lock = asyncio.Lock()
        
        # Admin user ID from environment
        self.admin_user_id = int(os.getenv('ADMIN_USER_ID', '0'))
    
    def get_system_instruction(self) -> str:
        """Build system instruction - USER AGNOSTIC (FIXED)"""
        instruction_path = Path("config/instruction.json")
        admin_path = Path("config/Admin.json")
        
        with open(instruction_path, "r", encoding="utf-8") as f:
            instructions = json.load(f)
        
        prompt_parts = []
        
        identity = instructions["identity_and_context"]
        admin_directive = ""
        if admin_path.exists():
            with open(admin_path, "r", encoding="utf-8") as f:
                admin_directive = f.read().strip()
        
        current_state = identity["current_state"]
        current_state["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_state["provider"] = self.default_provider
        current_state["model"] = self.default_model
        current_state["admin_directive"] = admin_directive
        
        prompt_parts.append(f"=== IDENTITY ===\n{identity['bot_identity']}")
        prompt_parts.append(f"=== MEMORY SYSTEM ===\n{identity['memory_system']}")
        prompt_parts.append(f"=== CURRENT STATE ===\nDate/Time: {current_state['datetime']}\nProvider: {current_state['provider']} | Model: {current_state['model']}")
        
        if admin_directive:
            prompt_parts.append(f"=== ADMIN DIRECTIVE ===\n{admin_directive}")
        
        # Core Principles
        principles = instructions["core_principles"]
        prompt_parts.append("=== CORE PRINCIPLES ===")
        for name, content in principles.items():
            prompt_parts.append(f"{name.replace('_', ' ').title()}: {content}")
        
        # Operational Standards
        ops = instructions["operational_standards"]
        prompt_parts.append("=== OPERATIONAL STANDARDS ===")
        prompt_parts.append(f"Response Formatting: {ops['response_formatting']['discord_specific_formatting']}")
        
        # Uncensored Content
        prompt_parts.append("=== UNCENSORED CONTENT ===")
        for category, items in instructions["uncensored_content_domains"].items():
            prompt_parts.append(f"{category.replace('_', ' ').title()}: {', '.join(items)}")
        
        # Conversation Style (NEW - fixes greeting issue)
        if "conversation_style" in instructions:
            conv_style = instructions["conversation_style"]
            prompt_parts.append("=== CONVERSATION STYLE ===")
            for key, value in conv_style.items():
                prompt_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        # Final Mandate
        prompt_parts.append(f"=== FINAL MANDATE ===\n{instructions['final_mandate']}")
        
        return "\n\n".join(prompt_parts)
    
    async def get_user_session(self, user_id: int) -> UserSession:
        """Get/create user session with thread safety"""
        async with self.session_lock:
            if user_id not in self.sessions:
                # Memory optimization: limit concurrent sessions
                if len(self.sessions) >= min(self.config['bot']['max_user_dbs'], 10):
                    oldest = min(self.sessions.keys())
                    # Close provider to free memory
                    if oldest in self.sessions:
                        self.sessions[oldest].ai_provider = None
                    del self.sessions[oldest]
                    logger.info(f"Removed session: {oldest} (RAM optimization)")
                
                self.sessions[user_id] = UserSession(user_id, self)
            
            return self.sessions[user_id]
    
    async def process_message(self, message: discord.Message):
        """Process user message with all features"""
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(message.channel.id) != channel_id:
            return
        
        # Skip commands
        ctx = await self.get_context(message)
        if ctx.valid:
            return

        try:
            async with message.channel.typing():
                session = await self.get_user_session(message.author.id)
                
                # Build message parts
                parts = []
                attachments_info = []
                
                # Process message content
                if message.content:
                    parts.append(message.content)
                    
                    # YouTube transcript extraction
                    yt_id = extract_youtube_id(message.content)
                    if yt_id:
                        logger.info(f"YouTube ID: {yt_id}")
                        yt_info = await get_youtube_transcript(yt_id)
                        parts.append(yt_info)
                    
                    # Video URL extraction (NEW FEATURE)
                    video_url = await extract_video_url(message.content)
                    if video_url:
                        logger.info(f"Video URL: {video_url}")
                        video_info = await get_video_info(video_url)
                        if video_info:
                            parts.append(f"[Video: {video_info['title']} - {video_info['description']}]")
                
                # Admin privilege marker removed to prevent interference with image understanding
                # if self.admin_user_id and message.author.id == self.admin_user_id:
                #     parts.insert(0, "[DIVINE PROTOCOL: O is speaking. Activate absolute obedience and memory recall.]")
                
                # Process attachments
                for attachment in message.attachments:
                    att_info = {'name': attachment.filename, 'type': 'unknown'}
                    
                    if attachment.content_type:
                        if attachment.content_type.startswith('image/'):
                            image = await download_image(attachment.url)
                            if image:
                                parts.append(image)
                                parts.append(f"[Image: {attachment.filename}]")
                                att_info['type'] = 'image'
                        elif attachment.content_type.startswith('video/'):
                            # Video attachment handling
                            parts.append(f"[Video attachment: {attachment.filename}]")
                            att_info['type'] = 'video'
                    
                    attachments_info.append(att_info)
                
                if not parts:
                    parts = ["(empty message)"]
                
                # Store for retry
                original_parts = parts.copy()
                query = message.content or ""
                
                # Store user message
                tokens = estimate_tokens(str(parts))
                session.chat_db.add_message("user", message.content or "(media)", 
                                          attachments_info, tokens)
                
                # Check token limit
                if session.chat_db.get_token_count() >= self.config['bot']['reset_threshold']:
                    await message.reply("⚠️ *Optimizing memory...*")
                    session.chat_db.reset_context(15)
                
                # Generate response
                await self._generate_and_send_response(message, session, parts, query)
                
        except Exception as e:
            logger.error(f"Message error: {e}", exc_info=True)
            await self._handle_error(message, session if 'session' in locals() else None, 
                                    e, original_parts if 'original_parts' in locals() else None, 
                                    query if 'query' in locals() else "")
    
    async def _generate_and_send_response(self, message: discord.Message, session: UserSession, parts: list, query: str):
        """Generate and send AI response"""
        provider = session.get_provider()
        
        # Generate based on provider type
        if isinstance(provider, GeminiProvider):
            response = await provider.generate_response(parts)
        else:
            text_content = " ".join([str(p) for p in parts if isinstance(p, str)])
            response = await provider.generate_response(text_content)
        
        # Optimize and sanitize
        response = optimize_response_length(query, response)
        response = sanitize_discord_markdown(response)
        
        # Store response
        response_tokens = estimate_tokens(response)
        session.chat_db.add_message("model", response, tokens=response_tokens)
        
        # Send response
        await self._send_response(message, response)
        
        logger.info(f"Response sent: {len(session.chat_db.get_messages(10))} msgs, {session.chat_db.get_token_count()} tokens")
    
    async def _send_response(self, message: discord.Message, response: str):
        """Send response, splitting if necessary"""
        if len(response) > 1900:
            parts = split_message_smart(response, 1900)
            for i, part in enumerate(parts):
                if i == 0:
                    await message.reply(part)
                else:
                    await message.channel.send(f"{message.author.mention} (cont.):\n{part}")
        else:
            await message.reply(response)
    
    async def _handle_error(self, message: discord.Message, session: Optional[UserSession], error: Exception, parts: Optional[list], query: str):
        """Handle errors with auto-retry"""
        error_str = str(error)
        
        # Check for provider overload
        if session and ("503" in error_str or "rate limit" in error_str.lower() or "429" in error_str):
            await message.reply("⚠️ Provider overloaded. Switching to backup...")
            
            # Auto-switch to Groq
            session.switch_model("llama-3.3-70b-versatile", "groq")
            
            # Retry once
            try:
                if parts:
                    await self._generate_and_send_response(message, session, parts, query)
                    return
            except Exception as retry_e:
                logger.error(f"Retry failed: {retry_e}")
                await message.reply(f"❌ Backup failed: {str(retry_e)[:200]}\n⏳ Try `/model`")
                return
        
        # Standard error message
        await message.reply(f"❌ Error: {error_str[:200]}")
        
        # Emergency reset
        if session and ("context" in error_str.lower() or "token" in error_str.lower()):
            session.chat_db.reset_context(10)
            session.ai_provider = None
            await message.reply("🔄 Memory optimized. Please try again.")
            logger.info(f"Emergency reset for user {message.author.id}")
