# MyFly Club Multitask Discord Bot v2

A production-ready multitask Discord bot featuring **oil price monitoring** and **daily Route of the Day (ROTD)** from [MyFly Club](https://play.myfly.club) with comprehensive crash recovery, health monitoring, and advanced error handling capabilities.

## ✨ v2 Features

### 🎯 **Multitask Bot Architecture**
- **🛢️ Oil Price Monitoring**: Real-time monitoring and alerts for MyFly Club oil prices
- **✈️ Route of the Day (ROTD)**: Daily random route generation with detailed flight information
- **🔧 Extensible Design**: Clean separation for multiple independent features
- **📱 Dual Channel Support**: Separate Discord channels for oil alerts and ROTD posts

### ✈️ **Route of the Day (ROTD) Features**
- **🎲 Random Route Selection**: Smart algorithm picks random valid airport pairs from MyFly Club
- **📊 Comprehensive Route Data**: Distance, runway restrictions, demand statistics, and more
- **🌍 Country Information**: Population, income, relationships, affinities, and flag emojis
- **✈️ Detailed Itineraries**: Flight codes, aircraft types, duration, amenities, and pricing
- **💰 Best Deals Highlighting**: Automatically identifies best price and most popular routes
- **🏆 Airport Charms**: Display airport features and their strength ratings
- **⚙️ Configurable Filters**: Minimum airport size and maximum retry attempts
- **🧪 Manual Generation**: `!randomroute` command for on-demand route generation

### 🛡️ **Production Stability & Reliability**
- **🔄 Automatic Crash Recovery**: Comprehensive crash detection with exponential backoff restart logic
- **📱 Discord Crash Alerts**: Instant notifications with detailed error information and stack traces
- **🏥 Health Monitoring**: Real-time bot health diagnostics with `!health` and `!stats` commands
- **🔧 Supervised Execution**: Process-level supervision with configurable restart limits
- **⚡ Circuit Breaker**: HTTP resilience with automatic failure detection and recovery

### 📊 **Enhanced Monitoring & Performance**
- **💾 In-Memory Architecture**: Pure in-memory operation with zero file dependencies (v2 improvement)
- **🔍 Smart Polling**: Adaptive polling intervals with content change detection
- **📈 Session Statistics**: Real-time tracking of updates, changes, and performance metrics
- **🌐 Discord API Resilience**: Advanced retry logic with rate limit handling and backoff strategies
- **⏰ UTC Timestamps**: Precise timing information on all price updates

### 🎯 **Core Oil Price Features**
- **📝 Automatic Channel Renaming**: Dynamic channel names with prices and trend indicators (📈/📉)
- **📊 Rich Price Notifications**: Detailed Discord embeds with price changes and statistics
- **🔍 JSON Endpoint Monitoring**: Efficient parsing of cycle-based price data
- **📱 Manual Commands**: `!check`, `!health`, `!stats`, `!crash-stats` for monitoring and control

### ✈️ **ROTD API Integration**
- **🌐 Airport Data**: Full airport details including IATA codes, population, and features
- **🔍 Route Search**: Itinerary discovery with pricing, carriers, and flight details
- **📊 Research Data**: Demand statistics, country relationships, and economic indicators
- **⚡ Circuit Breaker Protection**: Resilient API calls with automatic retry and failure handling

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Discord Server with appropriate permissions

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token (you'll need this later)
5. Enable the following bot permissions:
   - Send Messages
   - Manage Channels (for renaming)
   - Read Message History
   - Use Slash Commands

### 2. Invite Bot to Your Server

1. Go to "OAuth2" → "URL Generator"
2. Select "bot" scope
3. Select the permissions mentioned above
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Get Channel IDs

1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on the channel for oil price alerts and click "Copy ID"
3. Right-click on the channel for Route of the Day and click "Copy ID"
   - You can use the same channel for both features if desired

### 4. Clone and Setup Repository

```bash
git clone <your-repo-url>
cd MfcOilAlert
```

### 5. Create Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Configure Environment Variables

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` file with your values:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   DISCORD_OIL_CHANNEL=your_oil_channel_id_here
   DISCORD_RROTD_CHANNEL=your_rotd_channel_id_here
   OIL_PRICE_URL=https://play.myfly.club/oil-prices
   POLLING_INTERVAL=180
   BOT_PREFIX=!
   BOT_STATUS=Monitoring Oil Prices
   
   # Enable ROTD feature
   ROTD_ENABLED=true
   ROTD_MIN_AIRPORT_SIZE=3
   ROTD_MAX_RETRY_ATTEMPTS=100
   ```

### 8. Run the Bot

#### 🚀 Production Mode (Recommended)
```bash
# Run with supervised execution and crash recovery
python src/bot.py
```
*The bot automatically runs in supervised mode when `RUN_SUPERVISED=true` (default)*

#### 🧪 Development Mode  
```bash
# Run without crash recovery (for development/testing)
RUN_SUPERVISED=false python src/bot.py
```

## 🚀 Production Deployment

### Recommended Production Setup

The v2 bot is designed for 24/7 production deployment with comprehensive reliability features:

#### 1. **Supervised Execution** (Default)
- Set `RUN_SUPERVISED=true` in your `.env` file
- Bot automatically restarts after crashes with exponential backoff
- Maximum restart attempts configurable via `MAX_RESTART_ATTEMPTS`

#### 2. **Crash Recovery Configuration**
```env
# Recommended production settings
MAX_RESTART_ATTEMPTS=5        # Stop after 5 failed restarts
RESTART_DELAY_BASE=10         # Start with 10-second delays
EMERGENCY_CHANNEL_ID=12345    # Separate channel for crash alerts
```

#### 3. **Circuit Breaker Setup**
```env
# HTTP resilience settings
CB_FAILURE_THRESHOLD=3        # Open after 3 consecutive failures
CB_OPEN_SECONDS=120          # 2-minute cooldown period
CB_HALF_OPEN_PROBES=1        # Single probe in half-open state
```

#### 4. **Monitoring & Health Checks**
- Use `!health` command to monitor bot status
- Set up `!crash-stats` monitoring for reliability tracking
- Monitor Discord for crash alert notifications

### 🔧 **Production Benefits**
- **99%+ Uptime**: Automatic crash recovery ensures continuous operation
- **Instant Alerts**: Get notified immediately when issues occur
- **Zero File Dependencies**: Pure in-memory operation eliminates I/O failures
- **Circuit Breaker Protection**: HTTP failures don't crash the entire bot
- **Comprehensive Logging**: Detailed error tracking for troubleshooting

### 📊 **Deployment Verification**
After deployment, verify the bot is working correctly:

1. **Check Health**: Run `!health` to see system status
2. **Test Commands**: Use `!check` to trigger manual price update
3. **Monitor Stats**: Use `!stats` to verify monitoring is active
4. **Crash Recovery**: Check `!crash-stats` shows zero crashes initially

## How It Works (v2 Architecture)

The bot operates with a sophisticated v2 multitask architecture designed for production reliability:

### 🏗️ **Supervised Execution**
1. **Bot Supervisor** manages the main bot process with automatic restart capabilities
2. **Crash Handler** detects failures and implements exponential backoff recovery
3. **Health Monitor** continuously tracks bot performance and system status

### �️ **Smart Oil Price Monitoring**
1. **Fetches prices** from JSON endpoint every 3 minutes (configurable via `POLLING_INTERVAL`)
2. **Circuit Breaker** protects against API failures with automatic recovery
3. **Content Detection** uses hashing and cycle number comparison for efficiency
4. **In-Memory Processing** eliminates file I/O for better performance (v2 improvement)

### ✈️ **Route of the Day (ROTD) System**
1. **Daily Scheduling**: Posts a new random route every 24 hours (8 AM UTC by default)
2. **Smart Selection Algorithm**:
   - Fetches max airport ID from MyFly Club API (one-time initialization)
   - Generates random airport IDs within valid range
   - Validates both airports meet minimum size requirements (configurable)
   - Checks for available routes via search-route endpoint
   - Retries up to 100 times (configurable) to find a valid pair
3. **Data Aggregation**:
   - Airport details (name, IATA code, population, income, features/charms)
   - Route research (distance, demand, relationships, affinities)
   - Itinerary search (carriers, pricing, aircraft, amenities, duration)
4. **Rich Formatting**:
   - Country flag emojis next to airport names
   - Detailed flight information with icons and formatting
   - Highlights best deals and most popular routes
   - Professional Discord message format

### 💬 **Discord Integration**
1. **Oil Price Channel**: Renames channel with price and trend indicators (e.g., `oil-price💲76-28📈`)
2. **ROTD Channel**: Posts daily route with rich formatting and detailed information
3. **Rich Notifications** with detailed price change information and UTC timestamps
4. **Retry Logic** handles Discord API rate limits and transient failures
5. **Emergency Alerts** for crash notifications with detailed diagnostics

## 🎮 Available Commands

### Core Commands
- **`!check`** - Manually trigger price update and force refresh
- **`!health`** - Display comprehensive bot health status
- **`!stats`** - Show session statistics and monitoring metrics
- **`!crash-stats`** - View crash recovery statistics and history

### Route of the Day Commands
- **`!randomroute`** - Generate and post a random route on demand (same as daily ROTD)

### Health Command Example
```
🏥 Bot Health Status
⏰ Uptime: 2h 34m 12s
🔄 Monitoring: Active
💰 Current Price: $76.28 (Cycle: 6548)
🌐 Discord: Connected (2 guilds, 45ms latency)
🔧 HTTP Status: Healthy (last response: 12s ago)
⚡ Circuit Breaker: Closed (0/3 failures)
📊 Session: 47 updates processed, 3 changes detected
```

### Stats Command Example
```
📊 Bot Session Statistics
⏱️ Session Duration: 2h 34m 12s
🔄 Total Updates Processed: 47
📈 Price Changes Detected: 3
💰 Last Price: $76.28 (Cycle: 6548)
📅 Last Change: 23 minutes ago (+$2.15, +2.89%)
```

## 🏗️ Project Structure (v2)

```
MfcOilAlert/
├── src/
│   └── bot.py                      # Main Discord bot with multitask features
├── config/
│   └── config.py                   # Configuration with v2 + ROTD settings
├── utils/                          # v2 Enhanced utility modules
│   ├── __init__.py
│   ├── bot_supervisor.py           # 🔧 Bot lifecycle management & auto-restart
│   ├── crash_handler.py            # 🛡️ Comprehensive crash detection & recovery
│   ├── discord_client_wrapper.py   # 🌐 Discord API retry logic & rate limiting
│   ├── health_status.py            # 🏥 Health monitoring & diagnostic aggregation
│   ├── http_client.py              # ⚡ HTTP client with circuit breaker pattern
│   ├── mfc_api.py                  # ✈️ MyFly Club API client for ROTD
│   ├── rotd_service.py             # ✈️ Route of the Day selection & data aggregation
│   ├── rotd_formatter.py           # ✈️ ROTD message formatting for Discord
│   ├── price_monitor.py            # 📊 In-memory price monitoring (v2: no file I/O)
│   └── price_parser.py             # 🔍 JSON response parser
├── examples/                       # Example API responses for reference
│   ├── airportExample.json
│   ├── researchExample.json
│   └── searchExample.json
├── test_*.py                       # 🧪 Comprehensive v2 test suite
├── requirements.txt                # Python dependencies
├── env.example                     # v2 Environment variables with all features
└── README.md                       # This documentation
```

### 🔧 v2 Module Overview

| Module | Purpose | v2 Enhancement |
|--------|---------|----------------|
| **bot_supervisor.py** | Process supervision & lifecycle management | ✨ **NEW** - Automatic restart with exponential backoff |
| **crash_handler.py** | Crash detection & recovery system | ✨ **NEW** - Discord alerts & error tracking |
| **discord_client_wrapper.py** | Discord API resilience layer | ✨ **NEW** - Retry logic & rate limit handling |
| **health_status.py** | Health monitoring & diagnostics | ✨ **NEW** - Real-time status aggregation |
| **mfc_api.py** | MyFly Club API client | ✨ **NEW** - Airports, routes, and research endpoints |
| **rotd_service.py** | Route of the Day logic | ✨ **NEW** - Smart random selection & data aggregation |
| **rotd_formatter.py** | ROTD message formatting | ✨ **NEW** - Rich Discord message generation |
| **http_client.py** | HTTP client with circuit breaker | 🔄 **ENHANCED** - Added circuit breaker pattern |
| **price_monitor.py** | Price monitoring system | 🔄 **ENHANCED** - Pure in-memory architecture |

## ⚙️ Configuration Options (v2)

### Core Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | **Required** |
| `DISCORD_OIL_CHANNEL` | Oil price alerts channel ID | Optional |
| `DISCORD_RROTD_CHANNEL` | Route of the Day channel ID | Optional |
| `OIL_PRICE_URL` | Oil price JSON endpoint | `https://play.myfly.club/oil-prices` |
| `POLLING_INTERVAL` | Price check interval (seconds) | `180` (3 minutes) |
| `BOT_PREFIX` | Command prefix | `!` |
| `BOT_STATUS` | Bot status message | `Monitoring Oil Prices` |

### ✈️ Route of the Day (ROTD) Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `ROTD_ENABLED` | Enable/disable ROTD feature | `false` |
| `ROTD_MIN_AIRPORT_SIZE` | Minimum airport size filter (1-5) | `3` |
| `ROTD_MAX_RETRY_ATTEMPTS` | Max attempts to find valid route | `100` |
| `ROTD_ONCE` | Run ROTD once and exit (env override) | `false` |
| `ROTD_ORIGIN_ID` | Test mode: specific origin airport ID | Empty (random) |
| `ROTD_DEST_ID` | Test mode: specific destination airport ID | Empty (random) |

### 🛡️ v2 Crash Recovery Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_RESTART_ATTEMPTS` | Maximum restart attempts before giving up | `5` |
| `RESTART_DELAY_BASE` | Base delay for exponential backoff (seconds) | `10` |
| `EMERGENCY_CHANNEL_ID` | Separate channel for crash alerts (optional) | Empty (uses main channel) |
| `RUN_SUPERVISED` | Enable supervised execution with crash recovery | `true` |

### ⚡ Circuit Breaker Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `CB_FAILURE_THRESHOLD` | Consecutive failures before opening breaker | `3` |
| `CB_OPEN_SECONDS` | Cooldown period before attempting recovery | `120` |
| `CB_HALF_OPEN_PROBES` | Number of test requests in half-open state | `1` |

### 📝 Complete .env Example
```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_OIL_CHANNEL=your_oil_channel_id_here
DISCORD_RROTD_CHANNEL=your_rrotd_channel_id_here

# Oil Price Monitoring
OIL_PRICE_URL=https://play.myfly.club/oil-prices
POLLING_INTERVAL=180  # 3 minutes

# Bot Settings
BOT_PREFIX=!
BOT_STATUS=Monitoring Oil Prices

# Route of the Day (ROTD)
ROTD_ENABLED=true
ROTD_MIN_AIRPORT_SIZE=3
ROTD_MAX_RETRY_ATTEMPTS=100
ROTD_ONCE=false
ROTD_ORIGIN_ID=
ROTD_DEST_ID=

# v2 Crash Recovery System
MAX_RESTART_ATTEMPTS=5
RESTART_DELAY_BASE=10
EMERGENCY_CHANNEL_ID=  # Optional: separate crash alert channel
RUN_SUPERVISED=true   # Recommended for production

# v2 Circuit Breaker (HTTP Resilience)
CB_FAILURE_THRESHOLD=3
CB_OPEN_SECONDS=120
CB_HALF_OPEN_PROBES=1
```

## 🏛️ v2 Architecture Overview

The v2 architecture is designed for production reliability with comprehensive error handling, monitoring, and multitask support:

### 🔧 **Supervision Layer**
- **Bot Supervisor** (`bot_supervisor.py`): Process-level management with automatic restart
- **Crash Handler** (`crash_handler.py`): Global exception handling with Discord alerting
- **Health Aggregator** (`health_status.py`): Real-time system diagnostics and metrics

### 📊 **Core Application Layer**
- **Discord Bot** (`src/bot.py`): Main multitask application with v2 integrations and command handling
- **Price Monitor** (`price_monitor.py`): In-memory price tracking with session statistics
- **Price Parser** (`price_parser.py`): JSON response parsing and cycle-based price extraction
- **ROTD Service** (`rotd_service.py`): Random route selection and data aggregation
- **ROTD Formatter** (`rotd_formatter.py`): Rich Discord message formatting for routes

### 🌐 **Network & API Layer**
- **HTTP Client** (`http_client.py`): Smart polling with circuit breaker pattern
- **MFC API Client** (`mfc_api.py`): MyFly Club API wrapper with retry logic
- **Discord Wrapper** (`discord_client_wrapper.py`): Retry logic and rate limit handling
- **Configuration** (`config/config.py`): Environment-based settings with v2 + ROTD parameters

### 🔄 **Data Flow (v2 Multitask Architecture)**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bot Supervisor │    │   Crash Handler  │    │  Health Monitor │
│   (Lifecycle)    │───▶│   (Recovery)     │───▶│   (Diagnostics) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Discord Bot (Main)                          │
│                    (Multitask Coordinator)                       │
└─────────────────────────────────────────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────┐
│  Oil Price Monitor   │              │    ROTD Service          │
│   (Feature 1)        │              │    (Feature 2)           │
└──────────────────────┘              └──────────────────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────┐
│   Price Parser       │              │   MFC API Client         │
│   (JSON Parsing)     │              │   (Airports/Routes)      │
└──────────────────────┘              └──────────────────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────┐
│   HTTP Client        │◀─────────────│   ROTD Formatter         │
│ (Circuit Breaker)    │              │ (Discord Messages)       │
└──────────────────────┘              └──────────────────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────┐
│  Oil Price API       │              │  MyFly Club API          │
│ (External API)       │              │  (External API)          │
└──────────────────────┘              └──────────────────────────┘
```

### 🛡️ **Resilience Features**
- **Automatic Restart**: Exponential backoff with configurable limits
- **Circuit Breaker**: HTTP failure protection with automatic recovery  
- **Discord Resilience**: Rate limit handling and retry mechanisms
- **Health Monitoring**: Real-time diagnostics and performance tracking
- **Memory Architecture**: Zero file dependencies for improved reliability

## Message Format

### Oil Price Updates
All price updates use a unified format:
```
🔄 Oil Price Updated!
Automatic price update detected
💰 Old Price: $72.59
💰 New Price: $76.28
🔄 Cycle: 6548
📊 Change: $+3.69 (+5.08%)
⏰ Time: 14:30 UTC
```

### Route of the Day (ROTD) Format
Daily routes are posted with comprehensive information:
```
Random Route of the Day: 29 October 2025

Stockholm Arlanda Airport (ARN) 🇸🇪 - Singapore Changi Airport (SIN) 🇸🇬

Distance (direct): 9,875 km
Runway Restriction: 3,700m (SIN)
Population: 2,584,392 / 5,935,053
Income per Capita, PPP: $85,957 / $94,100
Relationship between Countries: 1 (Good)
Affinities: +1: Trade Relations
Flight Type: International
Direct Demand: 114 / 7 / –

No existing direct links

Tickets

Best Deal
ARN - HEL - SIN — $738 (Economy)
🛫 ARN - HEL 🛫
Finnair - AY 768 | Airbus A320neo | Duration: 55 minutes | $89 (Economy) with 65 quality including IFE, wifi
🛫 HEL - SIN 🛫
Finnair - AY 095 | Airbus A350-900 | Duration: 11 hours 30 minutes | $649 (Economy) with 82 quality including hot meal service, IFE, power outlet

Best Seller
ARN - DOH - SIN — $856 (Economy)
🛫 ARN - DOH 🛫
Qatar Airways - QR 170 | Boeing 787-9 | Duration: 6 hours 35 minutes | $499 (Economy) with 89 quality including hot meal service, IFE, wifi
🛫 DOH - SIN 🛫
Qatar Airways - QR 944 | Airbus A350-1000 | Duration: 7 hours 40 minutes | $357 (Economy) with 89 quality including hot meal service, IFE, power outlet
```

## 🔧 Troubleshooting

### Bot Connection Issues
- **Token Problems**: Check if your `DISCORD_TOKEN` is correct in `.env`
- **Permission Errors**: Ensure bot has "Manage Channels" and "Send Messages" permissions
- **Channel Access**: Verify bot can see the channels specified in `DISCORD_OIL_CHANNEL` and `DISCORD_RROTD_CHANNEL`

### ROTD Issues
- **Not Posting**: Check that `ROTD_ENABLED=true` in `.env`
- **No Valid Routes Found**: Increase `ROTD_MAX_RETRY_ATTEMPTS` (default: 100)
- **Airport Size Issues**: Lower `ROTD_MIN_AIRPORT_SIZE` to include smaller airports (minimum: 1)
- **Manual Testing**: Use `!randomroute` command to test route generation on demand
- **Specific Route Testing**: Set `ROTD_ORIGIN_ID` and `ROTD_DEST_ID` in `.env` to test with specific airports
- **API Errors**: Check logs for MyFly Club API connectivity issues

### v2 Crash Recovery Issues
- **Restart Loops**: Check `!crash-stats` to see restart attempts and reasons
- **Max Restarts Exceeded**: Review crash logs and increase `MAX_RESTART_ATTEMPTS` if needed
- **Emergency Alerts**: If `EMERGENCY_CHANNEL_ID` is set, check that channel for crash notifications

### Circuit Breaker Issues
- **HTTP Failures**: Use `!health` to check circuit breaker state
- **Open Circuit**: Wait for cooldown period (`CB_OPEN_SECONDS`) or manually trigger `!check`
- **API Unreachable**: Verify `OIL_PRICE_URL` is accessible

### Performance Issues
- **Memory Usage**: Use `!health` to monitor system performance
- **Polling Delays**: Check `POLLING_INTERVAL` setting and network connectivity
- **Discord Rate Limits**: Bot automatically handles rate limits with retry logic

### Configuration Issues
- **Environment Variables**: Ensure all required variables are set in `.env`
- **Invalid Values**: Check logs for configuration validation errors
- **Supervised Mode**: Set `RUN_SUPERVISED=false` for debugging without auto-restart

## 📦 Dependencies

- **discord.py==2.3.2** - Discord API wrapper with async support
- **requests==2.31.0** - HTTP requests with retry logic and session management
- **beautifulsoup4==4.12.2** - HTML parsing utilities (if needed for future features)
- **python-dotenv==1.0.0** - Environment variable management and configuration
- **html5lib==1.1** - HTML parsing library for robust content handling

## 🎯 v2 Summary & Production Readiness

### ✅ **What's New in v2**
The MyFly Club Multitask Discord Bot v2 represents a complete production-ready rewrite with enterprise-grade reliability and multitask capabilities:

- **🛡️ Comprehensive Crash Recovery**: Automatic restart with exponential backoff and Discord alerting
- **💾 In-Memory Architecture**: Zero file dependencies for improved performance and reliability  
- **⚡ Circuit Breaker Pattern**: HTTP resilience with automatic failure detection and recovery
- **🏥 Health Monitoring**: Real-time diagnostics with `!health`, `!stats`, and `!crash-stats` commands
- **🌐 Discord API Resilience**: Advanced retry logic with rate limit handling and backoff strategies
- **🔧 Supervised Execution**: Process-level management for 24/7 production deployment
- **✈️ Route of the Day (ROTD)**: Daily random route generation with rich flight information from MyFly Club
- **🎯 Multitask Architecture**: Clean separation for multiple independent features with extensibility

### 🚀 **Production Ready Features**
- **99%+ Uptime**: Automatic recovery from crashes and network failures
- **Dual Feature Support**: Independent oil price monitoring and daily route generation
- **Instant Monitoring**: Real-time health checks and performance metrics
- **Zero Maintenance**: Self-healing architecture with comprehensive error handling
- **Scalable Design**: In-memory operation suitable for containerized deployments
- **Comprehensive Testing**: Automated tests covering all v2 functionality
- **Rich Discord Integration**: Separate channels, formatted messages, and emoji support

### 📊 **Deployment Confidence**
The v2 bot has been thoroughly tested and validated for production use:
- **Crash Recovery**: Tested with various failure scenarios and recovery patterns
- **Network Resilience**: Validated against API failures, rate limits, and connectivity issues  
- **Performance**: Benchmarked for memory usage, response times, and long-term stability
- **Integration**: Full end-to-end testing of all v2 components working together
- **ROTD System**: Validated route selection algorithm, API integration, and message formatting

**Ready for Production**: Deploy with confidence using `RUN_SUPERVISED=true` for maximum reliability.

### ✈️ **ROTD Features**
The Route of the Day system provides:
- **Smart Random Selection**: Intelligent algorithm finds valid airport pairs efficiently
- **Comprehensive Data**: Distance, demand, pricing, relationships, and more
- **Rich Formatting**: Country flags, flight details, amenities, and professional layout
- **Best Deal Highlighting**: Automatically identifies best price and most popular routes
- **Flexible Configuration**: Adjustable airport size filters and retry limits
- **On-Demand Generation**: `!randomroute` command for manual route generation anytime
- **Testing Support**: Specific route testing with `ROTD_ORIGIN_ID` and `ROTD_DEST_ID`

## 📄 License

[Add your license here]

## 🆘 Support

For issues, questions, or feature requests:
- **Issues**: [Create an issue](link-to-issues) in this repository
- **v2 Features**: All v2 functionality is fully documented in this README
- **Health Monitoring**: Use `!health` command for real-time bot diagnostics
- **Crash Recovery**: Check `!crash-stats` for reliability information