from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

import config
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.3)

_coin_list_cache: list[dict] | None = None


async def _get_coin_list(session: aiohttp.ClientSession) -> list[dict]:
    global _coin_list_cache
    if _coin_list_cache is not None:
        return _coin_list_cache

    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.COINGECKO_BASE}/coins/list",
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                _coin_list_cache = await resp.json()
                return _coin_list_cache
    except Exception:
        log.debug("CoinGecko coin list fetch failed", exc_info=True)
    return []


async def find_coingecko_id(
    session: aiohttp.ClientSession, tag: str, name: str
) -> str:
    coins = await _get_coin_list(session)
    tag_lower = tag.lower()
    name_lower = name.lower()

    for c in coins:
        if c.get("symbol", "").lower() == tag_lower:
            if name_lower in c.get("name", "").lower() or c.get("name", "").lower() in name_lower:
                return c.get("id", "")

    for c in coins:
        if c.get("symbol", "").lower() == tag_lower:
            return c.get("id", "")

    return ""


async def get_market_data(
    session: aiohttp.ClientSession, coingecko_id: str
) -> dict:
    if not coingecko_id:
        return {}

    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.COINGECKO_BASE}/coins/{coingecko_id}",
            params={
                "localization": "false",
                "tickers": "true",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "true",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()
    except Exception:
        log.debug("CoinGecko market data failed for %s", coingecko_id, exc_info=True)
        return {}


def extract_exchange_count(market_data: dict) -> int:
    tickers = market_data.get("tickers", [])
    exchanges = {t.get("market", {}).get("name", "") for t in tickers}
    exchanges.discard("")
    return len(exchanges)


def extract_volume(market_data: dict) -> float:
    md = market_data.get("market_data", {})
    vol = md.get("total_volume", {})
    return float(vol.get("usd", 0) or 0)


def extract_community_active(market_data: dict) -> bool:
    cd = market_data.get("community_data", {})
    twitter = cd.get("twitter_followers", 0) or 0
    reddit = cd.get("reddit_subscribers", 0) or 0
    tg = cd.get("telegram_channel_user_count", 0) or 0
    return (twitter + reddit + tg) > 100


def extract_github_url(market_data: dict) -> str:
    repos = market_data.get("developer_data", {}).get("code_additions_deletions_4_weeks", None)
    links = market_data.get("links", {})
    gh_repos = links.get("repos_url", {}).get("github", [])
    if gh_repos:
        return gh_repos[0]
    return ""


def extract_has_premine(market_data: dict) -> bool:
    desc = (market_data.get("description", {}).get("en", "") or "").lower()
    return "premine" in desc or "pre-mine" in desc or "pre-mined" in desc


def extract_genesis_date(market_data: dict) -> datetime | None:
    gd = market_data.get("genesis_date", "")
    if gd:
        try:
            return datetime.fromisoformat(gd)
        except (ValueError, TypeError):
            pass
    return None
