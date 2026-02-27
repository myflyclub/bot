"""
Route of the Day (ROTD) feature module.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

import discord
from discord import app_commands

from shared.module_contract import ModuleHealth, ModuleStats
from utils.discord_client_wrapper import send_message_with_retry
from utils.rotd_formatter import format_rotd_text
from utils.rotd_service import ROTDService


@dataclass
class RotdModule:
    enabled: bool
    bot: Optional[discord.Client] = None
    config: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    service: ROTDService = field(default_factory=ROTDService)
    _commands_registered: bool = False
    _daily_task: Optional[asyncio.Task] = None
    _posts_attempted: int = 0
    _posts_succeeded: int = 0
    _last_post_ts: Optional[float] = None

    @property
    def name(self) -> str:
        return "rotd"

    async def register_commands(self, tree: Any) -> None:
        if self._commands_registered or not self.enabled:
            return

        @tree.command(name="randomroute", description="Generate and post a Route of the Day once")
        @app_commands.describe(origin_id="Optional origin airport ID", dest_id="Optional destination airport ID")
        async def randomroute_command(
            interaction: discord.Interaction,
            origin_id: Optional[int] = None,
            dest_id: Optional[int] = None,
        ):
            await self._handle_randomroute_command(interaction, origin_id, dest_id)

        self._commands_registered = True

    async def start(self) -> None:
        if not self.enabled:
            return
        channel_id = self.config.get_rrotd_channel_id() if self.config else None
        if not channel_id:
            self.logger.info("ROTD disabled at runtime: channel not configured")
            return
        schedule_enabled = bool(getattr(self.config, "ROTD_SCHEDULE_ENABLED", False)) if self.config else False
        if not schedule_enabled:
            self.logger.info("ROTD scheduler disabled (ROTD_SCHEDULE_ENABLED=false); use /randomroute for manual runs")
            return
        if self._daily_task and not self._daily_task.done():
            return
        self._daily_task = asyncio.create_task(self._daily_loop())
        self.logger.info("ROTD module started")

    async def stop(self) -> None:
        if self._daily_task and not self._daily_task.done():
            self._daily_task.cancel()
            try:
                await self._daily_task
            except Exception:
                pass
        self.logger.info("ROTD module stopped")

    def health_snapshot(self) -> ModuleHealth:
        running = bool(self._daily_task and not self._daily_task.done())
        return ModuleHealth(
            status="ok" if (not self.enabled or running) else "stopped",
            details={
                "enabled": self.enabled,
                "daily_task_running": running,
                "last_post_ts": self._last_post_ts,
            },
        )

    def stats_snapshot(self) -> ModuleStats:
        return ModuleStats(
            counters={
                "posts_attempted": self._posts_attempted,
                "posts_succeeded": self._posts_succeeded,
                "last_post_ts": self._last_post_ts,
            }
        )

    async def _daily_loop(self) -> None:
        while True:
            try:
                next_run_utc = self._next_scheduled_run_utc()
                now_utc = datetime.now(timezone.utc)
                sleep_seconds = max(1, int((next_run_utc - now_utc).total_seconds()))
                self.logger.info(
                    "ROTD next scheduled run at %s UTC (in %ss)",
                    next_run_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)
                await self.post_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error("ROTD daily task error: %s", e)

    def _next_scheduled_run_utc(self) -> datetime:
        """Return next schedule execution as UTC datetime."""
        tz_raw = getattr(self.config, "ROTD_SCHEDULE_TZ", "UTC") if self.config else "UTC"
        tz_name = str(tz_raw or "UTC").split("#")[0].strip()
        hour = int(getattr(self.config, "ROTD_SCHEDULE_HOUR", 15)) if self.config else 15
        minute = int(getattr(self.config, "ROTD_SCHEDULE_MINUTE", 0)) if self.config else 0

        if tz_name.upper() in {"UTC", "ETC/UTC", "Z"}:
            local_tz = timezone.utc
        else:
            try:
                local_tz = ZoneInfo(tz_name)
            except Exception as e:
                self.logger.warning(
                    "Could not load ROTD_SCHEDULE_TZ=%s (%s), falling back to UTC",
                    tz_name,
                    e.__class__.__name__,
                )
                local_tz = timezone.utc

        now_local = datetime.now(local_tz)
        target_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now_local >= target_local:
            target_local = target_local + timedelta(days=1)
        return target_local.astimezone(timezone.utc)

    async def post_once(self) -> bool:
        channel_id = self.config.get_rrotd_channel_id() if self.config else None
        if not channel_id:
            self.logger.warning("ROTD channel not configured")
            return False

        self._posts_attempted += 1
        payload = await self._generate_payload_for_post()
        if not payload:
            return False

        text = format_rotd_text(payload)
        await self._send_chunked(channel_id, text)

        self._posts_succeeded += 1
        self._last_post_ts = datetime.now(timezone.utc).timestamp()
        return True

    async def _handle_randomroute_command(
        self,
        interaction: discord.Interaction,
        origin_id: Optional[int],
        dest_id: Optional[int],
    ) -> None:
        try:
            channel_id = self.config.get_rrotd_channel_id() if self.config else None
            if not channel_id:
                await interaction.response.send_message(
                    "Error: ROTD channel not configured. Set DISCORD_RROTD_CHANNEL in .env.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(thinking=True, ephemeral=True)
            pair = await self._resolve_pair_for_command(interaction, origin_id, dest_id)
            if not pair:
                return
            origin_id, dest_id = pair

            payload = await self._generate_payload(origin_id, dest_id, timeout=25)
            if not payload:
                await interaction.followup.send("Could not generate route at this time.", ephemeral=True)
                return

            text = format_rotd_text(payload)
            origin_name = f"{payload.get('a_name', 'Airport')} ({payload.get('a_code', '?')})"
            dest_name = f"{payload.get('b_name', 'Airport')} ({payload.get('b_code', '?')})"
            await interaction.followup.send(
                f"Posting route {origin_name} -> {dest_name} to <#{channel_id}> ...",
                ephemeral=True,
            )
            await self._send_chunked(channel_id, text)
        except Exception as e:
            self.logger.error("randomroute command failed: %s", e, exc_info=True)
            if interaction.response.is_done():
                await interaction.followup.send(f"Error: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    async def _resolve_pair_for_command(
        self,
        interaction: discord.Interaction,
        origin_id: Optional[int],
        dest_id: Optional[int],
    ) -> Optional[Tuple[int, int]]:
        if origin_id is not None and dest_id is not None:
            return origin_id, dest_id
        if origin_id is None and dest_id is None:
            await interaction.followup.send("Selecting random airport pair...", ephemeral=True)
            try:
                pair = await asyncio.wait_for(
                    asyncio.to_thread(self.service._select_candidate_pair),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                await interaction.followup.send("Random selection timed out. Please try again.", ephemeral=True)
                return None
            if not pair:
                await interaction.followup.send(
                    "Could not find a valid random airport pair. Try providing specific IDs.",
                    ephemeral=True,
                )
                return None
            return pair
        pair = self.config.get_rotd_pair() if self.config else None
        if not pair:
            await interaction.followup.send(
                "Provide both origin and destination IDs, or neither for random selection.\n"
                "Usage: `/randomroute origin_id:3803 dest_id:3358` or `/randomroute`",
                ephemeral=True,
            )
            return None
        return pair

    async def _generate_payload_for_post(self) -> Optional[Dict[str, Any]]:
        pair = self.config.get_rotd_pair() if self.config else None
        if pair:
            origin_id, dest_id = pair
            self.logger.info("ROTD: Using configured pair %s -> %s", origin_id, dest_id)
        else:
            self.logger.info("ROTD: No configured pair, selecting random airports")
            try:
                pair = await asyncio.wait_for(
                    asyncio.to_thread(self.service._select_candidate_pair),
                    timeout=45,
                )
            except asyncio.TimeoutError:
                self.logger.error("ROTD: Random selection timed out")
                return None
            if not pair:
                self.logger.warning("ROTD: Could not find valid random pair; skipping")
                return None
            origin_id, dest_id = pair
        return await self._generate_payload(origin_id, dest_id, timeout=25)

    async def _generate_payload(self, origin_id: int, dest_id: int, timeout: int) -> Optional[Dict[str, Any]]:
        try:
            payload = await asyncio.wait_for(
                asyncio.to_thread(self.service.generate_payload, origin_id, dest_id),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self.logger.error("ROTD: generate_payload timed out")
            return None
        if not payload:
            self.logger.info("ROTD: No payload generated; skipping")
            return None
        return payload

    async def _send_chunked(self, channel_id: int, content: str, limit: int = 1900) -> None:
        lines = content.split("\n")
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > limit:
                await send_message_with_retry(self.bot, channel_id, content=chunk)
                chunk = ""
            chunk += (("\n" if chunk else "") + line)
        if chunk:
            await send_message_with_retry(self.bot, channel_id, content=chunk)

