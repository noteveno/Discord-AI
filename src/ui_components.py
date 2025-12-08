"""
Kamao AI - Clean Modern Discord UI Components
Minimalist design with strategic use of color and typography
"""
import discord
from discord.ext import commands
import logging
from typing import Optional, List, Callable
from datetime import datetime

logger = logging.getLogger('UI')


class Colors:
    """Modern color palette - Discord native colors"""
    PRIMARY = 0x5865F2      # Discord Blurple
    SECONDARY = 0x4E5058    # Dark gray
    SUCCESS = 0x3BA55C      # Green
    WARNING = 0xFAA61A      # Amber
    ERROR = 0xED4245        # Red
    INFO = 0x5865F2         # Blurple
    DARK = 0x2F3136         # Embed dark
    ACCENT = 0xEB459E       # Fuchsia


def create_embed(
    title: str,
    description: str = None,
    color: int = Colors.PRIMARY,
    footer: str = None
) -> discord.Embed:
    """Create a clean embed with minimal styling"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if footer:
        embed.set_footer(text=footer)
    return embed


def create_error_embed(message: str, suggestion: str = None) -> discord.Embed:
    """Create error embed with optional recovery suggestion"""
    embed = discord.Embed(
        title="Error",
        description=f"```{message[:400]}```",
        color=Colors.ERROR
    )
    if suggestion:
        embed.add_field(name="Suggestion", value=suggestion, inline=False)
    else:
        embed.add_field(
            name="Try",
            value="Use `/model` to switch providers or `/reset` to clear memory",
            inline=False
        )
    return embed


def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create success embed"""
    return discord.Embed(
        title=title,
        description=description,
        color=Colors.SUCCESS
    )


def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create info embed"""
    return discord.Embed(
        title=title,
        description=description,
        color=Colors.INFO
    )


class ConfirmView(discord.ui.View):
    """Clean confirmation dialog"""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.interaction: Optional[discord.Interaction] = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.interaction = interaction
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.interaction = interaction
        await interaction.response.edit_message(
            embed=create_embed("Cancelled", "Operation cancelled.", Colors.SECONDARY),
            view=None
        )
        self.stop()

    async def on_timeout(self):
        self.value = False


class ModelSelectorView(discord.ui.View):
    """Clean model selection with two-step flow"""
    
    PROVIDERS = {
        "gemini": {
            "name": "Google Gemini",
            "desc": "Multimodal AI with vision and grounding",
            "color": Colors.PRIMARY
        },
        "groq": {
            "name": "Groq",
            "desc": "Ultra-fast inference engine",
            "color": Colors.SUCCESS
        },
        "openrouter": {
            "name": "OpenRouter",
            "desc": "40+ free AI models",
            "color": Colors.ACCENT
        }
    }
    
    def __init__(self, user_id: int, bot, models_config: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bot = bot
        self.models_config = models_config
        self.current_page = 0
        self.selected_provider: Optional[str] = None
        self.model_options: List[discord.SelectOption] = []
        
        # Build provider dropdown
        self._add_provider_select()
    
    def _add_provider_select(self):
        """Add provider selection dropdown"""
        options = [
            discord.SelectOption(
                label=info["name"],
                value=provider,
                description=info["desc"]
            )
            for provider, info in self.PROVIDERS.items()
            if provider in self.models_config
        ]
        
        select = discord.ui.Select(
            placeholder="Select AI Provider",
            options=options,
            row=0
        )
        select.callback = self._on_provider_select
        self.add_item(select)
    
    async def _on_provider_select(self, interaction: discord.Interaction):
        """Handle provider selection"""
        self.selected_provider = interaction.data['values'][0]
        self.current_page = 0
        
        # Build model options for this provider
        session = await self.bot.get_user_session(self.user_id)
        self.model_options = []
        
        for model_id, info in self.models_config[self.selected_provider].items():
            self.model_options.append(discord.SelectOption(
                label=info['name'][:100],
                value=model_id,
                description=f"{info['desc'][:50]} | {info['speed']}"[:100],
                default=(model_id == session.current_model and 
                        self.selected_provider == session.current_provider)
            ))
        
        await self._update_view(interaction)
    
    async def _update_view(self, interaction: discord.Interaction):
        """Refresh the view with model options"""
        # Clear non-provider selects
        self.clear_items()
        self._add_provider_select()
        
        # Pagination
        per_page = 24
        start = self.current_page * per_page
        end = start + per_page
        page_options = self.model_options[start:end]
        total_pages = (len(self.model_options) - 1) // per_page + 1
        
        # Model dropdown
        model_select = discord.ui.Select(
            placeholder=f"Select Model (Page {self.current_page + 1}/{total_pages})",
            options=page_options,
            row=1
        )
        model_select.callback = self._on_model_select
        self.add_item(model_select)
        
        # Pagination buttons
        if self.current_page > 0:
            prev_btn = discord.ui.Button(label="Previous", style=discord.ButtonStyle.secondary, row=2)
            prev_btn.callback = self._prev_page
            self.add_item(prev_btn)
        
        if end < len(self.model_options):
            next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, row=2)
            next_btn.callback = self._next_page
            self.add_item(next_btn)
        
        # Build embed
        provider_info = self.PROVIDERS[self.selected_provider]
        embed = discord.Embed(
            title="Model Selection",
            description=f"**{provider_info['name']}**\n{provider_info['desc']}",
            color=provider_info['color']
        )
        embed.set_footer(text=f"{len(self.model_options)} models available")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _prev_page(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self._update_view(interaction)
    
    async def _next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        await self._update_view(interaction)
    
    async def _on_model_select(self, interaction: discord.Interaction):
        """Handle model selection"""
        model_id = interaction.data['values'][0]
        
        try:
            session = await self.bot.get_user_session(self.user_id)
            session.switch_model(model_id, self.selected_provider)
            
            info = self.models_config[self.selected_provider][model_id]
            
            embed = discord.Embed(
                title="Model Changed",
                description=f"**{info['name']}**\n\n{info['desc']}",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Provider", value=self.selected_provider.title(), inline=True)
            embed.add_field(name="Speed", value=info['speed'], inline=True)
            embed.add_field(name="Rating", value=f"{'★' * info['stars']}{'☆' * (5 - info['stars'])}", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Model switch failed: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(str(e)),
                ephemeral=True
            )


class ResetView(discord.ui.View):
    """Reset options view"""
    
    def __init__(self, user_id: int, bot):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bot = bot

    @discord.ui.button(label="Keep Last 10", style=discord.ButtonStyle.primary)
    async def soft_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Soft reset - keep recent context"""
        session = await self.bot.get_user_session(self.user_id)
        session.reset_memory(keep_last=10)
        
        embed = create_success_embed(
            "Memory Reset",
            "Conversation cleared. Kept last 10 messages for context."
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Full Wipe", style=discord.ButtonStyle.danger)
    async def hard_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Hard reset - clear everything"""
        session = await self.bot.get_user_session(self.user_id)
        session.reset_memory(keep_last=0)
        
        embed = create_success_embed(
            "Memory Wiped",
            "All conversation history has been deleted."
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed("Cancelled", "No changes made.", Colors.SECONDARY)
        await interaction.response.edit_message(embed=embed, view=None)
