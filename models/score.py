from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScoreBreakdown:
    coin_id: int
    total: int = 0
    age_score: int = 0
    explorer_score: int = 0
    pool_score: int = 0
    github_score: int = 0
    community_score: int = 0
    exchange_score: int = 0
    difficulty_score: int = 0
    tokenomics_score: int = 0
    penalty_premine: int = 0
    penalty_no_explorer: int = 0
    penalty_no_liquidity: int = 0
    penalty_anon_fork: int = 0
    scored_at: datetime | None = None

    def compute_total(self) -> int:
        self.total = (
            self.age_score
            + self.explorer_score
            + self.pool_score
            + self.github_score
            + self.community_score
            + self.exchange_score
            + self.difficulty_score
            + self.tokenomics_score
            + self.penalty_premine
            + self.penalty_no_explorer
            + self.penalty_no_liquidity
            + self.penalty_anon_fork
        )
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


@dataclass
class ExitSignal:
    coin_id: int
    signal_type: str
    severity: str  # "warning" | "critical"
    message: str
    detected_at: datetime | None = None

    @property
    def emoji(self) -> str:
        return "⚠️" if self.severity == "warning" else "\U0001f6a8"
