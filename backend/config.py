"""Central configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Core keys
ANTHROPIC_API_KEY: str    = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY: str   = os.getenv("OPENROUTER_API_KEY", "")
ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
JWT_SECRET: str           = os.getenv("JWT_SECRET", "change-me-in-production")
DATABASE_PATH: str        = os.getenv("DATABASE_PATH", "capital_lens.db")
JWT_ALGORITHM: str        = "HS256"
JWT_EXPIRY_DAYS: int      = 7

# Data source keys (all optional -- ingestors skip gracefully if empty)
FRED_API_KEY: str         = os.getenv("FRED_API_KEY", "")
FEC_API_KEY: str          = os.getenv("FEC_API_KEY", "")
POLYGON_API_KEY: str      = os.getenv("POLYGON_API_KEY", "")
QUIVER_API_KEY: str       = os.getenv("QUIVER_API_KEY", "")

# Scheduler intervals
EDGAR_INTERVAL_MINUTES: int   = 15
RSS_INTERVAL_MINUTES: int     = 10
MARKET_INTERVAL_MINUTES: int  = 30
FORBES_INTERVAL_HOURS: int    = 6
