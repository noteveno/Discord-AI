"""Modern Discord UI Components with rich embeds and gradients"""
import discord
from discord.ext import commands
import json
import logging
from pathlib import Path

logger = logging.getLogger('UI')

# Modern Color Scheme
class Colors:
    """Rich color palette for modern Discord UI"""
    PRIMARY = 0x5865F2  # Discord Blurple
    PRIMARY_DARK = 0x4752C4  # Darker blurple
    SUCCESS = 0x00FF7F  # Spring green
    WARNING = 0xFFA500  # Orange
    ERROR = 0xFF4444  # Red
    INFO = 0x00BFFF  # Cyan
    PURPLE_GRADIENT = 0x7289DA  # Light purple
    GOLD = 0xFFD700  # Gold
    DARK = 0x2C2F33  # Dark gray
    
# Emoji sets for visual appeal
class Emojis:
    """Rich emoji collection"""
    ROCKET = "🚀"
    SPARKLES = "✨"
    GEAR = "⚙️"
    CHART = "📊"
    CHECK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    BRAIN = "🧠"
    LIGHTNING = "⚡"
    STAR = "⭐"
    FIRE = "🔥"
    ROBOT = "🤖"
    MAGIC = "🪄"
    SHIELD = "🛡️"
    CROWN = "👑"
    GEM = "💎"
    TRASH = "🗑️"
    LOCK = "🔒"
    HAMMER = "🔨"
    ARROW_RIGHT = "➡️"
    ARROW_LEFT = "⬅️"

def create_status_embed(title: str, description: str, color: int, emoji: str = None) -> discord.Embed:
    """Create a styled status embed with emoji"""
    if emoji:
        title = f"{emoji} {title}"
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Kamao AI • Next-Gen Discord Bot")
    return embed

def create_error_embed(error_msg: str) -> discord.Embed:
    """Create a styled error embed"""
    embed = discord.Embed(
        title=f"{Emojis.CROSS} Error Occurred",
        description=f"```\n{error_msg[:500]}\n```",
        color=Colors.ERROR
    )
    embed.add_field(
        name="💡 What to try:",
        value="• Check your command syntax\n• Try a different model with `/model`\n• Contact admin if issue persists",
        inline=False
    )
    embed.set_footer(text="Kamao AI • Error Handler")
    return embed

def create_loading_embed() -> discord.Embed:
    """Create a loading/processing embed"""
    embed = discord.Embed(
        title=f"{Emojis.GEAR} Processing...",
        description="*Your request is being processed*",
        color=Colors.INFO
    )
    return embed

class ConfirmView(discord.ui.View):
    """Confirmation dialog view"""
    def __init__(self, timeout=30):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji=Emojis.CHECK)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji=Emojis.CROSS)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()

class ModelSelectorView(discord.ui.View):
    """Modern model selection UI with pagination"""
    
    def __init__(self, user_id: int, bot, models_config: dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.bot = bot
        self.models_config = models_config
        self.current_page = 0
        self.selected_provider = None
        self.all_model_options = []
        
        # Provider selection dropdown
        self.provider_select = discord.ui.Select(
            placeholder=f"{Emojis.ROCKET} Step 1: Choose Your AI Provider",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Google Gemini",
                    value="gemini",
                    description="Multimodal powerhouse with vision",
                    emoji="♊"
                ),
                discord.SelectOption(
                    label="Groq",
                    value="groq",
                    description="Lightning-fast inference",
                    emoji="🚀"
                ),
                discord.SelectOption(
                    label="OpenRouter",
                    value="openrouter",
                    description="Massive free model selection",
                    emoji="🌟"
                )
            ],
            row=0
        )
        self.provider_select.callback = self.provider_selected
        self.add_item(self.provider_select)

    async def provider_selected(self, interaction: discord.Interaction):
        """Handle provider selection"""
        self.selected_provider = interaction.data['values'][0]
        self.current_page = 0
        
        # Get current user session
        session = await self.bot.get_user_session(self.user_id)
        
        # Build all model options
        self.all_model_options = []
        for model_id, info in self.models_config[self.selected_provider].items():
            # Create rich label with stats
            label = f"{info['name']}"
            desc = f"{info['desc'][:40]} • {info['speed']}"
            
            self.all_model_options.append(discord.SelectOption(
                label=label[:100],
                value=model_id,
                description=desc[:100],
                emoji=info.get('emoji', Emojis.ROBOT),
                default=model_id == session.current_model
            ))
        
        await self.update_model_view(interaction)
        
    async def update_model_view(self, interaction: discord.Interaction):
        """Update the view with paginated models"""
        # Clear previous model select and buttons
        items_to_remove = [item for item in self.children if isinstance(item, (discord.ui.Select, discord.ui.Button)) and item != self.provider_select]
        for item in items_to_remove:
            self.remove_item(item)
            
        # Pagination logic
        items_per_page = 23 # Leave room for Next/Prev
        start_idx = self.current_page * items_per_page
        end_idx = start_idx + items_per_page
        current_options = self.all_model_options[start_idx:end_idx]
        
        # Model selection dropdown
        model_select = discord.ui.Select(
            placeholder=f"{Emojis.BRAIN} Step 2: Select Model (Page {self.current_page + 1})",
            min_values=1,
            max_values=1,
            options=current_options,
            row=1
        )
        model_select.callback = self.model_selected
        self.add_item(model_select)
        
        # Add pagination buttons if needed
        if self.current_page > 0:
            prev_btn = discord.ui.Button(label="Previous", style=discord.ButtonStyle.secondary, emoji=Emojis.ARROW_LEFT, row=2)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
            
        if end_idx < len(self.all_model_options):
            next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, emoji=Emojis.ARROW_RIGHT, row=2)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
            
        # Create beautiful provider embed
        provider_info = {
            "gemini": ("Google Gemini", "Advanced multimodal AI with vision capabilities", Colors.PRIMARY),
            "groq": ("Groq", "Ultra-fast inference for instant responses", Colors.SUCCESS),
            "openrouter": ("OpenRouter", "Access to 30+ free AI models", Colors.INFO)
        }
        
        name, desc, color = provider_info.get(self.selected_provider, ("Provider", "Selected", Colors.PRIMARY))
        
        embed = discord.Embed(
            title=f"{Emojis.SPARKLES} Model Configuration",
            description=f"**Provider:** `{name}`\n{desc}\n\n**Page {self.current_page + 1}** of {(len(self.all_model_options) - 1) // items_per_page + 1}",
            color=color
        )
        embed.set_footer(text=f"Kamao AI • {len(self.all_model_options)} models available")
        
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        await self.update_model_view(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        await self.update_model_view(interaction)
    
    async def model_selected(self, interaction: discord.Interaction):
        """Handle model selection"""
        model_id = interaction.data['values'][0]
        
        try:
            session = await self.bot.get_user_session(self.user_id)
            session.switch_model(model_id, self.selected_provider)
            info = self.models_config[self.selected_provider][model_id]
            
            embed = create_status_embed(
                "Model Switched",
                f"**Active Model:** {info['emoji']} {info['name']}\n\n{info['desc']}",
                Colors.SUCCESS,
                Emojis.CHECK
            )
            embed.add_field(name="Stats", value=f"⭐ {info['stars']}/5 | ⚡ {info['speed']}", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Model switch error: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to switch model: {str(e)}"),
                ephemeral=True
            )
