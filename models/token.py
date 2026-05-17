from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


SUPPORTED_CHAINS = {
    "ethereum": {"gt_slug": "eth", "goplus": "1", "family": "evm", "explorer": "https://etherscan.io/token/{addr}"},
    "bsc": {"gt_slug": "bsc", "goplus": "56", "family": "evm", "explorer": "https://bscscan.com/token/{addr}"},
    "base": {"gt_slug": "base", "goplus": "8453", "family": "evm", "explorer": "https://basescan.org/token/{addr}"},
    "arbitrum": {"gt_slug": "arbitrum", "goplus": "42161", "family": "evm", "explorer": "https://arbiscan.io/token/{addr}"},
    "polygon": {"gt_slug": "polygon_pos", "goplus": "137", "family": "evm", "explorer": "https://polygonscan.com/token/{addr}"},
    "optimism": {"gt_slug": "optimism", "goplus": "10", "family": "evm", "explorer": "https://optimistic.etherscan.io/token/{addr}"},
    "avalanche": {"gt_slug": "avax", "goplus": "43114", "family": "evm", "explorer": "https://snowtrace.io/token/{addr}"},
    "solana": {"gt_slug": "solana", "goplus": "solana", "family": "solana", "explorer": "https://solscan.io/token/{addr}"},
    "ton": {"gt_slug": "ton", "goplus": None, "family": "ton", "explorer": "https://tonviewer.com/{addr}"},
}


def chain_explorer_url(chain: str, address: str) -> str:
    cfg = SUPPORTED_CHAINS.get(chain)
    if not cfg:
        return ""
    return cfg["explorer"].format(addr=address)


@dataclass
class Token:
    chain: str
    address: str
    symbol: str = ""
    name: str = ""
    price_usd: float = 0.0
    fdv: float = 0.0
    market_cap: float = 0.0
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    pair_address: str = ""
    dex: str = ""
    pair_created_at: datetime | None = None
    holder_count: int = 0
    top10_concentration: float = 0.0
    lp_locked_pct: float = 0.0
    is_verified: bool = False
    is_honeypot: bool = False
    is_mintable: bool = False
    is_proxy: bool = False
    can_take_back_ownership: bool = False
    hidden_owner: bool = False
    audit_coverage: str = "full"  # "full" | "limited" | "none"
    risk_flags: list[str] = field(default_factory=list)
    first_seen: datetime | None = None
    updated_at: datetime | None = None

    @property
    def age_days(self) -> int:
        if not self.pair_created_at:
            return 0
        return max(0, (datetime.utcnow() - self.pair_created_at).days)


@dataclass
class TokenScoreBreakdown:
    chain: str
    address: str
    total: int = 0
    liquidity_score: int = 0
    age_score: int = 0
    holders_score: int = 0
    security_score: int = 0
    volume_score: int = 0
    penalty_honeypot: int = 0
    penalty_unverified: int = 0
    penalty_concentration: int = 0
    penalty_lp_unlocked: int = 0
    penalty_mintable: int = 0
    penalty_proxy: int = 0
    penalty_owner_risk: int = 0
    scored_at: datetime | None = None

    def compute_total(self) -> int:
        self.total = max(0, min(100, (
            self.liquidity_score
            + self.age_score
            + self.holders_score
            + self.security_score
            + self.volume_score
            + self.penalty_honeypot
            + self.penalty_unverified
            + self.penalty_concentration
            + self.penalty_lp_unlocked
            + self.penalty_mintable
            + self.penalty_proxy
            + self.penalty_owner_risk
        )))
        return self.total

    @property
    def signal(self) -> str:
        if self.total >= 60:
            return "green"
        if self.total >= 35:
            return "yellow"
        return "red"

    @property
    def signal_emoji(self) -> str:
        return {"green": "\U0001f7e2", "yellow": "\U0001f7e1", "red": "\U0001f534"}[self.signal]

    @property
    def signal_text(self) -> str:
        return {
            "green": "Можно пробовать",
            "yellow": "Только тестовым объёмом",
            "red": "Не лезть",
        }[self.signal]
