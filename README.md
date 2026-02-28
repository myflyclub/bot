# MfcOilAlert

Modular Discord bot for MyFly Club with three feature areas:

- Oil monitoring: polls oil prices, posts updates, and renames the oil channel.
- Route of the Day (ROTD): generates and posts route reports manually or on schedule.
- Aviation info: live lookups for airplane models, airports, and route research data.

The bot is slash-command only (`/`) and runs with a module-based runtime (`oil`, `rotd`, `aviation_info`, `ops`) plus crash recovery, retries, and HTTP circuit breaker support.

## Features

- Slash command interface only (no prefix commands).
- Modular architecture:
  - `oil` module: monitoring, health, stats, channel rename.
  - `rotd` module: random route command + optional daily scheduler.
  - `aviation_info` module: `/plane`, `/airport`, `/research`.
  - `ops` module: crash and system diagnostics.
- Supervised mode (`RUN_SUPERVISED`) for crash recovery and auto-restart.
- Retry helpers for Discord API operations.
- HTTP circuit breaker for external API calls.
- Aggregated module health/stats diagnostics.

## Slash Commands

The bot currently registers:

- `/check`: manual oil refresh.
- `/health`: oil runtime health snapshot.
- `/stats`: oil session counters.
- `/randomroute`: generate and post ROTD now.
- `/plane`: search airplane models by name.
- `/airport`: airport lookup by IATA/ICAO (and by ID when enabled).
- `/research`: research demand/relationship between two airport codes.
- `/crash_stats`: crash handler stats (admin).
- `/system_health`: aggregated health across modules (admin).
- `/system_stats`: aggregated stats across modules (admin).

Note: when `AVIATION_AIRPORT_ID_LOOKUP_ENABLED=true`, `/airport` supports `airport_id` and `code`. Otherwise it supports `code` only.

## Requirements

- Python 3.10+
- Discord bot token
- Discord server/channel IDs

## Setup

1. Clone and enter repo

```powershell
git clone <repo-url>
cd MfcOilAlert
```

2. Create and activate venv

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies

```powershell
pip install -r requirements.txt
```

4. Configure environment

```powershell
Copy-Item env.example .env
```

Then fill `.env` with your values.

## Environment Variables

Current keys from `env.example`:

```env
# Discord Bot Configuration
DISCORD_TOKEN=
DISCORD_OIL_CHANNEL=
DISCORD_RROTD_CHANNEL=

# Oil Price Monitoring Configuration
OIL_PRICE_URL=https://play.myfly.club/oil-prices
POLLING_INTERVAL=180

# MyFly API Configuration
MFC_BASE_URL=https://play.myfly.club
MFC_SEARCH_ROUTE_PATH_TEMPLATE=/search-route/{origin_id}/{dest_id}
MFC_RESEARCH_LINK_PATH_TEMPLATE=/research-link/{origin_id}/{dest_id}
MFC_AIRPORT_BY_ID_PATH_TEMPLATE=/airports/{airport_id}
MFC_AIRPORTS_PATH=/airports
MFC_AIRPLANE_MODELS_PATH=/airplane-models

# Bot Configuration
BOT_STATUS=Testing Aviation Info
CLEAR_GUILD_COMMANDS_ON_STARTUP=false

# Route of the Day (ROTD)
ROTD_ENABLED=true
ROTD_MIN_AIRPORT_SIZE=3
ROTD_MAX_RETRY_ATTEMPTS=100
ROTD_SELECTION_SAFETY_FLOOR_ATTEMPTS=500
ROTD_FALLBACK_MAX_AIRPORT_ID=500
ROTD_DEST_MAX_SIZE_FILTER_ENABLED=true
ROTD_DEST_MAX_SIZE=7
ROTD_MIN_DISTANCE_KM=5500
ROTD_ORIGIN_ID=
ROTD_DEST_ID=
ROTD_SCHEDULE_ENABLED=true
ROTD_SCHEDULE_TZ=UTC
ROTD_SCHEDULE_HOUR=15
ROTD_SCHEDULE_MINUTE=0

# Crash Handler Configuration
MAX_RESTART_ATTEMPTS=5
RESTART_DELAY_BASE=10
EMERGENCY_CHANNEL_ID=
RUN_SUPERVISED=true

# Aviation Info
AVIATION_INFO_ENABLED=true
AVIATION_AIRPORT_ID_LOOKUP_ENABLED=false

# Circuit Breaker (HTTP) Configuration
CB_FAILURE_THRESHOLD=3
CB_OPEN_SECONDS=120
CB_HALF_OPEN_PROBES=1
```

## Run

Recommended launcher:

```powershell
python src\main.py
```

Alternative launcher (same runtime):

```powershell
python src\bot.py
```

`RUN_SUPERVISED` modes:

- `true`: supervised with restart logic.
- `false`: direct run, useful for debugging.

## Verify Functionality

1. Start bot.
2. In Discord:
   - Run `/check` and verify oil embed post.
   - Run `/randomroute` and verify ROTD post.
   - Run `/plane` and `/airport`.
   - Run `/research origin_code:EZE dest_code:JFK` (example).
3. Run diagnostics:
   - `/system_health`
   - `/system_stats`

## Discord Permissions

At minimum, bot role needs:

- View Channels
- Send Messages
- Embed Links
- Manage Channels (required for oil channel rename)

If renaming fails, check channel-level permission overrides for explicit deny.

## Project Structure

```text
MfcOilAlert/
  src/
    bot.py
    main.py
  app/
    application.py
    bootstrap.py
    module_registry.py
    runtime.py
  modules/
    oil/
      module.py
    rotd/
      module.py
    aviation_info/
      module.py
    ops/
      module.py
  shared/
    formatting.py
    module_contract.py
  config/
    config.py
  utils/
    aviation_info_service.py
    bot_supervisor.py
    crash_handler.py
    discord_client_wrapper.py
    health_status.py
    http_client.py
    mfc_api.py
    price_monitor.py
    price_parser.py
    rotd_formatter.py
    rotd_service.py
  env.example
  requirements.txt
```

## Architecture Notes

- `src/bot.py` is thin and delegates lifecycle to modular runtime/application services.
- `app/bootstrap.py` wires dependencies and module registration.
- Feature behavior is encapsulated in `modules/*`.
- Reusable technical services live in `utils/*`.

## Troubleshooting

### Slash command missing in Discord

- Verify corresponding feature flag in `.env`:
  - `/randomroute` requires `ROTD_ENABLED=true`.
  - `/plane`, `/airport`, `/research` require `AVIATION_INFO_ENABLED=true`.
- Restart bot after changing `.env`.
- Check startup logs for command sync.

### `/airport` does not accept `airport_id`

- Set `AVIATION_AIRPORT_ID_LOOKUP_ENABLED=true` and restart.

### Bot starts but command says "application did not respond"

- Check logs for exceptions in command handlers.
- Verify channel IDs and permissions.

### Oil channel does not rename

- Ensure bot has `Manage Channels` in role and channel overrides.

## Security

- Do not commit `.env`.
- Rotate `DISCORD_TOKEN` if it was ever exposed.
