from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from config import settings
from bot.discord_api import set_voice_status, DiscordAPIError

class VoiceStatusCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _status(self, interaction: discord.Interaction, status: str | None):
        channel = interaction.guild.get_channel(interaction.channel_id) if interaction.guild else None
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            await interaction.response.send_message("Run this command inside a voice or stage channel.", ephemeral=True)
            return
        try:
            await set_voice_status(settings.discord_bot_token, channel.id, status)
            msg = "Voice channel status cleared." if status is None else "Voice channel status updated."
            await interaction.response.send_message(msg, ephemeral=True)
        except DiscordAPIError as exc:
            await interaction.response.send_message(f"Could not update status: {exc}", ephemeral=True)

    @app_commands.command(name="vcstatus", description="Set this voice channel's status")
    @app_commands.describe(text="Status text (up to 500 characters)")
    async def vcstatus(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 500]):
        await self._status(interaction, text)

    @app_commands.command(name="vcreset", description="Clear this voice channel's status")
    async def vcreset(self, interaction: discord.Interaction):
        await self._status(interaction, None)

    @app_commands.command(name="vchelp", description="Show VK VC Status Bot help")
    async def vchelp(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**VK VC STATUS BOT**\n`/vcstatus text:<message>` — set status\n`/vcreset` — clear status\nUse the web dashboard for server and channel selection.",
            ephemeral=True,
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceStatusCommands(bot))
