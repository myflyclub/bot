import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the Oil Price Alert Bot"""
    
    # Discord Configuration
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    # New: separate channel IDs for oil and ROTD
    DISCORD_OIL_CHANNEL = os.getenv('DISCORD_OIL_CHANNEL')
    DISCORD_RROTD_CHANNEL = os.getenv('DISCORD_RROTD_CHANNEL')
    
    # Oil Price Monitoring Configuration
    OIL_PRICE_URL = os.getenv('OIL_PRICE_URL', 'https://play.myfly.club/oil-prices')
    
    # Parse POLLING_INTERVAL, handling comments and whitespace
    _polling_raw = os.getenv('POLLING_INTERVAL', '300')
    if _polling_raw:
        # Remove comments and strip whitespace
        _polling_clean = _polling_raw.split('#')[0].strip()
        try:
            POLLING_INTERVAL = int(_polling_clean)
        except ValueError:
            print(f"Warning: Invalid POLLING_INTERVAL '{_polling_raw}', using default 300")
            POLLING_INTERVAL = 300
    else:
        POLLING_INTERVAL = 300
    
    # Bot Configuration
    BOT_STATUS = os.getenv('BOT_STATUS', 'Monitoring Oil Prices')
    
    # ROTD Feature Configuration
    ROTD_ENABLED = os.getenv('ROTD_ENABLED', 'false').lower() == 'true'
    ROTD_MIN_AIRPORT_SIZE = int(os.getenv('ROTD_MIN_AIRPORT_SIZE', '3'))
    ROTD_MAX_RETRY_ATTEMPTS = int(os.getenv('ROTD_MAX_RETRY_ATTEMPTS', '100'))
    # Optional explicit test pair for ROTD
    ROTD_ORIGIN_ID = os.getenv('ROTD_ORIGIN_ID')
    ROTD_DEST_ID = os.getenv('ROTD_DEST_ID')
    ROTD_SCHEDULE_ENABLED = os.getenv('ROTD_SCHEDULE_ENABLED', 'false').lower() == 'true'
    ROTD_SCHEDULE_TZ = os.getenv('ROTD_SCHEDULE_TZ', 'UTC')
    _rotd_hour_raw = os.getenv('ROTD_SCHEDULE_HOUR', '15')
    _rotd_minute_raw = os.getenv('ROTD_SCHEDULE_MINUTE', '0')
    try:
        ROTD_SCHEDULE_HOUR = int((_rotd_hour_raw or '15').split('#')[0].strip())
    except ValueError:
        print(f"Warning: Invalid ROTD_SCHEDULE_HOUR '{_rotd_hour_raw}', using default 15")
        ROTD_SCHEDULE_HOUR = 15
    try:
        ROTD_SCHEDULE_MINUTE = int((_rotd_minute_raw or '0').split('#')[0].strip())
    except ValueError:
        print(f"Warning: Invalid ROTD_SCHEDULE_MINUTE '{_rotd_minute_raw}', using default 0")
        ROTD_SCHEDULE_MINUTE = 0
    if ROTD_SCHEDULE_HOUR < 0 or ROTD_SCHEDULE_HOUR > 23:
        print(f"Warning: ROTD_SCHEDULE_HOUR '{ROTD_SCHEDULE_HOUR}' out of range 0-23, using default 15")
        ROTD_SCHEDULE_HOUR = 15
    if ROTD_SCHEDULE_MINUTE < 0 or ROTD_SCHEDULE_MINUTE > 59:
        print(f"Warning: ROTD_SCHEDULE_MINUTE '{ROTD_SCHEDULE_MINUTE}' out of range 0-59, using default 0")
        ROTD_SCHEDULE_MINUTE = 0
    
    # Aviation info feature
    AVIATION_INFO_ENABLED = os.getenv('AVIATION_INFO_ENABLED', 'true').lower() == 'true'
    AVIATION_AIRPORT_ID_LOOKUP_ENABLED = os.getenv('AVIATION_AIRPORT_ID_LOOKUP_ENABLED', 'false').lower() == 'true'

    @classmethod
    def get_rotd_pair(cls):
        """Return explicit ROTD origin/dest IDs if provided and valid."""
        try:
            if cls.ROTD_ORIGIN_ID and cls.ROTD_DEST_ID:
                return int(cls.ROTD_ORIGIN_ID), int(cls.ROTD_DEST_ID)
        except ValueError:
            raise ValueError(f"Invalid ROTD_ORIGIN_ID/ROTD_DEST_ID: {cls.ROTD_ORIGIN_ID}/{cls.ROTD_DEST_ID}")
        return None

    # Crash Handler Configuration
    MAX_RESTART_ATTEMPTS = int(os.getenv('MAX_RESTART_ATTEMPTS', '5'))
    RESTART_DELAY_BASE = int(os.getenv('RESTART_DELAY_BASE', '10'))  # seconds
    
    # Parse EMERGENCY_CHANNEL_ID, handling comments and whitespace
    _emergency_channel_raw = os.getenv('EMERGENCY_CHANNEL_ID', '')
    if _emergency_channel_raw:
        # Remove comments and strip whitespace
        _emergency_channel_clean = _emergency_channel_raw.split('#')[0].strip()
        EMERGENCY_CHANNEL_ID = _emergency_channel_clean if _emergency_channel_clean else None
    else:
        EMERGENCY_CHANNEL_ID = None
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        required_vars = ['DISCORD_TOKEN']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    @classmethod
    def get_oil_channel_id(cls):
        """Get the oil price Discord channel ID as an integer"""
        if cls.DISCORD_OIL_CHANNEL:
            try:
                return int(cls.DISCORD_OIL_CHANNEL)
            except ValueError:
                raise ValueError(f"Invalid DISCORD_OIL_CHANNEL: {cls.DISCORD_OIL_CHANNEL}")
        return None

    @classmethod
    def get_rrotd_channel_id(cls):
        """Get the Route of the Day Discord channel ID as an integer"""
        if cls.DISCORD_RROTD_CHANNEL:
            try:
                return int(cls.DISCORD_RROTD_CHANNEL)
            except ValueError:
                raise ValueError(f"Invalid DISCORD_RROTD_CHANNEL: {cls.DISCORD_RROTD_CHANNEL}")
        return None

    # Circuit Breaker Configuration
    CB_FAILURE_THRESHOLD = int(os.getenv('CB_FAILURE_THRESHOLD', '3'))
    CB_OPEN_SECONDS = int(os.getenv('CB_OPEN_SECONDS', '120'))
    CB_HALF_OPEN_PROBES = int(os.getenv('CB_HALF_OPEN_PROBES', '1'))
    
    @classmethod
    def get_emergency_channel_id(cls):
        """Get the emergency Discord channel ID as an integer"""
        if cls.EMERGENCY_CHANNEL_ID:
            try:
                return int(cls.EMERGENCY_CHANNEL_ID)
            except ValueError:
                raise ValueError(f"Invalid EMERGENCY_CHANNEL_ID: {cls.EMERGENCY_CHANNEL_ID}")
        return None
