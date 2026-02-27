"""
Runtime orchestration for Discord bot startup tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


@dataclass
class BotRuntime:
    bot: Any
    config: Any
    app_instance: Any
    logger: logging.Logger

    async def on_ready(self) -> None:
        self.logger.info("Bot connected successfully as %s#%s", self.bot.user.name, self.bot.user.discriminator)
        self.logger.info("Bot ID: %s", self.bot.user.id)
        self.logger.info("Connected to %s guild(s)", len(self.bot.guilds))

        if not getattr(self.bot, "_slash_synced", False):
            try:
                await self.app_instance.register_commands(self.bot.tree)
                synced = await self.bot.tree.sync()
                self.bot._slash_synced = True
                self.logger.info("Synced %s global slash command(s)", len(synced))
                # Also sync per-guild for faster command availability during development.
                for guild in self.bot.guilds:
                    try:
                        self.bot.tree.copy_global_to(guild=guild)
                        guild_synced = await self.bot.tree.sync(guild=guild)
                        self.logger.info(
                            "Synced %s guild slash command(s) for %s (%s)",
                            len(guild_synced),
                            guild.name,
                            guild.id,
                        )
                    except Exception as guild_error:
                        self.logger.warning(
                            "Guild command sync failed for %s (%s): %s",
                            guild.name,
                            guild.id,
                            guild_error,
                        )
            except Exception as e:
                self.logger.error("Failed to sync slash commands: %s", e)

        await self._apply_status()
        self._log_guild_context()
        await self.app_instance.start_modules()

    async def _apply_status(self) -> None:
        try:
            import discord

            await self.bot.change_presence(activity=discord.Game(name=self.config.BOT_STATUS))
        except Exception as e:
            self.logger.warning("Failed to set presence: %s", e)

    def _log_guild_context(self) -> None:
        for guild in self.bot.guilds:
            self.logger.info("Connected to guild: %s (ID: %s)", guild.name, guild.id)
            if self.config.DISCORD_OIL_CHANNEL:
                channel = guild.get_channel(self.config.get_oil_channel_id())
                if channel:
                    self.logger.info("Oil price channel found: %s (ID: %s)", channel.name, channel.id)
                    self.logger.info("Channel permissions: %s", channel.permissions_for(guild.me))
                else:
                    self.logger.warning(
                        "Oil price channel %s not found in guild %s",
                        self.config.DISCORD_OIL_CHANNEL,
                        guild.name,
                    )
