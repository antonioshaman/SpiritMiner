from __future__ import annotations

import logging

import aiohttp

from models.token import Token, SUPPORTED_CHAINS

log = logging.getLogger(__name__)

BASE = "https://api.gopluslabs.io/api/v1"
TIMEOUT = aiohttp.ClientTimeout(total=15)


def _bool(v) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip() == "1"


def _f(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


async def enrich_evm(
    session: aiohttp.ClientSession, token: Token
) -> Token:
    cfg = SUPPORTED_CHAINS[token.chain]
    chain_id = cfg["goplus"]
    url = f"{BASE}/token_security/{chain_id}"
    params = {"contract_addresses": token.address}
    try:
        async with session.get(url, params=params, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                token.audit_coverage = "none"
                token.risk_flags.append(f"goplus_http_{resp.status}")
                return token
            data = await resp.json()
    except Exception:
        log.debug("GoPlus EVM failed for %s/%s", token.chain, token.address, exc_info=True)
        token.audit_coverage = "none"
        token.risk_flags.append("goplus_error")
        return token

    result = (data.get("result") or {}).get(token.address.lower()) or {}
    if not result:
        token.audit_coverage = "none"
        token.risk_flags.append("goplus_no_data")
        return token

    token.is_honeypot = _bool(result.get("is_honeypot"))
    token.is_verified = _bool(result.get("is_open_source"))
    token.is_mintable = _bool(result.get("is_mintable"))
    token.is_proxy = _bool(result.get("is_proxy"))
    token.can_take_back_ownership = _bool(result.get("can_take_back_ownership"))
    token.hidden_owner = _bool(result.get("hidden_owner"))

    holder_count = result.get("holder_count")
    if holder_count:
        try:
            token.holder_count = int(holder_count)
        except (ValueError, TypeError):
            pass

    holders = result.get("holders") or []
    try:
        top10_sum = sum(_f(h.get("percent")) for h in holders[:10])
        token.top10_concentration = top10_sum * 100 if top10_sum <= 1 else top10_sum
    except Exception:
        pass

    lp_holders = result.get("lp_holders") or []
    locked_pct = 0.0
    for h in lp_holders:
        if _bool(h.get("is_locked")):
            locked_pct += _f(h.get("percent")) * (100 if _f(h.get("percent")) <= 1 else 1)
    token.lp_locked_pct = min(100.0, locked_pct)

    if _bool(result.get("transfer_pausable")):
        token.risk_flags.append("transfer_pausable")
    if _bool(result.get("is_blacklisted")):
        token.risk_flags.append("blacklist_fn")
    if _bool(result.get("trading_cooldown")):
        token.risk_flags.append("trading_cooldown")
    if _bool(result.get("slippage_modifiable")):
        token.risk_flags.append("slippage_modifiable")

    buy_tax = _f(result.get("buy_tax"))
    sell_tax = _f(result.get("sell_tax"))
    if buy_tax > 0.10:
        token.risk_flags.append(f"buy_tax_{int(buy_tax*100)}pct")
    if sell_tax > 0.10:
        token.risk_flags.append(f"sell_tax_{int(sell_tax*100)}pct")

    token.audit_coverage = "full"
    return token


async def enrich_solana(
    session: aiohttp.ClientSession, token: Token
) -> Token:
    url = f"{BASE}/solana/token_security"
    params = {"contract_addresses": token.address}
    try:
        async with session.get(url, params=params, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                token.audit_coverage = "limited"
                token.risk_flags.append(f"goplus_sol_http_{resp.status}")
                return token
            data = await resp.json()
    except Exception:
        log.debug("GoPlus Solana failed for %s", token.address, exc_info=True)
        token.audit_coverage = "limited"
        token.risk_flags.append("goplus_sol_error")
        return token

    result = (data.get("result") or {}).get(token.address) or {}
    if not result:
        token.audit_coverage = "limited"
        return token

    metadata = result.get("metadata") or {}
    mintable = (result.get("mintable") or {})
    freezable = (result.get("freezable") or {})

    token.is_mintable = _bool(mintable.get("status")) and mintable.get("status") != "0"
    token.is_verified = _bool(metadata.get("description"))  # weak proxy
    if _bool(freezable.get("status")) and freezable.get("status") != "0":
        token.risk_flags.append("freezable")

    holders = result.get("holders") or []
    try:
        top10 = sum(_f(h.get("percent")) for h in holders[:10])
        token.top10_concentration = top10 * 100 if top10 <= 1 else top10
    except Exception:
        pass

    if result.get("holder_count"):
        try:
            token.holder_count = int(result["holder_count"])
        except (ValueError, TypeError):
            pass

    transfer_fee = result.get("transfer_fee") or {}
    if _f(transfer_fee.get("current_fee_rate")) > 0.05:
        token.risk_flags.append("solana_transfer_fee")

    token.audit_coverage = "full"
    return token


async def enrich_security(
    session: aiohttp.ClientSession, token: Token
) -> Token:
    cfg = SUPPORTED_CHAINS.get(token.chain)
    if not cfg:
        token.audit_coverage = "none"
        return token

    family = cfg["family"]
    if family == "evm":
        return await enrich_evm(session, token)
    if family == "solana":
        return await enrich_solana(session, token)
    # ton — no GoPlus support; handled separately in tonapi
    token.audit_coverage = "limited"
    return token
