from __future__ import annotations

import logging
from datetime import datetime

import aiohttp
from aiogram import Bot

import config
from db.queries import TokenQueries, SubscriberQueries
from models.token import Token, SUPPORTED_CHAINS
from services import geckoterminal
from services.token_scorer import enrich_token, compute_score
from utils.formatting import format_token_card

log = logging.getLogger(__name__)

SCAN_CHAINS = ["ethereum", "bsc", "base", "arbitrum", "solana", "ton"]

MIN_LIQUIDITY = 50_000
MIN_SCORE = 60
MAX_AGE_DAYS = 7


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def _f(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _token_from_pool(pool: dict, chain: str) -> Token | None:
    attrs = pool.get("attributes") or {}
    rels = pool.get("relationships") or {}
    base = ((rels.get("base_token") or {}).get("data") or {}).get("id", "")
    if not base or "_" not in base:
        return None
    address = base.split("_", 1)[1]
    if SUPPORTED_CHAINS[chain]["family"] == "evm":
        address = address.lower()

    name = attrs.get("name") or ""
    symbol = ""
    if "/" in name:
        symbol = name.split("/")[0].strip()

    price_changes = attrs.get("price_change_percentage") or {}

    return Token(
        chain=chain,
        address=address,
        symbol=symbol,
        name=name,
        price_usd=_f(attrs.get("base_token_price_usd")),
        liquidity_usd=_f(attrs.get("reserve_in_usd")),
        volume_24h=_f((attrs.get("volume_usd") or {}).get("h24")),
        fdv=_f(attrs.get("fdv_usd")),
        market_cap=_f(attrs.get("market_cap_usd")),
        price_change_1h=_f(price_changes.get("h1")),
        price_change_24h=_f(price_changes.get("h24")),
        pair_address=attrs.get("address", ""),
        dex=((rels.get("dex") or {}).get("data") or {}).get("id", ""),
        pair_created_at=_parse_iso(attrs.get("pool_created_at")),
    )


async def scan_new_tokens(bot: Bot) -> None:
    """Scan new pools across SCAN_CHAINS, enrich, score, alert subscribers."""
    subscribers = await SubscriberQueries.get_all_subscribers()
    interested = [s for s in subscribers if s.get("alert_new_coins", 1)]
    if not interested:
        log.debug("No subscribers want new-token alerts, skipping discovery")
        return

    async with aiohttp.ClientSession() as session:
        for chain in SCAN_CHAINS:
            try:
                pools = await geckoterminal.fetch_new_pools(session, chain)
            except Exception:
                log.debug("Discovery: fetch_new_pools failed for %s", chain, exc_info=True)
                continue

            for pool in pools[:30]:
                t = _token_from_pool(pool, chain)
                if not t or not t.address:
                    continue
                if t.liquidity_usd < MIN_LIQUIDITY:
                    continue
                if t.pair_created_at:
                    age = (datetime.utcnow() - t.pair_created_at).days
                    if age > MAX_AGE_DAYS:
                        continue

                existing = await TokenQueries.get_token(chain, t.address)
                if existing:
                    continue

                try:
                    t = await enrich_token(session, t)
                except Exception:
                    log.debug("Discovery enrich failed %s/%s", chain, t.address, exc_info=True)
                    continue

                if t.is_honeypot:
                    continue

                score = compute_score(t)
                if score.total < MIN_SCORE:
                    continue

                await TokenQueries.upsert_token(t)
                await TokenQueries.save_score(score)
                await TokenQueries.record_price(chain, t.address, t.price_usd, t.liquidity_usd)

                log.info(
                    "Discovery hit: %s/%s score=%d liq=$%.0f",
                    chain, t.symbol or t.address, score.total, t.liquidity_usd,
                )
                await _broadcast(bot, interested, t, score)


async def _broadcast(bot: Bot, subs: list[dict], token: Token, score) -> None:
    text = (
        f"\U0001f4e2 <b>Новый токен в радаре</b>\n\n"
        f"{format_token_card(token, score)}"
    )
    for sub in subs:
        if score.total < sub.get("min_score", 60):
            continue
        try:
            await bot.send_message(
                sub["user_id"], text, parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception:
            log.debug("Discovery broadcast failed to %d", sub["user_id"], exc_info=True)
