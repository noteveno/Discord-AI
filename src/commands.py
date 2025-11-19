"""Discord Slash Commands including moderation"""
import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

from .ui_components import (
    ModelSelectorView, ConfirmView,
    create_status_embed, create_error_embed,
    Colors, Emojis
)

logger = logging.getLogger('Commands')

def setup_commands(bot):
    """Setup all slash commands for the bot"""
    
    @bot.tree.command(name="model", description="🤖 Change your AI model and provider")
    async def model_cmd(interaction: discord.Interaction):
        """Launch model selector"""
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(interaction.channel_id) != channel_id:
            await interaction.response.send_message(
                embed=create_error_embed("This command only works in the AI channel"),
                ephemeral=True
            )
            return
        
        session = await bot.get_user_session(interaction.user.id)
        current_info = bot.models_config[session.current_provider][session.current_model]
        
        embed = discord.Embed(
            title=f"{Emojis.ROBOT} AI Model Configuration",
            description=f"**Current Model:** {current_info['emoji']} {current_info['name']}\n*{current_info['desc']}*\n\n{Emojis.SPARKLES} Select a provider below to see available models",
            color=Colors.PRIMARY
        )
        embed.add_field(
            name="📊 Current Stats",
            value=f"⭐ {current_info['stars']}/5 | ⚡ {current_info['speed']} | 💻 {current_info['coding']}",
            inline=False
        )
        embed.set_footer(text="Kamao AI • Model Selector")
        
        view = ModelSelectorView(interaction.user.id, bot, bot.models_config)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @bot.tree.command(name="stats", description="📊 View your AI usage statistics")
    async def stats_cmd(interaction: discord.Interaction):
        """Show user stats with modern embed"""
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(interaction.channel_id) != channel_id:
            await interaction.response.send_message(
                embed=create_error_embed("This command only works in the AI channel"),
                ephemeral=True
            )
            return
        
        session = await bot.get_user_session(interaction.user.id)
        current_info = bot.models_config[session.current_provider][session.current_model]
        
        embed = discord.Embed(
            title=f"{Emojis.CHART} {interaction.user.name}'s AI Statistics",
            color=Colors.INFO,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=f"{Emojis.BRAIN} Current Model",
            value=f"{current_info['emoji']} **{current_info['name']}**",
            inline=False
        )
        embed.add_field(
            name="🌐 Provider",
            value=f"`{session.current_provider.upper()}`",
            inline=True
        )
        embed.add_field(
            name="💬 Messages",
            value=f"**{len(session.chat_db.get_messages(1000))}**",
            inline=True
        )
        embed.add_field(
            name="🎯 Token Usage",
            value=f"**{session.chat_db.get_token_count():,}**",
            inline=True
        )
        embed.add_field(
            name=f"{Emojis.STAR} Model Rating",
            value=f"{'⭐' * current_info['stars']}",
            inline=True
        )
        embed.add_field(
            name="⚡ Speed",
            value=f"`{current_info['speed']}`",
            inline=True
        )
        embed.add_field(
            name="💻 Coding",
            value=f"`{current_info['coding']}`",
            inline=True
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Kamao AI • Per-user isolated memory")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="reset", description="🗑️ Reset your conversation history (Admin only)")
    @app_commands.describe(full_wipe="Completely wipe ALL memory (True) or keep last 10 messages (False)")
    async def reset_cmd(interaction: discord.Interaction, full_wipe: bool = False):
        """Reset conversation with confirmation"""
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(interaction.channel_id) != channel_id:
            await interaction.response.send_message(
                embed=create_error_embed("This command only works in the AI channel"),
                ephemeral=True
            )
            return
        
        if interaction.guild and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed("This command requires Administrator permission"),
                ephemeral=True
            )
            return
        
        wipe_text = "**COMPLETE WIPE** - All messages will be deleted!" if full_wipe else "Keep last 10 messages for context"
        
        embed = discord.Embed(
            title=f"{Emojis.TRASH} Reset Conversation",
            description=f"This will clear your history.\n\n{wipe_text}\n\n**⚠️ This action cannot be undone!**",
            color=Colors.ERROR if full_wipe else Colors.WARNING
        )
        embed.set_footer(text="Click 'Confirm' to proceed or 'Cancel' to abort")
        
        view = ConfirmView(timeout=30)
        
        async def confirm_callback(interaction_inner: discord.Interaction):
            session = await bot.get_user_session(interaction_inner.user.id)
            
            if full_wipe:
                session.chat_db.clear_all()
                kept = 0
            else:
                session.chat_db.reset_context(10)
                kept = 10
            
            session.ai_provider = None
            
            success_embed = create_status_embed(
                "Reset Complete",
                f"✅ {'All messages cleared!' if full_wipe else f'Kept last {kept} messages for context.'}",
                Colors.SUCCESS,
                Emojis.CHECK
            )
            await interaction_inner.response.edit_message(embed=success_embed, view=None)
        
        view.confirm.callback = confirm_callback
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @bot.tree.command(name="user_reset", description="🔨 Reset a specific user's memory (Admin only)")
    @app_commands.describe(user="The user whose memory to reset")
    async def user_reset_cmd(interaction: discord.Interaction, user: discord.User):
        """Reset specific user's conversation"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed("This command requires Administrator permission"),
                ephemeral=True
            )
            return
        
        try:
            session = await bot.get_user_session(user.id)
            session.chat_db.reset_context(5)
            session.ai_provider = None
            
            embed = create_status_embed(
                "User Memory Reset",
                f"✅ Successfully reset conversation history for {user.mention}\nKept last 5 messages.",
                Colors.SUCCESS,
                Emojis.HAMMER
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"{interaction.user.name} reset memory for {user.name}")
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to reset: {str(e)}"),
                ephemeral=True
            )

    @bot.tree.command(name="kick", description="👢 Kick a member from the server (Admin only)")
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for kicking"
    )
    async def kick_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Kick a member"""
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to kick members"),
                ephemeral=True
            )
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot kick this user (role hierarchy)"),
                ephemeral=True
            )
            return
        
        try:
            await member.kick(reason=f"{reason} | By: {interaction.user.name}")
            
            embed = discord.Embed(
                title=f"{Emojis.CHECK} Member Kicked",
                description=f"**User:** {member.mention} ({member.name})\n**Reason:** {reason}",
                color=Colors.WARNING
            )
            embed.set_footer(text=f"Kicked by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} kicked {member.name}: {reason}")
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to kick: {str(e)}"),
                ephemeral=True
            )

    @bot.tree.command(name="ban", description="🔨 Ban a member from the server (Admin only)")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for banning",
        delete_days="Days of messages to delete (0-7)"
    )
    async def ban_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 0):
        """Ban a member"""
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to ban members"),
                ephemeral=True
            )
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot ban this user (role hierarchy)"),
                ephemeral=True
            )
            return
        
        delete_days = max(0, min(7, delete_days))
        
        try:
            await member.ban(reason=f"{reason} | By: {interaction.user.name}", delete_message_days=delete_days)
            
            embed = discord.Embed(
                title=f"{Emojis.HAMMER} Member Banned",
                description=f"**User:** {member.mention} ({member.name})\n**Reason:** {reason}\n**Messages Deleted:** {delete_days} days",
                color=Colors.ERROR
            )
            embed.set_footer(text=f"Banned by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} banned {member.name}: {reason}")
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to ban: {str(e)}"),
                ephemeral=True
            )

    @bot.tree.command(name="unban", description="🔓 Unban a user from the server (Admin only)")
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban_cmd(interaction: discord.Interaction, user_id: str):
        """Unban a user"""
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to unban members"),
                ephemeral=True
            )
            return
        
        try:
            user_id_int = int(user_id)
            user = await bot.fetch_user(user_id_int)
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user.name}")
            
            embed = discord.Embed(
                title=f"{Emojis.CHECK} User Unbanned",
                description=f"**User:** {user.mention} ({user.name})\n**ID:** {user_id}",
                color=Colors.SUCCESS
            )
            embed.set_footer(text=f"Unbanned by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} unbanned {user.name}")
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid user ID"),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to unban: {str(e)}"),
                ephemeral=True
            )

    @bot.tree.command(name="timeout", description="⏰ Timeout a member (Admin only)")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes",
        reason="Reason for timeout"
    )
    async def timeout_cmd(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
        """Timeout a member"""
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to timeout members"),
                ephemeral=True
            )
            return
        
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot timeout this user (role hierarchy)"),
                ephemeral=True
            )
            return
        
        try:
            until = datetime.utcnow() + timedelta(minutes=duration)
            await member.timeout(until, reason=f"{reason} | By: {interaction.user.name}")
            
            embed = discord.Embed(
                title=f"{Emojis.WARNING} Member Timed Out",
                description=f"**User:** {member.mention}\n**Duration:** {duration} minutes\n**Reason:** {reason}",
                color=Colors.WARNING
            )
            embed.set_footer(text=f"Timed out by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user.name} timed out {member.name} for {duration}m: {reason}")
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to timeout: {str(e)}"),
                ephemeral=True
            )

    @bot.tree.command(name="help", description="ℹ️ Show help and available commands")
    async def help_cmd(interaction: discord.Interaction):
        """Show help with modern embed"""
        channel_id = os.getenv('CHANNEL_ID')
        if not channel_id or str(interaction.channel_id) != channel_id:
            await interaction.response.send_message(
                embed=create_error_embed("This command only works in the AI channel"),
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"{Emojis.ROBOT} Kamao AI - Help",
            description="**🎯 Private per-user memory** - Each user has isolated conversations\n\nJust send a message to chat with the AI!",
            color=Colors.PRIMARY
        )
        
        # AI Commands
        embed.add_field(
            name=f"{Emojis.BRAIN} AI Commands",
            value=(
                "• `/model` - Change AI model & provider\n"
                "• `/stats` - View your usage statistics\n"
                "• `/help` - Show this help message"
            ),
            inline=False
        )
        
        # Admin Commands
        embed.add_field(
            name=f"{Emojis.SHIELD} Admin Commands",
            value=(
                "• `/reset` - Clear your history (Admin)\n"
                "• `/user_reset` - Reset specific user's memory\n"
                "• `/kick` - Kick a member\n"
                "• `/ban` - Ban a member\n"
                "• `/unban` - Unban a user\n"
                "• `/timeout` - Timeout a member"
            ),
            inline=False
        )
        
        # Features
        embed.add_field(
            name=f"{Emojis.SPARKLES} Features",
            value=(
                "• 🖼️ Image understanding (Gemini)\n"
                "• 📺 YouTube transcript extraction\n"
                "• 💾 Persistent memory per user\n"
                "• 🔄 Auto-provider fallback"
            ),
            inline=False
        )
        
        embed.set_footer(text="Kamao AI • All commands work only in the AI channel")
        embed.set_thumbnail(url=bot.user.display_avatar.url if bot.user else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    logger.info("All commands registered")
