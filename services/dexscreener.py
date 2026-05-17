from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from models.token import Token, SUPPORTED_CHAINS

log = logging.getLogger(__name__)

BASE = "https://api.dexscreener.com/latest/dex"
TIMEOUT = aiohttp.ClientTimeout(total=15)

# Dexscreener chainId -> our chain name
CHAIN_MAP = {
    "ethereum": "ethereum",
    "bsc": "bsc",
    "base": "base",
    "arbitrum": "arbitrum",
    "polygon": "polygon",
    "optimism": "optimism",
    "avalanche": "avalanche",
    "solana": "solana",
    "ton": "ton",
}


def _f(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _pair_to_token(pair: dict) -> Token | None:
    chain_id = pair.get("chainId", "")
    chain = CHAIN_MAP.get(chain_id)
    if not chain:
        return None

    base = pair.get("baseToken") or {}
    address = base.get("address", "")
    if not address:
        return None
    if SUPPORTED_CHAINS[chain]["family"] == "evm":
        address = address.lower()

    created_ms = pair.get("pairCreatedAt")
    pair_created_at = None
    if created_ms:
        try:
            pair_created_at = datetime.utcfromtimestamp(int(created_ms) / 1000)
        except (ValueError, TypeError):
            pass

    price_change = pair.get("priceChange") or {}
    volume = pair.get("volume") or {}
    liquidity = pair.get("liquidity") or {}

    return Token(
        chain=chain,
        address=address,
        symbol=base.get("symbol", ""),
        name=base.get("name", ""),
        price_usd=_f(pair.get("priceUsd")),
        fdv=_f(pair.get("fdv")),
        market_cap=_f(pair.get("marketCap")),
        liquidity_usd=_f(liquidity.get("usd")),
        volume_24h=_f(volume.get("h24")),
        price_change_1h=_f(price_change.get("h1")),
        price_change_24h=_f(price_change.get("h24")),
        pair_address=pair.get("pairAddress", ""),
        dex=pair.get("dexId", ""),
        pair_created_at=pair_created_at,
    )


async def fetch_token_pairs(
    session: aiohttp.ClientSession, address: str
) -> list[Token]:
    """Returns Token candidates across all chains where this address has a tracked pair."""
    url = f"{BASE}/tokens/{address}"
    try:
        async with session.get(url, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    except Exception:
        log.debug("Dexscreener fetch failed for %s", address, exc_info=True)
        return []

    pairs = data.get("pairs") or []
    # Group by chain, keep highest-liquidity pair per chain
    best_per_chain: dict[str, Token] = {}
    for p in pairs:
        t = _pair_to_token(p)
        if not t:
            continue
        cur = best_per_chain.get(t.chain)
        if cur is None or t.liquidity_usd > cur.liquidity_usd:
            best_per_chain[t.chain] = t
    return list(best_per_chain.values())
