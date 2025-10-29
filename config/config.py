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
    BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
    BOT_STATUS = os.getenv('BOT_STATUS', 'Monitoring Oil Prices')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
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
