from __future__ import annotations

from datetime import datetime

from models.coin import Coin
from models.score import ScoreBreakdown
from models.token import Token, TokenScoreBreakdown
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
        genesis_date=(
            datetime.fromisoformat(row["genesis_date"]) if row["genesis_date"] else None
        ),
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
                genesis_date, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, CURRENT_TIMESTAMP
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
                genesis_date=COALESCE(excluded.genesis_date, coins.genesis_date),
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
                coin.genesis_date.isoformat() if coin.genesis_date else None,
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


class SubscriberQueries:

    @staticmethod
    async def subscribe(user_id: int, username: str = "") -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO subscribers (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
            """,
            (user_id, username),
        )
        await db.commit()

    @staticmethod
    async def unsubscribe(user_id: int) -> None:
        db = await get_db()
        await db.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
        await db.commit()

    @staticmethod
    async def is_subscribed(user_id: int) -> bool:
        db = await get_db()
        async with db.execute(
            "SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None

    @staticmethod
    async def get_all_subscribers() -> list[dict]:
        db = await get_db()
        async with db.execute("SELECT * FROM subscribers") as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def was_alert_sent(user_id: int, coin_id: int, alert_type: str) -> bool:
        db = await get_db()
        async with db.execute(
            """
            SELECT 1 FROM sent_alerts
            WHERE user_id = ? AND coin_id = ? AND alert_type = ?
            AND sent_at > datetime('now', '-24 hours')
            """,
            (user_id, coin_id, alert_type),
        ) as cur:
            return await cur.fetchone() is not None

    @staticmethod
    async def mark_alert_sent(user_id: int, coin_id: int, alert_type: str) -> None:
        db = await get_db()
        await db.execute(
            "INSERT INTO sent_alerts (user_id, coin_id, alert_type) VALUES (?, ?, ?)",
            (user_id, coin_id, alert_type),
        )
        await db.commit()


class WatchlistQueries:

    @staticmethod
    async def add(user_id: int, coin_id: int) -> None:
        db = await get_db()
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, coin_id) VALUES (?, ?)",
            (user_id, coin_id),
        )
        await db.commit()

    @staticmethod
    async def remove(user_id: int, coin_id: int) -> None:
        db = await get_db()
        await db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND coin_id = ?",
            (user_id, coin_id),
        )
        await db.commit()

    @staticmethod
    async def get_user_watchlist(user_id: int) -> list[int]:
        db = await get_db()
        async with db.execute(
            "SELECT coin_id FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ) as cur:
            return [r["coin_id"] for r in await cur.fetchall()]

    @staticmethod
    async def get_watchers(coin_id: int) -> list[int]:
        db = await get_db()
        async with db.execute(
            "SELECT user_id FROM watchlist WHERE coin_id = ?",
            (coin_id,),
        ) as cur:
            return [r["user_id"] for r in await cur.fetchall()]


class VoteQueries:

    @staticmethod
    async def vote(user_id: int, coin_id: int, vote: str) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO votes (user_id, coin_id, vote)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, coin_id) DO UPDATE SET vote=excluded.vote, voted_at=CURRENT_TIMESTAMP
            """,
            (user_id, coin_id, vote),
        )
        await db.commit()

    @staticmethod
    async def get_sentiment(coin_id: int) -> dict:
        db = await get_db()
        result = {"bullish": 0, "watching": 0, "bearish": 0, "total": 0}
        async with db.execute(
            "SELECT vote, COUNT(*) as cnt FROM votes WHERE coin_id = ? GROUP BY vote",
            (coin_id,),
        ) as cur:
            for row in await cur.fetchall():
                result[row["vote"]] = row["cnt"]
                result["total"] += row["cnt"]
        return result

    @staticmethod
    async def get_user_vote(user_id: int, coin_id: int) -> str | None:
        db = await get_db()
        async with db.execute(
            "SELECT vote FROM votes WHERE user_id = ? AND coin_id = ?",
            (user_id, coin_id),
        ) as cur:
            row = await cur.fetchone()
            return row["vote"] if row else None


