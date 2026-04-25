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

DB_PATH = str(BASE_DIR / "data" / "spiritminer.db")

# Scoring thresholds
NEW_COIN_AGE_DAYS = 7
LOW_DIFFICULTY_PERCENTILE = 25
FRESH_COMMIT_DAYS = 14

# Exit signal thresholds
DIFF_SPIKE_MULTIPLIER = 3.0
DIFF_CRITICAL_MULTIPLIER = 5.0
MIN_PROFITABILITY = 50
LOW_VOLUME_USD = 1000

ADMIN_ID = 525931330

# Scheduler intervals (minutes)
SCAN_INTERVAL = 30
RESCORE_INTERVAL = 60
HISTORY_INTERVAL = 60

VERSION_FILE = str(BASE_DIR / "VERSION")

def get_version() -> str:
    try:
        return Path(VERSION_FILE).read_text().strip()
    except FileNotFoundError:
        return "unknown"
