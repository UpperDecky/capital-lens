"""Central configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Core keys
ANTHROPIC_API_KEY: str     = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY: str    = os.getenv("OPENROUTER_API_KEY", "")
ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
JWT_SECRET: str            = os.getenv("JWT_SECRET", "change-me-in-production")
DATABASE_PATH: str         = os.getenv("DATABASE_PATH", "capital_lens.db")
JWT_ALGORITHM: str         = "HS256"
JWT_EXPIRY_DAYS: int       = 7

# Data source keys (all optional -- ingestors skip gracefully if empty)
FRED_API_KEY: str          = os.getenv("FRED_API_KEY", "")
FEC_API_KEY: str           = os.getenv("FEC_API_KEY", "")
POLYGON_API_KEY: str       = os.getenv("POLYGON_API_KEY", "")
QUIVER_API_KEY: str        = os.getenv("QUIVER_API_KEY", "")

# Market data -- Twelve Data (50+ exchanges, free 800 credits/day)
# Register at https://twelvedata.com/register
TWELVE_DATA_API_KEY: str   = os.getenv("TWELVE_DATA_API_KEY", "")

# Crypto -- CoinGecko (18,000+ coins; demo key = 30 calls/min)
# Register at https://www.coingecko.com/en/api/pricing
COINGECKO_API_KEY: str     = os.getenv("COINGECKO_API_KEY", "")

# ADS-B -- OpenSky Network (optional login increases rate limit)
# Register at https://opensky-network.org
OPENSKY_USERNAME: str      = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD: str      = os.getenv("OPENSKY_PASSWORD", "")

# Maritime AIS -- aisstream.io (free WebSocket)
# Register at https://aisstream.io
AISSTREAM_API_KEY: str     = os.getenv("AISSTREAM_API_KEY", "")

# Geopolitical conflicts -- ACLED (free, register at acleddata.com/register)
ACLED_EMAIL: str           = os.getenv("ACLED_EMAIL", "")
ACLED_KEY: str             = os.getenv("ACLED_KEY", "")

# Geopolitical conflicts -- UCDP (free token, email ucdp@pcr.uu.se)
UCDP_TOKEN: str            = os.getenv("UCDP_TOKEN", "")

# Satellite fire detection -- NASA FIRMS (free MAP_KEY)
# Register at https://firms.modaps.eosdis.nasa.gov/api
NASA_FIRMS_MAP_KEY: str    = os.getenv("NASA_FIRMS_MAP_KEY", "")

# Infrastructure monitoring -- Cloudflare Radar (free API token)
# Token at https://dash.cloudflare.com -> My Profile -> API Tokens
CLOUDFLARE_API_TOKEN: str  = os.getenv("CLOUDFLARE_API_TOKEN", "")

# Telegram OSINT (register app at https://my.telegram.org/apps)
TELEGRAM_API_ID: str       = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH: str     = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION: str      = os.getenv("TELEGRAM_SESSION", "")  # base64 StringSession

# Cash flow -- Blockchair (free 1440 req/day, key unlocks higher limits)
# Register at https://blockchair.com/api
BLOCKCHAIR_API_KEY: str    = os.getenv("BLOCKCHAIR_API_KEY", "")

# Cash flow -- Etherscan (free 100k calls/day for ETH whale lookup)
# Register at https://etherscan.io/apis
ETHERSCAN_API_KEY: str     = os.getenv("ETHERSCAN_API_KEY", "")

# Security / compliance
ENCRYPTION_KEY: str        = os.getenv("ENCRYPTION_KEY", "")
ENCRYPT_PII: bool          = os.getenv("ENCRYPT_PII", "false").lower() == "true"
HTTPS_REDIRECT: bool       = os.getenv("HTTPS_REDIRECT", "false").lower() == "true"
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]

# Scheduler intervals
EDGAR_INTERVAL_MINUTES: int   = 15
RSS_INTERVAL_MINUTES: int     = 10
MARKET_INTERVAL_MINUTES: int  = 30
FORBES_INTERVAL_HOURS: int    = 6
