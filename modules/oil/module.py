"""
Oil feature module.

Contains oil lifecycle, background monitoring, and slash commands.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import discord

from shared.module_contract import ModuleHealth, ModuleStats
from utils.discord_client_wrapper import edit_channel_name_with_retry, send_message_with_retry
from utils.health_status import HealthStatusAggregator
from utils.price_monitor import OilPriceMonitor, create_monitor


class OilModule:
    def __init__(
        self,
        enabled: bool,
        bot: Optional[discord.Client] = None,
        config: Any = None,
        crash_handler: Any = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._enabled = bool(enabled)
        self.bot = bot
        self.config = config
        self.crash_handler = crash_handler
        self.logger = logger or logging.getLogger(__name__)
        self.health_aggregator = HealthStatusAggregator()
        self.price_monitor: Optional[OilPriceMonitor] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self._commands_registered = False

    @property
    def name(self) -> str:
        return "oil"

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def register_commands(self, tree: Any) -> None:
        if self._commands_registered or not self.enabled:
            return

        @tree.command(name="check", description="Manually check for oil price updates")
        async def check_price_updates(interaction: discord.Interaction):
            if not self.price_monitor:
                await interaction.response.send_message("Error: Price monitor not initialized.", ephemeral=True)
                return
            try:
                await interaction.response.defer(thinking=True, ephemeral=True)
                change_event = self.price_monitor.check_for_updates()
                if change_event:
                    await self._send_unified_oil_price_message(
                        self.price_monitor.get_current_price(),
                        change_event,
                        is_update=True,
                    )
                    if self.config and self.config.DISCORD_OIL_CHANNEL:
                        await self._auto_rename_channel(change_event)
                else:
                    current_price = self.price_monitor.get_current_price()
                    if current_price:
                        await self._send_unified_oil_price_message(current_price, is_update=False)
                await interaction.followup.send("Oil check completed.", ephemeral=True)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to check for updates: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to check for updates: {e}", ephemeral=True)
                self.logger.error("Error checking oil updates: %s", e)

        @tree.command(name="health", description="Show bot health and breaker status")
        async def health_command(interaction: discord.Interaction):
            try:
                snap = self.health_aggregator.snapshot(self.price_monitor, self.bot)
                embed = discord.Embed(
                    title="Bot Health",
                    description="Runtime and dependency health",
                    color=discord.Color.blue(),
                )
                embed.add_field(name="Uptime", value=f"{snap.uptime:.1f}s", inline=True)
                embed.add_field(name="Monitoring", value=str(snap.monitoring_active), inline=True)
                embed.add_field(name="Guilds", value=str(snap.guild_count), inline=True)
                if snap.websocket_latency is not None:
                    embed.add_field(name="WS Latency", value=f"{snap.websocket_latency * 1000:.0f} ms", inline=True)
                embed.add_field(name="Price", value=(f"${snap.current_price:.2f}" if snap.current_price is not None else "-"), inline=True)
                embed.add_field(name="Cycle", value=(str(snap.current_cycle) if snap.current_cycle is not None else "-"), inline=True)
                embed.add_field(
                    name="Last HTTP",
                    value=(f"<t:{int(snap.last_http_response_time)}:R>" if snap.last_http_response_time else "-"),
                    inline=True,
                )
                embed.add_field(
                    name="Next Poll",
                    value=(f"<t:{int(snap.next_poll_time)}:R>" if snap.next_poll_time else "-"),
                    inline=True,
                )
                embed.add_field(name="Updates", value=str(snap.total_updates_processed), inline=True)
                embed.add_field(name="Changes", value=str(snap.total_changes_detected), inline=True)
                cb = snap.circuit_breaker
                embed.add_field(name="Breaker", value=f"{cb.get('state')} (fail={cb.get('failures')})", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to get health: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to get health: {e}", ephemeral=True)
                self.logger.error("Error generating oil health: %s", e)

        @tree.command(name="stats", description="Show session statistics")
        async def stats_command(interaction: discord.Interaction):
            try:
                if not self.price_monitor:
                    await interaction.response.send_message("Error: Price monitor not initialized.", ephemeral=True)
                    return
                summary = self.price_monitor.get_price_change_summary()
                embed = discord.Embed(
                    title="Session Statistics",
                    description="Monitoring session metrics",
                    color=discord.Color.purple(),
                )
                sess = summary.get("session_stats", {})
                embed.add_field(name="Session Duration", value=f"{sess.get('session_duration', 0):.1f}s", inline=True)
                embed.add_field(name="Updates", value=str(sess.get("total_updates_processed", 0)), inline=True)
                embed.add_field(name="Changes", value=str(sess.get("total_changes_detected", 0)), inline=True)
                last = summary.get("last_change_event") or {}
                embed.add_field(name="Last Event", value=str(last.get("event_type")), inline=True)
                embed.add_field(
                    name="Last Delta",
                    value=(f"${last.get('price_change'):+.2f}" if last.get("price_change") is not None else "-"),
                    inline=True,
                )
                embed.add_field(
                    name="% Last Delta",
                    value=(f"{last.get('price_change_percent'):+.2f}%" if last.get("price_change_percent") is not None else "-"),
                    inline=True,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: Failed to get stats: {e}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: Failed to get stats: {e}", ephemeral=True)
                self.logger.error("Error generating oil stats: %s", e)

        self._commands_registered = True

    async def start(self) -> None:
        if not self.enabled:
            return
        if self.price_monitor is None:
            self.price_monitor = create_monitor(
                base_url=self.config.OIL_PRICE_URL,
                polling_interval=self.config.POLLING_INTERVAL,
            )
        self.price_monitor.start_monitoring()
        self._start_monitoring_task()
        await self._fetch_and_send_current_price()
        self.logger.info("Oil module started")

    async def stop(self) -> None:
        if self.price_monitor:
            self.price_monitor.stop_monitoring()
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except Exception:
                pass
        self.logger.info("Oil module stopped")

    def health_snapshot(self) -> ModuleHealth:
        if not self.price_monitor:
            return ModuleHealth(status="initializing", details={})
        status = self.price_monitor.get_monitoring_status()
        return ModuleHealth(status="ok" if status.get("monitoring_active") else "stopped", details=status)

    def stats_snapshot(self) -> ModuleStats:
        if not self.price_monitor:
            return ModuleStats(counters={})
        summary = self.price_monitor.get_price_change_summary()
        return ModuleStats(counters=summary.get("session_stats", {}))

    def _start_monitoring_task(self) -> None:
        if self.monitoring_task and not self.monitoring_task.done():
            return
        self.monitoring_task = asyncio.create_task(self._background_monitoring())

    async def _fetch_and_send_current_price(self) -> None:
        if not self.config.DISCORD_OIL_CHANNEL or not self.price_monitor:
            return
        try:
            change_event = self.price_monitor.check_for_updates()
            if change_event:
                await self._send_unified_oil_price_message(self.price_monitor.get_current_price(), change_event, is_update=True)
                await self._auto_rename_channel(change_event)
                self.logger.info("Initial oil update sent: $%.2f", change_event.new_price)
            else:
                current_price = self.price_monitor.get_current_price()
                if current_price:
                    await self._send_unified_oil_price_message(current_price, is_update=False)
                    self.logger.info("Current oil info sent: $%.2f", current_price.price)
        except Exception as e:
            self.logger.error("Error fetching initial oil update: %s", e)

    async def _background_monitoring(self) -> None:
        if not self.price_monitor:
            return
        self.logger.info("Oil background monitoring started")
        try:
            while self.price_monitor.monitoring_active:
                try:
                    change_event = self.price_monitor.check_for_updates()
                    if change_event:
                        self.logger.info("Oil change detected in background: $%.2f", change_event.new_price)
                        await self._auto_rename_channel(change_event)
                        if self.config.DISCORD_OIL_CHANNEL:
                            await self._send_unified_oil_price_message(self.price_monitor.get_current_price(), change_event, is_update=True)
                    next_poll = self.price_monitor.http_client.get_next_poll_time()
                    wait_time = max(0, next_poll - time.time())
                    await asyncio.sleep(wait_time if wait_time > 0 else self.config.POLLING_INTERVAL)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error("Oil background monitoring error: %s", e)
                    if self.crash_handler:
                        await self.crash_handler.handle_crash(
                            e,
                            {
                                "function": "oil_background_monitoring",
                                "monitoring_active": self.price_monitor.monitoring_active if self.price_monitor else False,
                            },
                        )
                    await asyncio.sleep(60)
        finally:
            self.logger.info("Oil background monitoring stopped")

    async def _auto_rename_channel(self, change_event: Any) -> None:
        if not self.config.DISCORD_OIL_CHANNEL:
            return
        try:
            channel_id = self.config.get_oil_channel_id()
            trend_emoji = "\U0001F4CA"  # 📊
            if change_event.event_type != "initial":
                if change_event.price_change > 0:
                    trend_emoji = "\U0001F4C8"  # 📈
                elif change_event.price_change < 0:
                    trend_emoji = "\U0001F4C9"  # 📉

            price_str = f"{change_event.new_price:.2f}"
            dollars, cents = price_str.split(".")
            money_emoji = "\U0001F4B2"  # 💲
            new_channel_name = f"oil-price-{trend_emoji}{money_emoji}{dollars}-{cents}"

            if len(new_channel_name) > 100:
                new_channel_name = f"oil-{trend_emoji}{money_emoji}{dollars}-{cents}"

            success = await edit_channel_name_with_retry(self.bot, channel_id, new_channel_name)
            if not success:
                self.logger.error("Failed to rename oil channel %s", channel_id)
        except Exception as e:
            self.logger.error("Oil channel rename error: %s", e)

    async def _send_unified_oil_price_message(self, price_data: Any, change_event: Any = None, is_update: bool = False) -> None:
        if not self.config.DISCORD_OIL_CHANNEL:
            return
        channel_id = self.config.get_oil_channel_id()

        embed = discord.Embed(
            title="\U0001F504 Oil Price Updated!",  # 🔄
            description=("Automatic price update detected" if is_update else "Current price information"),
            color=discord.Color.green(),
        )

        if change_event and change_event.event_type != "initial":
            embed.add_field(name="\U0001F4B0 Old Price", value=f"${change_event.old_price:.2f}", inline=True)  # 💰
            embed.add_field(name="\U0001F4B0 New Price", value=f"${change_event.new_price:.2f}", inline=True)  # 💰
            embed.add_field(name="\U0001F504 Cycle", value=f"{change_event.new_cycle}", inline=True)  # 🔄
            embed.add_field(
                name="\U0001F4CA Change",  # 📊
                value=f"${change_event.price_change:+.2f} ({change_event.price_change_percent:+.2f}%)",
                inline=True,
            )
        elif change_event and change_event.event_type == "initial":
            embed.add_field(name="\U0001F4B0 New Price", value=f"${change_event.new_price:.2f}", inline=True)  # 💰
            embed.add_field(name="\U0001F504 Cycle", value=f"{change_event.new_cycle}", inline=True)  # 🔄
            embed.add_field(name="\U0001F4DD Type", value="Initial Price", inline=True)  # 📝
        else:
            embed.add_field(name="\U0001F4B0 Current Price", value=f"${price_data.price:.2f}", inline=True)  # 💰
            embed.add_field(name="\U0001F504 Cycle", value=f"{price_data.cycle}", inline=True)  # 🔄
            embed.add_field(name="\U0001F4CA Status", value="No price change detected", inline=True)  # 📊

        current_time = datetime.now(timezone.utc)
        embed.add_field(name="\u23F0 Time", value=f"{current_time.strftime('%H:%M')} UTC", inline=True)  # ⏰
        success = await send_message_with_retry(self.bot, channel_id, embed=embed)
        if not success:
            self.logger.error("Failed to send oil message to channel %s", channel_id)

