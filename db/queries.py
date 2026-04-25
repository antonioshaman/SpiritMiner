from __future__ import annotations

from datetime import datetime

from models.coin import Coin
from models.score import ScoreBreakdown
from .database import get_db


def _row_to_coin(row) -> Coin:
    return Coin(
        id=row["id"],
        tag=row["tag"],
        name=row["name"],
        algorithm=row["algorithm"],
        block_time=row["block_time"] or 0,
        block_reward=row["block_reward"] or 0,
        difficulty=row["difficulty"] or 0,
        difficulty_24h=row["difficulty_24h"] or 0,
        difficulty_7d=row["difficulty_7d"] or 0,
        nethash=row["nethash"] or 0,
        exchange_rate_btc=row["exchange_rate_btc"] or 0,
        exchange_rate_usd=row["exchange_rate_usd"] or 0,
        volume_24h=row["volume_24h"] or 0,
        market_cap=row["market_cap"] or "",
        profitability=row["profitability"] or 0,
        profitability_24h=row["profitability_24h"] or 0,
        status=row["status"] or "Active",
        first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
        pool_count=row["pool_count"] or 0,
        has_explorer=bool(row["has_explorer"]),
        explorer_url=row["explorer_url"] or "",
        github_url=row["github_url"] or "",
        github_last_commit=(
            datetime.fromisoformat(row["github_last_commit"]) if row["github_last_commit"] else None
        ),
        coingecko_id=row["coingecko_id"] or "",
        exchange_count=row["exchange_count"] or 0,
        has_premine=bool(row["has_premine"]),
        has_community=bool(row["has_community"]),
        updated_at=(
            datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        ),
    )