class ActionQueries:

    @staticmethod
    async def record_action(user_id: int, coin_id: int, action: str, price: float = 0) -> None:
        db = await get_db()
        await db.execute(
            "INSERT INTO user_actions (user_id, coin_id, action, price_at_action) VALUES (?, ?, ?, ?)",
            (user_id, coin_id, action, price),
        )
        await db.commit()

    @staticmethod
    async def get_user_actions(user_id: int, limit: int = 50) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """
            SELECT ua.*, c.tag, c.name, c.exchange_rate_usd
            FROM user_actions ua
            JOIN coins c ON c.id = ua.coin_id
            WHERE ua.user_id = ?
            ORDER BY ua.created_at DESC LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def get_entry_exit_pairs(user_id: int) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """
            SELECT ua.coin_id, c.tag, c.name, c.exchange_rate_usd as current_price,
                   e.price_at_action as entry_price, e.created_at as entry_time,
                   x.price_at_action as exit_price, x.created_at as exit_time
            FROM user_actions e
            JOIN coins c ON c.id = e.coin_id
            LEFT JOIN user_actions x ON x.user_id = e.user_id AND x.coin_id = e.coin_id AND x.action = 'exit'
                AND x.created_at > e.created_at
            JOIN (SELECT coin_id, MAX(created_at) as max_entry FROM user_actions WHERE user_id = ? AND action = 'enter' GROUP BY coin_id) ua
                ON ua.coin_id = e.coin_id AND ua.max_entry = e.created_at
            WHERE e.user_id = ? AND e.action = 'enter'
            ORDER BY e.created_at DESC
            """,
            (user_id, user_id),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def get_leaderboard(limit: int = 20) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """
            SELECT e.user_id,
                   COUNT(DISTINCT e.coin_id) as trades,
                   s.username
            FROM user_actions e
            LEFT JOIN subscribers s ON s.user_id = e.user_id
            WHERE e.action = 'enter'
            GROUP BY e.user_id
            ORDER BY trades DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


