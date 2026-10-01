import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

BOT_TOKEN = os.getenv("SPIRITMINER_BOT_TOKEN", "")
WTM_API_KEY = os.getenv("WTM_API_KEY", "")
WTM_BASE = "https://whattomine.com"
WTM_API_BASE = "https://whattomine.com/api/v1"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
GITHUB_API_BASE = "https://api.github.com"
MININGPOOLSTATS_BASE = "https://miningpoolstats.stream"
COINPAPRIKA_BASE = "https://api.coinpaprika.com/v1"

DB_PATH = str(BASE_DIR / "data" / "spiritminer.db")

# Scoring thresholds
NEW_COIN_AGE_DAYS = 7
MAX_ALERT_AGE_DAYS = 90
SUSPICIOUS_EXCHANGES_FOR_NEW_COIN = 5
LOW_DIFFICULTY_PERCENTILE = 25
FRESH_COMMIT_DAYS = 14

# Exit signal thresholds
DIFF_SPIKE_MULTIPLIER = 3.0
DIFF_CRITICAL_MULTIPLIER = 5.0
MIN_PROFITABILITY = 50
LOW_VOLUME_USD = 1000

ADMIN_ID = 525931330

# Read-only full-cycle arbitrage; missing providers block profit signals.
ARB_ETH_RPC_URL = os.getenv("ARB_ETH_RPC_URL", "")
ARB_BRIDGE_QUOTE_URL = os.getenv("ARB_BRIDGE_QUOTE_URL", "")
ARB_SETTLEMENT_QUOTE_URL = os.getenv("ARB_SETTLEMENT_QUOTE_URL", "")
ARB_NATIVE_QUOTE_URL = os.getenv("ARB_NATIVE_QUOTE_URL", "")
ARB_TRADE_SIZES = tuple(x.strip() for x in os.getenv("ARB_TRADE_SIZES", "100,500,1000").split(",") if x.strip())
ARB_MIN_NET_PCT = os.getenv("ARB_MIN_NET_PCT", "3")
ARB_SAFETY_BPS = os.getenv("ARB_SAFETY_BPS", "100")
ARB_MAX_QUOTE_AGE_SECONDS = int(os.getenv("ARB_MAX_QUOTE_AGE_SECONDS", "60"))
ARB_POLL_SECONDS = int(os.getenv("ARB_POLL_SECONDS", "60"))

# Scheduler intervals (minutes)
SCAN_INTERVAL = 30
RESCORE_INTERVAL = 60
HISTORY_INTERVAL = 60
TOKEN_POLL_INTERVAL = 15
TOKEN_DISCOVERY_INTERVAL = 2880

VERSION_FILE = str(BASE_DIR / "VERSION")

def get_version() -> str:
    try:
        return Path(VERSION_FILE).read_text().strip()
    except FileNotFoundError:
        return "unknown"
