from __future__ import annotations

import logging

import aiohttp

from models.token import Token

log = logging.getLogger(__name__)

BASE = "https://tonapi.io/v2"
TIMEOUT = aiohttp.ClientTimeout(total=15)


def _f(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


async def enrich_ton(session: aiohttp.ClientSession, token: Token) -> Token:
    url = f"{BASE}/jettons/{token.address}"
    try:
        async with session.get(url, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                token.audit_coverage = "limited"
                token.risk_flags.append(f"tonapi_http_{resp.status}")
                return token
            data = await resp.json()
    except Exception:
        log.debug("tonapi failed for %s", token.address, exc_info=True)
        token.audit_coverage = "limited"
        token.risk_flags.append("tonapi_error")
        return token

    metadata = data.get("metadata") or {}
    if metadata.get("symbol") and not token.symbol:
        token.symbol = metadata["symbol"]
    if metadata.get("name") and not token.name:
        token.name = metadata["name"]

    if data.get("holders_count"):
        try:
            token.holder_count = int(data["holders_count"])
        except (ValueError, TypeError):
            pass

    verification = data.get("verification") or ""
    token.is_verified = verification == "whitelist"
    if verification == "blacklist":
        token.is_honeypot = True
        token.risk_flags.append("ton_blacklist")
    elif verification == "none":
        token.risk_flags.append("ton_unverified")

    mintable = data.get("mintable")
    if mintable is True:
        token.is_mintable = True

    admin = data.get("admin") or {}
    if admin.get("address") and admin.get("address") != "0:0000000000000000000000000000000000000000000000000000000000000000":
        token.risk_flags.append("ton_admin_present")

    try:
        holders_url = f"{BASE}/jettons/{token.address}/holders"
        async with session.get(holders_url, params={"limit": 10}, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                hdata = await resp.json()
                addresses = hdata.get("addresses") or []
                total_supply = _f(data.get("total_supply"))
                if total_supply > 0 and addresses:
                    top10_balance = sum(_f(a.get("balance")) for a in addresses[:10])
                    token.top10_concentration = min(100.0, top10_balance / total_supply * 100)
    except Exception:
        log.debug("tonapi holders failed", exc_info=True)

    token.audit_coverage = "limited"
    return token
