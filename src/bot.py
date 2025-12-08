"""
Kamao AI Discord Bot - Core Bot Class
Handles user sessions, message processing, and provider management
"""
import discord
from discord.ext import commands
import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime

from .database import ChatDatabase
from .providers import GeminiProvider, GroqProvider, OpenRouterProvider, AIProvider
from .utils import (
    sanitize_discord_markdown, 
    optimize_response_length, 
    split_message_smart,
    estimate_tokens,
    download_image,
    extract_youtube_id,
    get_youtube_transcript
)

logger = logging.getLogger('Bot')


class UserSession:
    """Manages per-user state including database and AI provider"""
    
    def __init__(self, user_id: int, config: dict, models_config: dict):
        self.user_id = user_id
        self.config = config
        self.models_config = models_config
        
        # Initialize with default provider/model from config
        default_provider = list(models_config.keys())[0]  # gemini
        provider_config = config.get('providers', {}).get(default_provider, {})
        default_model = provider_config.get('default_model', list(models_config[default_provider].keys())[0])
        
        self.current_provider = default_provider
        self.current_model = default_model
        self.ai_provider: Optional[AIProvider] = None
        
        # Initialize user database
        db_path = Path(f"data/user_dbs/{user_id}.db")
        self.chat_db = ChatDatabase(str(db_path))
        
        self._lock = asyncio.Lock()
        logger.info(f"Created session for user {user_id} with {self.current_provider}/{self.current_model}")
    
    def switch_model(self, model_id: str, provider: str, reset_context: bool = False) -> None:
        """Switch to a different model/provider
        
        Args:
            model_id: The model identifier
            provider: The provider name (gemini, groq, openrouter)
            reset_context: If True, clears provider's in-memory conversation history
        """
        if provider not in self.models_config:
            raise ValueError(f"Unknown provider: {provider}")
        if model_id not in self.models_config[provider]:
            raise ValueError(f"Unknown model: {model_id}")
        
        # Check if actually switching
        is_provider_change = provider != self.current_provider
        is_model_change = model_id != self.current_model
        
        self.current_provider = provider
        self.current_model = model_id
        
        # Always reset provider instance to reinitialize with new model
        self.ai_provider = None
        
        # Clear internal conversation state if requested or switching providers
        if reset_context or is_provider_change:
            self._reset_provider_state()
        
        logger.info(f"User {self.user_id} switched to {provider}/{model_id} (reset={reset_context or is_provider_change})")
    
    def _reset_provider_state(self) -> None:
        """Reset provider's internal conversation state (not database)"""
        self.ai_provider = None
        # Mark that next initialization should use limited history
        self._use_fresh_context = True
    
    def reset_memory(self, keep_last: int = 0) -> None:
        """Reset both database and provider state
        
        Args:
            keep_last: Number of recent messages to preserve (0 = full wipe)
        """
        if keep_last > 0:
            self.chat_db.reset_context(keep_last)
        else:
            self.chat_db.clear_all()
        
        self.ai_provider = None
        self._use_fresh_context = True
        logger.info(f"User {self.user_id} memory reset (kept={keep_last})")
    
    def get_provider_instance(self, api_config: dict, http_session: Optional[aiohttp.ClientSession] = None) -> AIProvider:
        """Get or create the current AI provider instance"""
        if self.ai_provider is not None:
            return self.ai_provider
        
        # Load system instruction
        instruction = self._load_system_instruction()
        
        provider_classes = {
            'gemini': GeminiProvider,
            'groq': GroqProvider,
            'openrouter': OpenRouterProvider
        }
        
        provider_class = provider_classes.get(self.current_provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {self.current_provider}")
        
        self.ai_provider = provider_class(
            model_name=self.current_model,
            system_instruction=instruction,
            config=api_config,
            http_session=http_session
        )
        
        # Initialize with history (limited if fresh context requested)
        if getattr(self, '_use_fresh_context', False):
            # Fresh start - only load last 5 messages for minimal context
            history = self.chat_db.get_messages(5)
            self._use_fresh_context = False
        else:
            # Normal operation - load recent history
            history = self.chat_db.get_messages(50)
        
        self.ai_provider.initialize(history)
        
        return self.ai_provider
    
    def _load_system_instruction(self) -> str:
        """Load and format system instruction"""
        try:
            instruction_path = Path("config/instruction.json")
            admin_path = Path("config/Admin.json")
            
            instruction_data = {}
            admin_data = {}
            
            if instruction_path.exists():
                with open(instruction_path, encoding='utf-8') as f:
                    instruction_data = json.load(f)
            
            if admin_path.exists():
                with open(admin_path, encoding='utf-8') as f:
                    admin_data = json.load(f)
            
            # Build instruction string
            parts = []
            
            # Identity
            identity = instruction_data.get('identity_and_context', {})
            if identity.get('bot_identity'):
                parts.append(identity['bot_identity'])
            if identity.get('memory_system'):
                parts.append(identity['memory_system'])
            
            # Core principles
            principles = instruction_data.get('core_principles', {})
            for key, value in principles.items():
                if value:
                    parts.append(value)
            
            # Operational standards
            ops = instruction_data.get('operational_standards', {})
            formatting = ops.get('response_formatting', {})
            for key, value in formatting.items():
                if value:
                    parts.append(value)
            
            # Reasoning methodology
            reasoning = instruction_data.get('reasoning_methodology', {})
            for key, value in reasoning.items():
                if value:
                    parts.append(value)
            
            # Admin directive
            admin_user_id = os.getenv('ADMIN_USER_ID')
            if admin_user_id and str(self.user_id) == admin_user_id:
                if admin_data.get('CoreDirectives'):
                    parts.append(f"ADMIN MODE ACTIVE: {json.dumps(admin_data['CoreDirectives'])}")
            
            # Current state
            current_state = identity.get('current_state', {})
            state_str = f"\n\nCurrent: {datetime.utcnow().isoformat()} | Provider: {self.current_provider} | Model: {self.current_model}"
            parts.append(state_str)
            
            return "\n\n".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to load instruction: {e}")
            return "You are Kamao AI, a helpful Discord bot assistant."


class KamaoBot(discord.Client):
    """Main bot class with session management and message processing"""
    
    def __init__(self, config: dict, models_config: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(intents=intents)
        
        self.config = config
        self.models_config = models_config
        self.tree = discord.app_commands.CommandTree(self)
        
        # User session management
        self.user_sessions: Dict[int, UserSession] = {}
        self._session_locks: Dict[int, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        
        # Shared HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # API config from environment
        self._api_config = {
            'gemini_api_key': os.getenv('GEMINI_API_KEY'),
            'groq_api_key': os.getenv('GROQ_API'),
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY'),
            'openrouter_referrer': config.get('providers', {}).get('openrouter', {}).get('referrer', '')
        }
        
        logger.info("KamaoBot initialized")
    
    async def setup_hook(self) -> None:
        """Called when bot is ready to setup resources"""
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "KamaoBot/2.0"}
        )
        logger.info("HTTP session created")
    
    async def close(self) -> None:
        """Cleanup on shutdown"""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            logger.info("HTTP session closed")
        await super().close()
    
    async def get_user_session(self, user_id: int) -> UserSession:
        """Get or create a user session with proper locking"""
        # Get or create lock for this user
        async with self._global_lock:
            if user_id not in self._session_locks:
                self._session_locks[user_id] = asyncio.Lock()
            lock = self._session_locks[user_id]
        
        async with lock:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = UserSession(
                    user_id=user_id,
                    config=self.config,
                    models_config=self.models_config
                )
            return self.user_sessions[user_id]
    
    async def process_message(self, message: discord.Message) -> None:
        """Process incoming messages"""
        # Check if in AI channel
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(message.channel.id) != channel_id:
            return
        
        # Ignore bots
        if message.author.bot:
            return
        
        user_id = message.author.id
        content = message.content.strip()
        
        # Check for empty content (attachments only)
        if not content and not message.attachments:
            return
        
        try:
            # Show typing indicator
            async with message.channel.typing():
                await self._generate_response(message, user_id, content)
                
        except Exception as e:
            logger.error(f"Message processing error for user {user_id}: {e}", exc_info=True)
            try:
                await message.reply(
                    f"❌ **Error:** {str(e)[:200]}\n\n💡 Try `/model` to switch providers or `/reset` to clear context.",
                    mention_author=False
                )
            except:
                pass
    
    async def _generate_response(self, message: discord.Message, user_id: int, content: str) -> None:
        """Generate and send AI response"""
        session = await self.get_user_session(user_id)
        
        async with session._lock:
            # Build input parts
            parts = await self._build_input_parts(message, content)
            
            # Get text content for database
            text_content = content
            
            # Get provider (with failover)
            response_text = None
            providers_tried = []
            last_error = None
            
            # Try current provider first, then others
            provider_order = [session.current_provider] + [
                p for p in self.models_config.keys() 
                if p != session.current_provider
            ]
            
            for provider_name in provider_order:
                if provider_name in providers_tried:
                    continue
                providers_tried.append(provider_name)
                
                try:
                    # Switch provider if needed
                    if provider_name != session.current_provider:
                        default_model = self.config.get('providers', {}).get(provider_name, {}).get(
                            'default_model', 
                            list(self.models_config[provider_name].keys())[0]
                        )
                        session.switch_model(default_model, provider_name)
                        logger.warning(f"Failover to {provider_name}/{default_model} for user {user_id}")
                    
                    provider = session.get_provider_instance(self._api_config, self.http_session)
                    
                    # Generate response
                    if provider_name == 'gemini':
                        response_text = await provider.generate_response(parts)
                    else:
                        # Groq/OpenRouter only support text
                        response_text = await provider.generate_response(text_content)
                    
                    if response_text:
                        break
                        
                except Exception as e:
                    last_error = e
                    logger.error(f"Provider {provider_name} failed: {e}")
                    session.ai_provider = None  # Reset for retry
                    continue
            
            if not response_text:
                raise last_error or Exception("All providers failed")
            
            # Save to database
            input_tokens = estimate_tokens(text_content)
            output_tokens = estimate_tokens(response_text)
            
            # Build attachments list
            attachments = []
            for att in message.attachments:
                attachments.append({
                    'type': 'image' if att.content_type and 'image' in att.content_type else 'file',
                    'name': att.filename,
                    'url': att.url
                })
            
            session.chat_db.add_message('user', text_content, attachments, input_tokens)
            session.chat_db.add_message('model', response_text, None, output_tokens)
            
            # Sanitize and send response
            response_text = sanitize_discord_markdown(response_text)
            response_text = optimize_response_length(text_content, response_text)
            
            # Split if too long
            parts_to_send = split_message_smart(response_text, 1900)
            
            for i, part in enumerate(parts_to_send):
                if i == 0:
                    await message.reply(part, mention_author=False)
                else:
                    await message.channel.send(part)
    
    async def _build_input_parts(self, message: discord.Message, content: str) -> List[Any]:
        """Build input parts including text, images, and YouTube transcripts"""
        parts = []
        
        # Add text content
        if content:
            parts.append(content)
        
        # Process attachments
        for attachment in message.attachments:
            if attachment.content_type and 'image' in attachment.content_type:
                try:
                    image = await download_image(attachment.url, self.http_session)
                    if image:
                        parts.append(image)
                        logger.info(f"Added image attachment: {attachment.filename}")
                except Exception as e:
                    logger.warning(f"Failed to download image {attachment.filename}: {e}")
                    parts.append(f"[Image: {attachment.filename} - failed to load]")
        
        # Check for YouTube URLs
        youtube_id = extract_youtube_id(content) if content else None
        if youtube_id:
            try:
                transcript = await get_youtube_transcript(youtube_id, self.http_session)
                parts.append(f"\n\n{transcript}")
                logger.info(f"Added YouTube transcript for {youtube_id}")
            except Exception as e:
                logger.warning(f"Failed to get YouTube transcript: {e}")
        
        return parts if parts else ["."]