class CoinQueries:

    @staticmethod
    async def upsert_coin(coin: Coin) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO coins (
                id, tag, name, algorithm, block_time, block_reward,
                difficulty, difficulty_24h, difficulty_7d, nethash,
                exchange_rate_btc, exchange_rate_usd, volume_24h,
                market_cap, profitability, profitability_24h, status,
                pool_count, has_explorer, explorer_url, github_url,
                coingecko_id, exchange_count, has_premine, has_community,
                updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT(id) DO UPDATE SET
                tag=excluded.tag, name=excluded.name, algorithm=excluded.algorithm,
                block_time=excluded.block_time, block_reward=excluded.block_reward,
                difficulty=excluded.difficulty, difficulty_24h=excluded.difficulty_24h,
                difficulty_7d=excluded.difficulty_7d, nethash=excluded.nethash,
                exchange_rate_btc=excluded.exchange_rate_btc,
                exchange_rate_usd=excluded.exchange_rate_usd,
                volume_24h=excluded.volume_24h,
                market_cap=excluded.market_cap,
                profitability=excluded.profitability,
                profitability_24h=excluded.profitability_24h,
                status=excluded.status,
                pool_count=excluded.pool_count,
                has_explorer=excluded.has_explorer,
                explorer_url=excluded.explorer_url,
                github_url=excluded.github_url,
                coingecko_id=excluded.coingecko_id,
                exchange_count=excluded.exchange_count,
                has_premine=excluded.has_premine,
                has_community=excluded.has_community,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                coin.id, coin.tag, coin.name, coin.algorithm,
                coin.block_time, coin.block_reward,
                coin.difficulty, coin.difficulty_24h, coin.difficulty_7d, coin.nethash,
                coin.exchange_rate_btc, coin.exchange_rate_usd, coin.volume_24h,
                coin.market_cap, coin.profitability, coin.profitability_24h, coin.status,
                coin.pool_count, int(coin.has_explorer), coin.explorer_url, coin.github_url,
                coin.coingecko_id, coin.exchange_count, int(coin.has_premine),
                int(coin.has_community),
            ),
        )
        await db.commit()

    @staticmethod
    async def get_coin(coin_id: int) -> Coin | None:
        db = await get_db()
        async with db.execute("SELECT * FROM coins WHERE id = ?", (coin_id,)) as cur:
            row = await cur.fetchone()
            return _row_to_coin(row) if row else None

    @staticmethod
    async def find_coin(query: str) -> list[Coin]:
        db = await get_db()
        q = f"%{query}%"
        async with db.execute(
            "SELECT * FROM coins WHERE tag LIKE ? OR name LIKE ? LIMIT 10",
            (q, q),
        ) as cur:
            return [_row_to_coin(r) for r in await cur.fetchall()]

    @staticmethod
    async def list_new_coins(days: int = 7, limit: int = 20) -> list[Coin]:
        db = await get_db()
        async with db.execute(
            """
            SELECT * FROM coins
            WHERE first_seen >= datetime('now', ? || ' days')
            ORDER BY first_seen DESC
            LIMIT ?
            """,
            (f"-{days}", limit),
        ) as cur:
            return [_row_to_coin(r) for r in await cur.fetchall()]

    @staticmethod
    async def list_all_coins() -> list[Coin]:
        db = await get_db()
        async with db.execute("SELECT * FROM coins ORDER BY name") as cur:
            return [_row_to_coin(r) for r in await cur.fetchall()]

    @staticmethod
    async def save_score(s: ScoreBreakdown) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO scores (
                coin_id, total, age_score, explorer_score, pool_score,
                github_score, community_score, exchange_score,
                difficulty_score, tokenomics_score,
                penalty_premine, penalty_no_explorer,
                penalty_no_liquidity, penalty_anon_fork
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.coin_id, s.total, s.age_score, s.explorer_score, s.pool_score,
                s.github_score, s.community_score, s.exchange_score,
                s.difficulty_score, s.tokenomics_score,
                s.penalty_premine, s.penalty_no_explorer,
                s.penalty_no_liquidity, s.penalty_anon_fork,
            ),
        )
        await db.commit()

    @staticmethod
    async def get_latest_score(coin_id: int) -> ScoreBreakdown | None:
        db = await get_db()
        async with db.execute(
            "SELECT * FROM scores WHERE coin_id = ? ORDER BY scored_at DESC LIMIT 1",
            (coin_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return ScoreBreakdown(
                coin_id=row["coin_id"],
                total=row["total"],
                age_score=row["age_score"],
                explorer_score=row["explorer_score"],
                pool_score=row["pool_score"],
                github_score=row["github_score"],
                community_score=row["community_score"],
                exchange_score=row["exchange_score"],
                difficulty_score=row["difficulty_score"],
                tokenomics_score=row["tokenomics_score"],
                penalty_premine=row["penalty_premine"],
                penalty_no_explorer=row["penalty_no_explorer"],
                penalty_no_liquidity=row["penalty_no_liquidity"],
                penalty_anon_fork=row["penalty_anon_fork"],
                scored_at=(
                    datetime.fromisoformat(row["scored_at"]) if row["scored_at"] else None
                ),
            )

    @staticmethod
    async def top_scored(limit: int = 20) -> list[tuple[Coin, ScoreBreakdown]]:
        db = await get_db()
        async with db.execute(
            """
            SELECT c.*, s.total as s_total, s.age_score, s.explorer_score,
                   s.pool_score, s.github_score, s.community_score,
                   s.exchange_score, s.difficulty_score, s.tokenomics_score,
                   s.penalty_premine, s.penalty_no_explorer,
                   s.penalty_no_liquidity, s.penalty_anon_fork, s.scored_at
            FROM coins c
            JOIN scores s ON s.coin_id = c.id
            WHERE s.id = (
                SELECT id FROM scores WHERE coin_id = c.id ORDER BY scored_at DESC LIMIT 1
            )
            ORDER BY s.total DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            results = []
            for row in await cur.fetchall():
                coin = _row_to_coin(row)
                score = ScoreBreakdown(
                    coin_id=row["id"],
                    total=row["s_total"],
                    age_score=row["age_score"],
                    explorer_score=row["explorer_score"],
                    pool_score=row["pool_score"],
                    github_score=row["github_score"],
                    community_score=row["community_score"],
                    exchange_score=row["exchange_score"],
                    difficulty_score=row["difficulty_score"],
                    tokenomics_score=row["tokenomics_score"],
                    penalty_premine=row["penalty_premine"],
                    penalty_no_explorer=row["penalty_no_explorer"],
                    penalty_no_liquidity=row["penalty_no_liquidity"],
                    penalty_anon_fork=row["penalty_anon_fork"],
                    scored_at=(
                        datetime.fromisoformat(row["scored_at"]) if row["scored_at"] else None
                    ),
                )
                results.append((coin, score))
            return results

    @staticmethod
    async def record_difficulty(coin: Coin) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO difficulty_history (
                coin_id, difficulty, nethash, profitability,
                exchange_rate_btc, exchange_rate_usd, volume_24h
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                coin.id, coin.difficulty, coin.nethash, coin.profitability,
                coin.exchange_rate_btc, coin.exchange_rate_usd, coin.volume_24h,
            ),
        )
        await db.commit()

    @staticmethod
    async def get_difficulty_history(
        coin_id: int, limit: int = 72
    ) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """
            SELECT * FROM difficulty_history
            WHERE coin_id = ?
            ORDER BY recorded_at DESC
            LIMIT ?
            """,
            (coin_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
