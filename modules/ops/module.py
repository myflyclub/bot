"""
Ops module: administrative/diagnostic slash commands.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import discord
from discord import app_commands

from shared.module_contract import ModuleHealth, ModuleStats


@dataclass
class OpsModule:
    enabled: bool
    crash_handler: Any = None
    application: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    _commands_registered: bool = False

    @property
    def name(self) -> str:
        return "ops"

    async def register_commands(self, tree: Any) -> None:
        if self._commands_registered or not self.enabled:
            return

        @tree.command(name="crash_stats", description="Get crash handler statistics (admin)")
        @app_commands.default_permissions(administrator=True)
        async def crash_stats_command(interaction: discord.Interaction):
            try:
                stats = self.crash_handler.get_crash_stats() if self.crash_handler else {}
                embed = discord.Embed(
                    title="Crash Handler Statistics",
                    description="Bot stability and recovery information",
                    color=discord.Color.blue(),
                )
                if stats:
                    embed.add_field(
                        name="Restart Count",
                        value=f"{stats['restart_count']}/{stats['max_restart_attempts']}",
                        inline=True,
                    )
                    embed.add_field(name="Current Uptime", value=f"{stats['current_uptime']:.1f}s", inline=True)
                    embed.add_field(name="Total Crashes", value=str(stats["total_crashes"]), inline=True)
                    if stats.get("last_crash_time"):
                        embed.add_field(name="Last Crash", value=f"<t:{int(stats['last_crash_time'])}:R>", inline=True)
                    embed.add_field(name="Start Time", value=f"<t:{int(stats['start_time'])}:F>", inline=False)
                    if stats.get("crash_history"):
                        crash_list = []
                        for crash in stats["crash_history"][-5:]:
                            crash_list.append(f"`{crash['error_type']}` - <t:{int(crash['timestamp'])}:R>")
                        embed.add_field(name="Recent Crashes", value="\n".join(crash_list) or "None", inline=False)
                else:
                    embed.add_field(name="Status", value="Crash handler not available", inline=False)

                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.logger.info("Crash stats requested by %s", interaction.user)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to get crash stats: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to get crash stats: {e}", ephemeral=True)
                self.logger.error("Error getting crash stats: %s", e)

        @tree.command(name="system_health", description="Show aggregated module health")
        @app_commands.default_permissions(administrator=True)
        async def system_health_command(interaction: discord.Interaction):
            try:
                payload = self.application.module_health() if self.application else {}
                embed = discord.Embed(
                    title="System Health",
                    description="Aggregated module health snapshot",
                    color=discord.Color.green(),
                )
                if not payload:
                    embed.add_field(name="Status", value="No module health available", inline=False)
                else:
                    for module_name, module_data in payload.items():
                        status = module_data.get("status", "unknown")
                        details = module_data.get("details", {})
                        if details:
                            preview = ", ".join([f"{k}={v}" for k, v in list(details.items())[:3]])
                        else:
                            preview = "no details"
                        embed.add_field(name=module_name, value=f"status={status} | {preview}", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to get system health: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to get system health: {e}", ephemeral=True)
                self.logger.error("Error getting system health: %s", e)

        @tree.command(name="system_stats", description="Show aggregated module stats")
        @app_commands.default_permissions(administrator=True)
        async def system_stats_command(interaction: discord.Interaction):
            try:
                payload = self.application.module_stats() if self.application else {}
                embed = discord.Embed(
                    title="System Stats",
                    description="Aggregated module counters",
                    color=discord.Color.blurple(),
                )
                if not payload:
                    embed.add_field(name="Status", value="No module stats available", inline=False)
                else:
                    for module_name, module_data in payload.items():
                        counters = module_data.get("counters", {})
                        if counters:
                            preview = ", ".join([f"{k}={v}" for k, v in list(counters.items())[:4]])
                        else:
                            preview = "no counters"
                        embed.add_field(name=module_name, value=preview, inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to get system stats: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to get system stats: {e}", ephemeral=True)
                self.logger.error("Error getting system stats: %s", e)

        self._commands_registered = True

    def bind_application(self, application: Any) -> None:
        self.application = application

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def health_snapshot(self) -> ModuleHealth:
        return ModuleHealth(status="ok", details={"enabled": self.enabled})

    def stats_snapshot(self) -> ModuleStats:
        if not self.crash_handler:
            return ModuleStats(counters={})
        stats = self.crash_handler.get_crash_stats()
        return ModuleStats(
            counters={
                "restart_count": stats.get("restart_count"),
                "total_crashes": stats.get("total_crashes"),
                "current_uptime": stats.get("current_uptime"),
            }
        )
