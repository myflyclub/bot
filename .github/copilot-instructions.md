
# Copilot Instructions for MfcOilAlert


## Project Goal
- **Multitask Bot Objective:**
  - Convert the bot into a multitask Discord bot, keeping all current oil price monitoring features fully functional.
  - Add a second feature: a Discord bot that publishes a randomly generated "route of the day" from MyFly Club.
  - Ensure the architecture supports multiple independent features, with clear separation and extensibility for future tasks.

## New Feature: Route of the Day (ROTD)
- **Purpose:**
  - Every 24 hours, the bot posts a randomly generated "route of the day" to a configured Discord channel.
  - The route is selected from airport pairs with available itineraries using MyFly Club API endpoints (route search and research data).
- **Configurable:**
  - Minimum airport size filter (default: 3).
- **Report Content:**
  - Distance between airports
  - Runway restrictions
  - Population data
  - Income per capita (PPP)
  - Country relationships and affinities
  - Flight type (International/Domestic)
  - Direct demand statistics
  - Country flag emojis next to airport names
  - Highlights best deals based on price and popularity
  - Detailed itinerary information:
    - Carrier and flight codes
    - Aircraft types
    - Flight duration
    - Amenities (meals, IFE, wifi, etc.)
    - Pricing
- **Other Features:**
  - Supports a `--once` CLI flag for testing (runs the ROTD logic once and exits).

## Project Overview
- **Purpose:** Discord bot for monitoring oil prices from https://play.myfly.club/oil-prices with production-grade reliability, crash recovery, and health monitoring.
- **Core Architecture:**
  - `src/bot.py`: Main entry point, Discord command handling, integrates all v2 features.
  - `utils/`: Key modules for supervision, crash handling, Discord API resilience, health monitoring, HTTP client (with circuit breaker), price monitoring, and parsing.
  - `config/config.py`: Loads environment variables and configures all resilience features.
- **In-Memory Design:** No file-based state; all monitoring and stats are kept in memory for reliability.

## Key Patterns & Workflows
- **Supervised Execution:**
  - Default: Bot runs under supervision (`RUN_SUPERVISED=true`), auto-restarts on crash with exponential backoff (see `utils/bot_supervisor.py`).
  - Crash recovery and Discord alerting handled by `utils/crash_handler.py`.
- **Health & Stats:**
  - Use Discord commands: `!health`, `!stats`, `!crash-stats` for diagnostics and monitoring.
  - Health/status aggregation in `utils/health_status.py`.
- **HTTP Resilience:**
  - All HTTP calls use a circuit breaker pattern (`utils/http_client.py`).
  - Circuit breaker config via `.env` (see `env.example`).
- **Discord API Handling:**
  - All Discord API calls are wrapped for retry and rate limit handling (`utils/discord_client_wrapper.py`).
  - Channel renaming and rich notifications are core features.
- **Price Monitoring:**
  - Polls JSON endpoint at interval (`POLLING_INTERVAL`), detects changes by hash/cycle, and updates Discord.
  - All logic is in-memory (`utils/price_monitor.py`).

## Developer Workflows
- **Setup:**
  - Copy `env.example` to `.env` and fill required values.
  - Install dependencies: `pip install -r requirements.txt`.
  - Run: `python src/bot.py` (supervised by default).
- **Testing:**
  - Tests are named `test_*.py` (not included in repo structure above, but referenced in README).
- **Debugging:**
  - Set `RUN_SUPERVISED=false` in `.env` to disable auto-restart for local debugging.

## Project-Specific Conventions
- **Environment variables** are the only config mechanism (see `env.example`).
- **No persistent storage**: All state is ephemeral and in-memory.
- **Crash notifications**: Sent to Discord, optionally to a separate channel (`EMERGENCY_CHANNEL_ID`).
- **Commands**: All bot commands use the prefix from `BOT_PREFIX` (default: `!`).
- **Rich Discord embeds**: All price updates and alerts use a consistent, detailed format.

## Integration Points
- **Discord API**: All bot actions and notifications.
- **Oil Price API**: JSON endpoint at `OIL_PRICE_URL`.

## Examples
- **Add a new health metric:** Implement in `utils/health_status.py`, expose via `!health`.
- **Change polling interval:** Update `POLLING_INTERVAL` in `.env`.
- **Add a new command:** Implement in `src/bot.py` using the command prefix.

## References
- See `README.md` for full architecture, config, and troubleshooting details.
- See `env.example` for all required and optional environment variables.
- Key modules: `utils/bot_supervisor.py`, `utils/crash_handler.py`, `utils/discord_client_wrapper.py`, `utils/health_status.py`, `utils/http_client.py`, `utils/price_monitor.py`, `utils/price_parser.py`.

---

**Update this file if you introduce new modules, commands, or architectural changes.**
