from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Coin:
    id: int
    tag: str
    name: str
    algorithm: str
    block_time: float = 0.0
    block_reward: float = 0.0
    difficulty: float = 0.0
    difficulty_24h: float = 0.0
    difficulty_7d: float = 0.0
    nethash: float = 0.0
    exchange_rate_btc: float = 0.0
    exchange_rate_usd: float = 0.0
    volume_24h: float = 0.0
    market_cap: str = ""
    profitability: int = 0
    profitability_24h: int = 0
    status: str = "Active"
    first_seen: datetime | None = None
    pool_count: int = 0
    has_explorer: bool = False
    explorer_url: str = ""
    github_url: str = ""
    github_last_commit: datetime | None = None
    coingecko_id: str = ""
    exchange_count: int = 0
    has_premine: bool = False
    has_community: bool = False
    community_urls: list[str] = field(default_factory=list)
    genesis_date: datetime | None = None
    updated_at: datetime | None = None
