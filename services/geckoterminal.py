from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from models.token import Token, SUPPORTED_CHAINS

log = logging.getLogger(__name__)

BASE = "https://api.geckoterminal.com/api/v2"
TIMEOUT = aiohttp.ClientTimeout(total=15)
HEADERS = {"Accept": "application/json;version=20230302"}


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def _f(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


async def fetch_token_pools(
    session: aiohttp.ClientSession, chain: str, address: str
) -> list[dict]:
    """Returns all pools for a token on a specific network, sorted by liquidity desc."""
    cfg = SUPPORTED_CHAINS.get(chain)
    if not cfg:
        return []
    url = f"{BASE}/networks/{cfg['gt_slug']}/tokens/{address}/pools"
    try:
        async with session.get(url, headers=HEADERS, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                log.debug("GT pools %s/%s -> %d", chain, address, resp.status)
                return []
            data = await resp.json()
            pools = data.get("data") or []
            pools.sort(
                key=lambda p: _f(p.get("attributes", {}).get("reserve_in_usd")),
                reverse=True,
            )
            return pools
    except Exception:
        log.debug("GT pools fetch failed for %s/%s", chain, address, exc_info=True)
        return []


async def fetch_token_on_chain(
    session: aiohttp.ClientSession, chain: str, address: str
) -> Token | None:
    """Builds a Token from GeckoTerminal token+pool data on a known chain."""
    cfg = SUPPORTED_CHAINS.get(chain)
    if not cfg:
        return None

    pools = await fetch_token_pools(session, chain, address)
    if not pools:
        return None

    top = pools[0]
    attrs = top.get("attributes", {})

    token_url = f"{BASE}/networks/{cfg['gt_slug']}/tokens/{address}"
    token_attrs: dict = {}
    try:
        async with session.get(token_url, headers=HEADERS, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                tdata = await resp.json()
                token_attrs = (tdata.get("data") or {}).get("attributes", {})
    except Exception:
        log.debug("GT token fetch failed", exc_info=True)

    name = token_attrs.get("name") or attrs.get("name", "")
    symbol = token_attrs.get("symbol") or ""

    price_changes = attrs.get("price_change_percentage") or {}

    return Token(
        chain=chain,
        address=address.lower() if cfg["family"] == "evm" else address,
        symbol=symbol,
        name=name,
        price_usd=_f(attrs.get("base_token_price_usd")),
        fdv=_f(token_attrs.get("fdv_usd")),
        market_cap=_f(token_attrs.get("market_cap_usd")),
        liquidity_usd=_f(attrs.get("reserve_in_usd")),
        volume_24h=_f((attrs.get("volume_usd") or {}).get("h24")),
        price_change_1h=_f(price_changes.get("h1")),
        price_change_24h=_f(price_changes.get("h24")),
        pair_address=attrs.get("address", ""),
        dex=(top.get("relationships", {}).get("dex", {}).get("data", {}) or {}).get("id", ""),
        pair_created_at=_parse_iso(attrs.get("pool_created_at")),
    )


async def find_token_multi_chain(
    session: aiohttp.ClientSession, address: str, candidate_chains: list[str]
) -> list[Token]:
    """Probe candidate chains in parallel and return tokens that resolve."""
    import asyncio

    tasks = [fetch_token_on_chain(session, c, address) for c in candidate_chains]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [t for t in results if isinstance(t, Token)]


async def fetch_new_pools(
    session: aiohttp.ClientSession, chain: str, page: int = 1
) -> list[dict]:
    """Returns recent new pools on a network (Phase 3 discovery)."""
    cfg = SUPPORTED_CHAINS.get(chain)
    if not cfg:
        return []
    url = f"{BASE}/networks/{cfg['gt_slug']}/new_pools"
    try:
        async with session.get(
            url, params={"page": page}, headers=HEADERS, timeout=TIMEOUT
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data") or []
    except Exception:
        log.debug("GT new_pools failed for %s", chain, exc_info=True)
        return []
