from __future__ import annotations

from datetime import datetime

from db.queries import CoinQueries, VoteQueries, ActionQueries
from db.database import get_db


async def compute_spirit_index() -> dict:
    db = await get_db()

    coins = await CoinQueries.list_all_coins()
    total_coins = len(coins)

    new_7d = sum(1 for c in coins if c.first_seen and (datetime.utcnow() - c.first_seen).days <= 7)
    new_30d = sum(1 for c in coins if c.first_seen and (datetime.utcnow() - c.first_seen).days <= 30)

    scored = await CoinQueries.top_scored(limit=total_coins)
    avg_score = 0
    green_count = 0
    if scored:
        avg_score = sum(s.total for _, s in scored) / len(scored)
        green_count = sum(1 for _, s in scored if s.total >= 60)

    async with db.execute("SELECT COUNT(*) as cnt FROM votes") as cur:
        row = await cur.fetchone()
        total_votes = row["cnt"] if row else 0

    async with db.execute(
        "SELECT vote, COUNT(*) as cnt FROM votes GROUP BY vote"
    ) as cur:
        vote_dist = {}
        for r in await cur.fetchall():
            vote_dist[r["vote"]] = r["cnt"]

    bullish_pct = 0
    if total_votes > 0:
        bullish_pct = vote_dist.get("bullish", 0) * 100 // total_votes

    async with db.execute(
        "SELECT COUNT(DISTINCT user_id) as cnt FROM user_actions"
    ) as cur:
        row = await cur.fetchone()
        active_traders = row["cnt"] if row else 0

    async with db.execute(
        "SELECT COUNT(*) as cnt FROM user_actions WHERE action = 'enter'"
    ) as cur:
        row = await cur.fetchone()
        total_entries = row["cnt"] if row else 0

    async with db.execute("SELECT COUNT(*) as cnt FROM subscribers") as cur:
        row = await cur.fetchone()
        total_subs = row["cnt"] if row else 0

    # Spirit Index formula (0-100):
    # 25% market quality (avg score)
    # 25% sentiment (bullish %)
    # 25% activity (traders + votes)
    # 25% discovery (new coins velocity)
    market_quality = min(avg_score, 100)
    sentiment_score = bullish_pct
    activity = min((active_traders * 10 + total_votes * 2), 100)
    discovery = min(new_7d * 15 + new_30d * 3, 100)

    index = int((market_quality + sentiment_score + activity + discovery) / 4)

    if index >= 70:
        mood = "\U0001f525 HOT"
        mood_desc = "Рынок горячий — много возможностей"
    elif index >= 50:
        mood = "\U0001f7e2 WARM"
        mood_desc = "Есть интересные монеты"
    elif index >= 30:
        mood = "\U0001f7e1 NEUTRAL"
        mood_desc = "Спокойный рынок, ждём сигналы"
    else:
        mood = "\U0001f535 COLD"
        mood_desc = "Мало возможностей, копим ресурсы"

    return {
        "index": index,
        "mood": mood,
        "mood_desc": mood_desc,
        "total_coins": total_coins,
        "new_7d": new_7d,
        "new_30d": new_30d,
        "avg_score": avg_score,
        "green_count": green_count,
        "total_votes": total_votes,
        "bullish_pct": bullish_pct,
        "active_traders": active_traders,
        "total_entries": total_entries,
        "total_subs": total_subs,
        "components": {
            "market_quality": int(market_quality),
            "sentiment": int(sentiment_score),
            "activity": int(activity),
            "discovery": int(discovery),
        },
    }
