# MfcOilAlert

Modular Discord bot for MyFly Club with two core services:

- Oil monitoring: polls oil prices, posts updates, and renames the oil channel.
- Route of the Day (ROTD): generates and posts random route reports.

The bot uses slash commands (`/`) and a modular runtime (`oil`, `rotd`, `ops`) with crash recovery and retry logic.

## Features

- Slash command interface only (no prefix commands).
- Modular architecture:
  - `oil` module: monitoring, health, stats, channel rename.
  - `rotd` module: random route command + daily posting loop.
  - `ops` module: crash and system diagnostics.
- Crash recovery and supervised mode.
- Circuit breaker and retry handling for HTTP/Discord calls.
- Aggregated module diagnostics.

## Commands

The bot registers these slash commands:

- `/check`: manual oil refresh.
- `/health`: oil runtime health snapshot.
- `/stats`: oil session counters.
- `/randomroute`: generate and post ROTD now.
- `/crash_stats`: crash handler stats (admin).
- `/system_health`: aggregated health across modules (admin).
- `/system_stats`: aggregated stats across modules (admin).

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

Current `env.example` keys:

```env
# Discord
DISCORD_TOKEN=
DISCORD_OIL_CHANNEL=
DISCORD_RROTD_CHANNEL=

# Bot
BOT_STATUS=Monitoring Oil Prices
RUN_SUPERVISED=true

# Oil
OIL_PRICE_URL=https://play.myfly.club/oil-prices
POLLING_INTERVAL=180

# ROTD
ROTD_ENABLED=true
ROTD_MIN_AIRPORT_SIZE=3
ROTD_MAX_RETRY_ATTEMPTS=100
ROTD_ORIGIN_ID=
ROTD_DEST_ID=

# Crash recovery
MAX_RESTART_ATTEMPTS=5
RESTART_DELAY_BASE=10
EMERGENCY_CHANNEL_ID=

# Circuit breaker
CB_FAILURE_THRESHOLD=3
CB_OPEN_SECONDS=120
CB_HALF_OPEN_PROBES=1
```

## Run

Standard run:

```powershell
python src\bot.py
```

This supports both modes using `RUN_SUPERVISED`:

- `true`: supervised with restart logic.
- `false`: direct run, useful for debugging.

Alternative launcher (same runtime):

```powershell
python src\main.py
```

## Verify Functionality

1. Start bot (`python src\bot.py`).
2. In Discord:
- run `/check` and verify oil embed post.
- run `/randomroute` and verify ROTD post.
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
    ops/
      module.py
  config/
    config.py
  utils/
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

- `src/bot.py` is now thin: bootstraps app, delegates startup to runtime, and starts Discord.
- `app/bootstrap.py` wires dependencies and modules.
- Business behavior is encapsulated in feature modules.
- `utils/` holds reusable technical services (HTTP clients, monitoring primitives, retry wrappers).

## Troubleshooting

### `/randomroute` missing in Discord

- Ensure `ROTD_ENABLED=true` in `.env`.
- Restart bot.
- Wait for startup sync logs (`global` and `guild` sync).

### Bot starts but command says "application did not respond"

- Check bot logs for exceptions in command handlers.
- Verify channel IDs and permissions.

### Oil channel does not rename

- Ensure bot has `Manage Channels` in role and channel overrides.

### Multiple bot instances

Stop all local bot processes:

```powershell
Get-CimInstance Win32_Process |
Where-Object { $_.Name -match '^python(\\.exe)?$' -and ($_.CommandLine -match 'src\\bot.py' -or $_.CommandLine -match 'src\\main.py' -or $_.CommandLine -match 'MfcOilAlert') } |
ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## Security

- Do not commit `.env`.
- Rotate `DISCORD_TOKEN` if it was ever exposed.
