"""
Aviation Info module: slash commands for live plane/airport lookup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import discord
from discord import app_commands

from shared.formatting import country_flag, format_int, relationship_text
from shared.module_contract import ModuleHealth, ModuleStats
from utils.aviation_info_service import AviationInfoService


@dataclass
class AviationInfoModule:
    enabled: bool
    config: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    _commands_registered: bool = False
    _queries_total: int = 0
    _queries_plane: int = 0
    _queries_airport: int = 0
    _queries_research: int = 0
    _queries_success: int = 0
    _queries_not_found: int = 0
    _queries_failed: int = 0

    def __post_init__(self) -> None:
        self.service = AviationInfoService()
        self._airport_id_lookup_enabled = (
            bool(getattr(self.config, "AVIATION_AIRPORT_ID_LOOKUP_ENABLED", False)) if self.config else False
        )

    @property
    def name(self) -> str:
        return "aviation_info"

    async def register_commands(self, tree: Any) -> None:
        if self._commands_registered or not self.enabled:
            return

        @tree.command(name="plane", description="Search airplane models by name")
        @app_commands.describe(model="Full or partial airplane model (ex: A320, 737, 787)")
        async def plane_command(interaction: discord.Interaction, model: str):
            await self._handle_plane_command(interaction, model)

        if self._airport_id_lookup_enabled:
            @tree.command(name="airport", description="Get airport information by ID or IATA/ICAO code")
            @app_commands.describe(
                airport_id="Airport ID from MyFly",
                code="IATA/ICAO code (ex: EZE, KJFK)",
            )
            async def airport_command(
                interaction: discord.Interaction,
                airport_id: Optional[int] = None,
                code: Optional[str] = None,
            ):
                await self._handle_airport_command(interaction, airport_id=airport_id, code=code)
        else:
            @tree.command(name="airport", description="Get airport information by IATA/ICAO code")
            @app_commands.describe(code="IATA/ICAO code (ex: EZE, KJFK)")
            async def airport_command(interaction: discord.Interaction, code: str):
                await self._handle_airport_command(interaction, airport_id=None, code=code)

        @tree.command(name="research", description="Research demand and relationship between two airport codes")
        @app_commands.describe(
            origin_code="Origin IATA/ICAO code (ex: EZE, SAEZ)",
            dest_code="Destination IATA/ICAO code (ex: JFK, KJFK)",
        )
        async def research_command(interaction: discord.Interaction, origin_code: str, dest_code: str):
            await self._handle_research_command(interaction, origin_code, dest_code)

        self._commands_registered = True

    @staticmethod
    def _quality_to_stars(quality: Any) -> str:
        try:
            score = float(quality) / 2.0
        except (TypeError, ValueError):
            return "-"
        return f"{score:g} stars"

    async def _handle_plane_command(self, interaction: discord.Interaction, model: str) -> None:
        self._queries_total += 1
        self._queries_plane += 1
        try:
            query = (model or "").strip()
            if len(query) < 2:
                self._queries_not_found += 1
                await interaction.response.send_message(
                    "Please provide at least 2 characters for `model`.",
                )
                return

            await interaction.response.defer(thinking=True)
            matches = self.service.search_models(query=query, limit=5)
            if not matches:
                self._queries_not_found += 1
                await interaction.followup.send(
                    f"No airplane model matches found for `{query}`.",
                )
                return

            top = self.service.normalize_model(matches[0])
            embed = discord.Embed(
                title=f"Aircraft: {top['name']}",
                description=f"Best match for `{query}`",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="🏭 Manufacturer", value=str(top["manufacturer"]), inline=True)
            embed.add_field(name="🧬 Family", value=str(top["family"]), inline=True)
            embed.add_field(name="⭐ Quality", value=f"{self._quality_to_stars(top['quality'])} ({top['quality']}/10)", inline=True)

            capacity_value = top["capacity"]
            capacity_text = f"{capacity_value} pax" if isinstance(capacity_value, (int, float)) else str(capacity_value)
            embed.add_field(name="👥 Capacity", value=capacity_text, inline=True)

            range_value = top["range"]
            range_text = f"{range_value} km" if isinstance(range_value, (int, float)) else str(range_value)
            embed.add_field(name="🛫 Range", value=range_text, inline=True)

            speed_value = top["speed"]
            speed_text = f"{speed_value} km/h" if isinstance(speed_value, (int, float)) else str(speed_value)
            embed.add_field(name="⚡ Speed", value=speed_text, inline=True)

            runway_value = top["runway_requirement"]
            runway_text = f"{runway_value} m" if isinstance(runway_value, (int, float)) else str(runway_value)
            embed.add_field(name="🛬 Runway Req.", value=runway_text, inline=True)

            if len(matches) > 1:
                alternatives = []
                for item in matches[1:]:
                    m = self.service.normalize_model(item)
                    alternatives.append(f"- `{m['name']}`")
                embed.add_field(name="🧩 Other Matches", value="\n".join(alternatives), inline=False)

            self._queries_success += 1
            await interaction.followup.send(embed=embed)
        except Exception as e:
            self._queries_failed += 1
            self.logger.error("plane command failed: %s", e, exc_info=True)
            user_msg = "An error occurred while retrieving plane data. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(user_msg)
            else:
                await interaction.response.send_message(user_msg)

    async def _handle_airport_command(
        self,
        interaction: discord.Interaction,
        airport_id: Optional[int],
        code: Optional[str],
    ) -> None:
        self._queries_total += 1
        self._queries_airport += 1
        try:
            if airport_id is None and not code:
                self._queries_not_found += 1
                await interaction.response.send_message(
                    "Provide `airport_id` or `code`.",
                )
                return
            if airport_id is not None and airport_id <= 0:
                self._queries_not_found += 1
                await interaction.response.send_message(
                    "Airport ID must be a positive integer.",
                )
                return

            await interaction.response.defer(thinking=True)
            airport = None
            if airport_id is not None:
                airport = self.service.get_airport_by_id(airport_id)
            elif code:
                airport = self.service.find_airport_by_code(code)

            if not airport:
                self._queries_not_found += 1
                lookup_ref = f"id `{airport_id}`" if airport_id is not None else f"code `{code}`"
                await interaction.followup.send(
                    f"Airport with {lookup_ref} was not found.",
                )
                return

            normalized = self.service.normalize_airport(airport)
            country_flag_value = country_flag(normalized.get("country_code"))
            country_text = str(normalized["country"])
            if country_flag_value:
                country_text = f"{country_text} {country_flag_value}"
            embed = discord.Embed(
                title=f"Airport: {normalized['name']}",
                color=discord.Color.green(),
            )
            embed.add_field(name="🧭 IATA", value=str(normalized["iata"]), inline=True)
            embed.add_field(name="🗺️ ICAO", value=str(normalized["icao"]), inline=True)
            embed.add_field(name="🏙️ City", value=str(normalized["city"]), inline=True)
            embed.add_field(name="🌍 Country", value=country_text, inline=True)
            embed.add_field(name="📏 Size", value=str(normalized["size"]), inline=True)
            runway_value = normalized["runway"]
            runway_text = f"{runway_value} m" if isinstance(runway_value, (int, float)) else str(runway_value)
            embed.add_field(name="🛬 Runway", value=runway_text, inline=True)

            self._queries_success += 1
            await interaction.followup.send(embed=embed)
        except Exception as e:
            self._queries_failed += 1
            self.logger.error("airport command failed: %s", e, exc_info=True)
            user_msg = "An error occurred while retrieving airport data. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(user_msg)
            else:
                await interaction.response.send_message(user_msg)

    async def _handle_research_command(
        self,
        interaction: discord.Interaction,
        origin_code: str,
        dest_code: str,
    ) -> None:
        self._queries_total += 1
        self._queries_research += 1
        try:
            origin_q = (origin_code or "").strip().upper()
            dest_q = (dest_code or "").strip().upper()
            if len(origin_q) not in (3, 4) or len(dest_q) not in (3, 4):
                self._queries_not_found += 1
                await interaction.response.send_message(
                    "Use valid IATA/ICAO codes for `origin_code` and `dest_code`.",
                )
                return
            if origin_q == dest_q:
                self._queries_not_found += 1
                await interaction.response.send_message(
                    "`origin_code` and `dest_code` must be different.",
                )
                return

            await interaction.response.defer(thinking=True)
            payload = self.service.get_research_by_codes(origin_q, dest_q)
            if not payload:
                self._queries_not_found += 1
                await interaction.followup.send(
                    f"Research data not found for `{origin_q} -> {dest_q}`.",
                )
                return

            from_code = payload.get("fromAirportCountryCode", "")
            to_code = payload.get("toAirportCountryCode", "")
            from_flag = country_flag(from_code)
            to_flag = country_flag(to_code)
            from_iata = payload.get("fromAirportIata", origin_q)
            to_iata = payload.get("toAirportIata", dest_q)
            route_text = f"{from_iata} {from_flag} -> {to_iata} {to_flag}".strip()

            direct = payload.get("directDemand", {}) if isinstance(payload.get("directDemand"), dict) else {}
            embed = discord.Embed(
                title="Route Research",
                description=route_text,
                color=discord.Color.teal(),
            )
            embed.add_field(name="🌐 Flight Type", value=str(payload.get("flightType", "-")), inline=True)
            distance = payload.get("distance")
            distance_text = f"{format_int(distance)} km" if isinstance(distance, (int, float)) else str(distance)
            embed.add_field(name="📏 Distance", value=distance_text, inline=True)
            embed.add_field(
                name="🤝 Relationship",
                value=relationship_text(payload.get("mutualRelationship")),
                inline=True,
            )
            embed.add_field(name="🧲 Affinity", value=str(payload.get("affinity", "-")), inline=False)

            discount_economy = direct.get("discountEconomy", 0)
            economy = direct.get("economy", 0)
            business = direct.get("business", 0)
            first = direct.get("first", 0)
            economy_total = (discount_economy if isinstance(discount_economy, (int, float)) else 0) + (
                economy if isinstance(economy, (int, float)) else 0
            )
            direct_line = (
                f"{format_int(economy_total)} / "
                f"{format_int(business)} / "
                f"{format_int(first)}"
            )
            embed.add_field(name="👥 Direct Demand", value=direct_line, inline=False)

            from_population = format_int(payload.get("fromAirportPopulation", 0))
            to_population = format_int(payload.get("toAirportPopulation", 0))
            from_income = format_int(payload.get("fromAirportIncome", 0))
            to_income = format_int(payload.get("toAirportIncome", 0))
            from_label = str(payload.get("fromAirportText", from_iata)).split("(")[0].strip() or from_iata
            to_label = str(payload.get("toAirportText", to_iata)).split("(")[0].strip() or to_iata
            population_col = f"{from_label}: {from_population}\n{to_label}: {to_population}"
            income_col = f"{from_label}: ${from_income}\n{to_label}: ${to_income}"
            embed.add_field(name="🏙️ Population", value=population_col, inline=True)
            embed.add_field(name="💰 Income per Capita", value=income_col, inline=True)

            self._queries_success += 1
            await interaction.followup.send(embed=embed)
        except Exception as e:
            self._queries_failed += 1
            self.logger.error("research command failed: %s", e, exc_info=True)
            user_msg = "An error occurred while retrieving route research data. Please try again later."
            if interaction.response.is_done():
                await interaction.followup.send(user_msg)
            else:
                await interaction.response.send_message(user_msg)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def health_snapshot(self) -> ModuleHealth:
        breaker_state = getattr(self.service.client.breaker, "state", "unknown")
        return ModuleHealth(
            status="ok" if self.enabled else "disabled",
            details={
                "enabled": self.enabled,
                "breaker_state": breaker_state,
                **self.service.cache_stats(),
            },
        )

    def stats_snapshot(self) -> ModuleStats:
        return ModuleStats(
            counters={
                "queries_total": self._queries_total,
                "queries_plane": self._queries_plane,
                "queries_airport": self._queries_airport,
                "queries_research": self._queries_research,
                "queries_success": self._queries_success,
                "queries_not_found": self._queries_not_found,
                "queries_failed": self._queries_failed,
                **self.service.cache_stats(),
            }
        )