class PointsQueries:

    LEVELS = [
        (0, "Новичок"),
        (50, "Разведчик"),
        (200, "Охотник"),
        (500, "Мастер"),
        (1000, "Легенда"),
    ]

    @staticmethod
    async def award(user_id: int, amount: int) -> int:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO spirit_points (user_id, points, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                points = spirit_points.points + excluded.points,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, amount),
        )
        await db.commit()
        async with db.execute(
            "SELECT points FROM spirit_points WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row["points"] if row else 0

    @staticmethod
    async def get_points(user_id: int) -> int:
        db = await get_db()
        async with db.execute(
            "SELECT points FROM spirit_points WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row["points"] if row else 0

    @staticmethod
    def get_level(points: int) -> str:
        level = "Новичок"
        for threshold, name in PointsQueries.LEVELS:
            if points >= threshold:
                level = name
        return level

    @staticmethod
    def get_next_level(points: int) -> tuple[str, int] | None:
        for threshold, name in PointsQueries.LEVELS:
            if points < threshold:
                return name, threshold - points
        return None

    @staticmethod
    async def get_top(limit: int = 20) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """
            SELECT sp.user_id, sp.points, s.username
            FROM spirit_points sp
            LEFT JOIN subscribers s ON s.user_id = sp.user_id
            ORDER BY sp.points DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


def _row_to_token(row) -> Token:
    return Token(
        chain=row["chain"],
        address=row["address"],
        symbol=row["symbol"] or "",
        name=row["name"] or "",
        price_usd=row["price_usd"] or 0,
        fdv=row["fdv"] or 0,
        market_cap=row["market_cap"] or 0,
        liquidity_usd=row["liquidity_usd"] or 0,
        volume_24h=row["volume_24h"] or 0,
        price_change_1h=row["price_change_1h"] or 0,
        price_change_24h=row["price_change_24h"] or 0,
        pair_address=row["pair_address"] or "",
        dex=row["dex"] or "",
        pair_created_at=(
            datetime.fromisoformat(row["pair_created_at"]) if row["pair_created_at"] else None
        ),
        holder_count=row["holder_count"] or 0,
        top10_concentration=row["top10_concentration"] or 0,
        lp_locked_pct=row["lp_locked_pct"] or 0,
        is_verified=bool(row["is_verified"]),
        is_honeypot=bool(row["is_honeypot"]),
        is_mintable=bool(row["is_mintable"]),
        is_proxy=bool(row["is_proxy"]),
        can_take_back_ownership=bool(row["can_take_back_ownership"]),
        hidden_owner=bool(row["hidden_owner"]),
        audit_coverage=row["audit_coverage"] or "full",
        risk_flags=(row["risk_flags"] or "").split(",") if row["risk_flags"] else [],
        first_seen=datetime.fromisoformat(row["first_seen"]) if row["first_seen"] else None,
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
    )


class TokenQueries:

    @staticmethod
    async def upsert_token(t: Token) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO tokens (
                chain, address, symbol, name, price_usd, fdv, market_cap,
                liquidity_usd, volume_24h, price_change_1h, price_change_24h,
                pair_address, dex, pair_created_at, holder_count,
                top10_concentration, lp_locked_pct, is_verified, is_honeypot,
                is_mintable, is_proxy, can_take_back_ownership, hidden_owner,
                audit_coverage, risk_flags, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chain, address) DO UPDATE SET
                symbol=excluded.symbol, name=excluded.name,
                price_usd=excluded.price_usd, fdv=excluded.fdv,
                market_cap=excluded.market_cap, liquidity_usd=excluded.liquidity_usd,
                volume_24h=excluded.volume_24h,
                price_change_1h=excluded.price_change_1h,
                price_change_24h=excluded.price_change_24h,
                pair_address=excluded.pair_address, dex=excluded.dex,
                pair_created_at=COALESCE(excluded.pair_created_at, tokens.pair_created_at),
                holder_count=excluded.holder_count,
                top10_concentration=excluded.top10_concentration,
                lp_locked_pct=excluded.lp_locked_pct,
                is_verified=excluded.is_verified,
                is_honeypot=excluded.is_honeypot,
                is_mintable=excluded.is_mintable,
                is_proxy=excluded.is_proxy,
                can_take_back_ownership=excluded.can_take_back_ownership,
                hidden_owner=excluded.hidden_owner,
                audit_coverage=excluded.audit_coverage,
                risk_flags=excluded.risk_flags,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                t.chain, t.address, t.symbol, t.name,
                t.price_usd, t.fdv, t.market_cap,
                t.liquidity_usd, t.volume_24h,
                t.price_change_1h, t.price_change_24h,
                t.pair_address, t.dex,
                t.pair_created_at.isoformat() if t.pair_created_at else None,
                t.holder_count, t.top10_concentration, t.lp_locked_pct,
                int(t.is_verified), int(t.is_honeypot), int(t.is_mintable),
                int(t.is_proxy), int(t.can_take_back_ownership), int(t.hidden_owner),
                t.audit_coverage, ",".join(t.risk_flags),
            ),
        )
        await db.commit()

    @staticmethod
    async def get_token(chain: str, address: str) -> Token | None:
        db = await get_db()
        async with db.execute(
            "SELECT * FROM tokens WHERE chain = ? AND address = ?",
            (chain, address.lower() if chain != "ton" else address),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_token(row) if row else None

    @staticmethod
    async def list_all_tokens() -> list[Token]:
        db = await get_db()
        async with db.execute("SELECT * FROM tokens ORDER BY updated_at DESC") as cur:
            return [_row_to_token(r) for r in await cur.fetchall()]

    @staticmethod
    async def save_score(s: TokenScoreBreakdown) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO token_scores (
                chain, address, total, liquidity_score, age_score, holders_score,
                security_score, volume_score, penalty_honeypot, penalty_unverified,
                penalty_concentration, penalty_lp_unlocked, penalty_mintable,
                penalty_proxy, penalty_owner_risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.chain, s.address, s.total, s.liquidity_score, s.age_score,
                s.holders_score, s.security_score, s.volume_score,
                s.penalty_honeypot, s.penalty_unverified, s.penalty_concentration,
                s.penalty_lp_unlocked, s.penalty_mintable, s.penalty_proxy,
                s.penalty_owner_risk,
            ),
        )
        await db.commit()

    @staticmethod
    async def get_latest_score(chain: str, address: str) -> TokenScoreBreakdown | None:
        db = await get_db()
        async with db.execute(
            """SELECT * FROM token_scores WHERE chain = ? AND address = ?
               ORDER BY scored_at DESC LIMIT 1""",
            (chain, address),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return TokenScoreBreakdown(
                chain=row["chain"],
                address=row["address"],
                total=row["total"],
                liquidity_score=row["liquidity_score"],
                age_score=row["age_score"],
                holders_score=row["holders_score"],
                security_score=row["security_score"],
                volume_score=row["volume_score"],
                penalty_honeypot=row["penalty_honeypot"],
                penalty_unverified=row["penalty_unverified"],
                penalty_concentration=row["penalty_concentration"],
                penalty_lp_unlocked=row["penalty_lp_unlocked"],
                penalty_mintable=row["penalty_mintable"],
                penalty_proxy=row["penalty_proxy"],
                penalty_owner_risk=row["penalty_owner_risk"],
                scored_at=(
                    datetime.fromisoformat(row["scored_at"]) if row["scored_at"] else None
                ),
            )

    @staticmethod
    async def record_price(chain: str, address: str, price_usd: float, liquidity_usd: float) -> None:
        db = await get_db()
        await db.execute(
            """INSERT INTO token_price_history (chain, address, price_usd, liquidity_usd)
               VALUES (?, ?, ?, ?)""",
            (chain, address, price_usd, liquidity_usd),
        )
        await db.commit()

    @staticmethod
    async def get_price_history(chain: str, address: str, hours: int = 24) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """SELECT * FROM token_price_history
               WHERE chain = ? AND address = ?
                 AND recorded_at >= datetime('now', ? || ' hours')
               ORDER BY recorded_at ASC""",
            (chain, address, f"-{hours}"),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def prune_price_history(chain: str, address: str, days: int) -> None:
        """Delete price-history rows older than `days` for a contract."""
        db = await get_db()
        await db.execute(
            """DELETE FROM token_price_history
               WHERE chain = ? AND address = ?
                 AND recorded_at < datetime('now', ? || ' days')""",
            (chain, address, f"-{days}"),
        )
        await db.commit()


class TokenWatchlistQueries:

    @staticmethod
    async def add(user_id: int, chain: str, address: str, entry_price: float = 0) -> None:
        db = await get_db()
        await db.execute(
            """INSERT OR IGNORE INTO token_watchlist (user_id, chain, address, entry_price_usd)
               VALUES (?, ?, ?, ?)""",
            (user_id, chain, address, entry_price),
        )
        await db.commit()

    @staticmethod
    async def remove(user_id: int, chain: str, address: str) -> None:
        db = await get_db()
        await db.execute(
            "DELETE FROM token_watchlist WHERE user_id = ? AND chain = ? AND address = ?",
            (user_id, chain, address),
        )
        await db.commit()

    @staticmethod
    async def is_watching(user_id: int, chain: str, address: str) -> bool:
        db = await get_db()
        async with db.execute(
            "SELECT 1 FROM token_watchlist WHERE user_id = ? AND chain = ? AND address = ?",
            (user_id, chain, address),
        ) as cur:
            return await cur.fetchone() is not None

    @staticmethod
    async def get_user_tokens(user_id: int) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """SELECT chain, address, entry_price_usd, added_at FROM token_watchlist
               WHERE user_id = ? ORDER BY added_at DESC""",
            (user_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def all_watched() -> list[dict]:
        db = await get_db()
        async with db.execute(
            "SELECT DISTINCT chain, address FROM token_watchlist"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def get_watchers(chain: str, address: str) -> list[dict]:
        db = await get_db()
        async with db.execute(
            """SELECT user_id, entry_price_usd FROM token_watchlist
               WHERE chain = ? AND address = ?""",
            (chain, address),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    @staticmethod
    async def was_alert_sent(user_id: int, chain: str, address: str, alert_type: str) -> bool:
        db = await get_db()
        async with db.execute(
            """SELECT 1 FROM token_sent_alerts
               WHERE user_id = ? AND chain = ? AND address = ? AND alert_type = ?
                 AND sent_at > datetime('now', '-6 hours')""",
            (user_id, chain, address, alert_type),
        ) as cur:
            return await cur.fetchone() is not None

    @staticmethod
    async def mark_alert_sent(user_id: int, chain: str, address: str, alert_type: str) -> None:
        db = await get_db()
        await db.execute(
            """INSERT INTO token_sent_alerts (user_id, chain, address, alert_type)
               VALUES (?, ?, ?, ?)""",
            (user_id, chain, address, alert_type),
        )
        await db.commit()

    @staticmethod
    async def clear_alerts(chain: str, address: str, alert_type: str) -> None:
        """Drop dedup markers for a signal so the next threshold crossing re-fires."""
        db = await get_db()
        await db.execute(
            "DELETE FROM token_sent_alerts WHERE chain = ? AND address = ? AND alert_type = ?",
            (chain, address, alert_type),
        )
        await db.commit()


class PoolDetailQueries:

    @staticmethod
    async def upsert_pools(coin_id: int, pools: list[dict]) -> None:
        db = await get_db()
        for p in pools:
            await db.execute(
                """
                INSERT INTO pool_details (coin_id, pool_name, pool_url, hashrate, workers, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(coin_id, pool_name) DO UPDATE SET
                    pool_url=excluded.pool_url, hashrate=excluded.hashrate,
                    workers=excluded.workers, updated_at=CURRENT_TIMESTAMP
                """,
                (coin_id, p["name"], p.get("url", ""), p.get("hashrate", 0), p.get("workers", 0)),
            )
        await db.commit()

    @staticmethod
    async def get_pools(coin_id: int) -> list[dict]:
        db = await get_db()
        async with db.execute(
            "SELECT * FROM pool_details WHERE coin_id = ? ORDER BY hashrate DESC",
            (coin_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
