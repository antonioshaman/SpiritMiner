import aiosqlite

import config

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS coins (
    id INTEGER PRIMARY KEY,
    tag TEXT NOT NULL,
    name TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    block_time REAL DEFAULT 0,
    block_reward REAL DEFAULT 0,
    difficulty REAL DEFAULT 0,
    difficulty_24h REAL DEFAULT 0,
    difficulty_7d REAL DEFAULT 0,
    nethash REAL DEFAULT 0,
    exchange_rate_btc REAL DEFAULT 0,
    exchange_rate_usd REAL DEFAULT 0,
    volume_24h REAL DEFAULT 0,
    market_cap TEXT DEFAULT '',
    profitability INTEGER DEFAULT 0,
    profitability_24h INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Active',
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pool_count INTEGER DEFAULT 0,
    has_explorer INTEGER DEFAULT 0,
    explorer_url TEXT DEFAULT '',
    github_url TEXT DEFAULT '',
    github_last_commit TIMESTAMP,
    coingecko_id TEXT DEFAULT '',
    exchange_count INTEGER DEFAULT 0,
    has_premine INTEGER DEFAULT 0,
    has_community INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id INTEGER NOT NULL REFERENCES coins(id),
    total INTEGER NOT NULL,
    age_score INTEGER DEFAULT 0,
    explorer_score INTEGER DEFAULT 0,
    pool_score INTEGER DEFAULT 0,
    github_score INTEGER DEFAULT 0,
    community_score INTEGER DEFAULT 0,
    exchange_score INTEGER DEFAULT 0,
    difficulty_score INTEGER DEFAULT 0,
    tokenomics_score INTEGER DEFAULT 0,
    penalty_premine INTEGER DEFAULT 0,
    penalty_no_explorer INTEGER DEFAULT 0,
    penalty_no_liquidity INTEGER DEFAULT 0,
    penalty_anon_fork INTEGER DEFAULT 0,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS difficulty_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id INTEGER NOT NULL REFERENCES coins(id),
    difficulty REAL NOT NULL,
    nethash REAL DEFAULT 0,
    profitability INTEGER DEFAULT 0,
    exchange_rate_btc REAL DEFAULT 0,
    exchange_rate_usd REAL DEFAULT 0,
    volume_24h REAL DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    alert_new_coins INTEGER DEFAULT 1,
    alert_exit_signals INTEGER DEFAULT 1,
    min_score INTEGER DEFAULT 60,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    coin_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, coin_id)
);

CREATE TABLE IF NOT EXISTS sent_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    coin_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scores_coin ON scores(coin_id, scored_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_coin ON difficulty_history(coin_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_coins_first_seen ON coins(first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_sent_alerts ON sent_alerts(user_id, coin_id, alert_type);
"""


MIGRATIONS = [
    "ALTER TABLE coins ADD COLUMN genesis_date TIMESTAMP",
]


async def _run_migrations(db: aiosqlite.Connection) -> None:
    for sql in MIGRATIONS:
        try:
            await db.execute(sql)
        except Exception:
            pass
    await db.commit()


async def init_db() -> aiosqlite.Connection:
    global _db
    _db = await aiosqlite.connect(config.DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA)
    await _run_migrations(_db)
    await _db.commit()
    return _db


async def get_db() -> aiosqlite.Connection:
    if _db is None:
        return await init_db()
    return _db


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
