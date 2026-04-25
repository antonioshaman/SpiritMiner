from __future__ import annotations

import logging

import aiohttp

import config
from models.coin import Coin
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.5)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Token {config.WTM_API_KEY}"}


async def fetch_all_coins(session: aiohttp.ClientSession) -> list[Coin]:
    await _limiter.acquire()
    coins: list[Coin] = []

    try:
        async with session.get(
            f"{config.WTM_API_BASE}/coins",
            headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                log.warning("WhatToMine /coins returned %d", resp.status)
                return coins
            data = await resp.json()
    except Exception:
        log.exception("Failed to fetch WhatToMine coins")
        return coins

    items = data if isinstance(data, list) else data.get("coins", data.get("data", []))

    if isinstance(items, dict):
        items = list(items.values())

    for item in items:
        try:
            coin = _parse_coin(item)
            if coin:
                coins.append(coin)
        except Exception:
            log.debug("Failed to parse coin: %s", item.get("tag", "?"), exc_info=True)

    log.info("Fetched %d coins from WhatToMine", len(coins))
    return coins


async def fetch_coin_detail(session: aiohttp.ClientSession, coin_id: int) -> Coin | None:
    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.WTM_API_BASE}/coins/{coin_id}",
            headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return _parse_coin(data)
    except Exception:
        log.exception("Failed to fetch coin detail %d", coin_id)
        return None


async def fetch_algorithms(session: aiohttp.ClientSession) -> list[dict]:
    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.WTM_API_BASE}/algorithms",
            headers=_headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data if isinstance(data, list) else data.get("algorithms", [])
    except Exception:
        log.exception("Failed to fetch algorithms")
        return []


def _parse_coin(d: dict) -> Coin | None:
    coin_id = d.get("id")
    tag = d.get("tag") or d.get("symbol", "")
    name = d.get("name", "")
    algo = d.get("algorithm", "")

    if not tag or not name:
        return None

    return Coin(
        id=int(coin_id) if coin_id else hash(tag) & 0x7FFFFFFF,
        tag=tag.upper(),
        name=name,
        algorithm=algo,
        block_time=float(d.get("block_time", 0) or 0),
        block_reward=float(d.get("block_reward", 0) or 0),
        difficulty=float(d.get("difficulty", 0) or 0),
        difficulty_24h=float(d.get("difficulty24", d.get("difficulty_24h", 0)) or 0),
        difficulty_7d=float(d.get("difficulty7", d.get("difficulty_7d", 0)) or 0),
        nethash=float(d.get("nethash", 0) or 0),
        exchange_rate_btc=float(d.get("exchange_rate", d.get("exchange_rate_btc", 0)) or 0),
        exchange_rate_usd=float(d.get("exchange_rate_usd", 0) or 0),
        volume_24h=float(d.get("exchange_rate_vol", d.get("volume_24h", 0)) or 0),
        market_cap=str(d.get("market_cap", "")),
        profitability=int(d.get("profitability", 0) or 0),
        profitability_24h=int(d.get("profitability24", d.get("profitability_24h", 0)) or 0),
        status=d.get("status", "Active"),
    )
