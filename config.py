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

# TON 12h green-candle signal (ERC-20 -> native arbitrage)
TON_SIGNAL_CHAIN = "ethereum"
TON_SIGNAL_CONTRACT = "0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1"
CANDLE_WINDOW_HOURS = 12
CANDLE_THRESHOLD_PCT = 10.0  # |Δ| over the window that fires a signal (both directions)
# Hysteresis: after a signal fires, re-arm only once |Δ| retreats below this (< threshold),
# so a price oscillating around the 10% boundary does not re-fire every hour.
CANDLE_REARM_PCT = 7.0
# A single on-chain print deviating more than this from the last recorded price is treated
# as a bad tick: not recorded, no signal (prevents one glitch poisoning the 12h baseline).
CANDLE_OUTLIER_PCT = 50.0
# Baseline must be within this many hours of the exact -window target, else skip (no signal).
CANDLE_BASELINE_TOLERANCE_HOURS = 2
# Prune token_price_history rows older than this on each poll.
CANDLE_HISTORY_RETENTION_DAYS = 7

# Scheduler intervals (minutes)
SCAN_INTERVAL = 30
RESCORE_INTERVAL = 60
HISTORY_INTERVAL = 60
TOKEN_POLL_INTERVAL = 15
TOKEN_DISCOVERY_INTERVAL = 2880
CANDLE_CHECK_INTERVAL = 60

VERSION_FILE = str(BASE_DIR / "VERSION")

def get_version() -> str:
    try:
        return Path(VERSION_FILE).read_text().strip()
    except FileNotFoundError:
        return "unknown"
