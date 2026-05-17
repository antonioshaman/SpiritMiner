from __future__ import annotations

import logging
import math
from datetime import datetime

import aiohttp

from models.token import Token, TokenScoreBreakdown, SUPPORTED_CHAINS
from models.score import ExitSignal
from . import geckoterminal, goplus, tonapi

log = logging.getLogger(__name__)


async def enrich_token(session: aiohttp.ClientSession, token: Token) -> Token:
    cfg = SUPPORTED_CHAINS.get(token.chain)
    if not cfg:
        return token
    family = cfg["family"]
    if family == "ton":
        return await tonapi.enrich_ton(session, token)
    return await goplus.enrich_security(session, token)


def compute_score(token: Token) -> TokenScoreBreakdown:
    s = TokenScoreBreakdown(chain=token.chain, address=token.address)

    # Liquidity: 0-25, log10($) — $1k=0, $100k=20, $1M=25
    if token.liquidity_usd > 0:
        liq_log = math.log10(token.liquidity_usd)
        if liq_log >= 6:
            s.liquidity_score = 25
        elif liq_log >= 3:
            s.liquidity_score = int((liq_log - 3) / 3 * 25)
        else:
            s.liquidity_score = 0

    # Age: 0-20 — fresh = high (DeFi-degen logic). <7d=20, >180d=5
    age = token.age_days
    if 0 < age <= 7:
        s.age_score = 20
    elif age <= 30:
        s.age_score = 15
    elif age <= 90:
        s.age_score = 10
    elif age > 0:
        s.age_score = 5

    # Holders: 0-15 — log scale
    if token.holder_count > 0:
        h_log = math.log10(token.holder_count)
        if h_log >= 4:
            s.holders_score = 15
        elif h_log >= 2:
            s.holders_score = int((h_log - 2) / 2 * 15)

    # Volume: 0-10 — $10k=5, $100k=10
    if token.volume_24h >= 100_000:
        s.volume_score = 10
    elif token.volume_24h >= 10_000:
        s.volume_score = 5
    elif token.volume_24h >= 1_000:
        s.volume_score = 2

    # Security: 0-30 base for full audit, capped at 15 for limited (TON)
    if token.audit_coverage == "full":
        sec = 30
        if not token.is_verified:
            sec -= 15
        if token.is_mintable:
            sec -= 5
        if token.is_proxy:
            sec -= 5
        if token.lp_locked_pct >= 50:
            sec += 0
        else:
            sec -= 5
        s.security_score = max(0, sec)
    elif token.audit_coverage == "limited":
        # TON: cap at 15
        sec = 10
        if token.is_verified:
            sec += 5
        s.security_score = sec

    # Penalties (negative)
    if token.is_honeypot:
        s.penalty_honeypot = -100
    if not token.is_verified and token.audit_coverage == "full":
        s.penalty_unverified = -25
    if token.top10_concentration > 50:
        s.penalty_concentration = -25
    elif token.top10_concentration > 30:
        s.penalty_concentration = -10
    if token.audit_coverage == "full" and token.lp_locked_pct < 20:
        s.penalty_lp_unlocked = -15
    if token.is_mintable:
        s.penalty_mintable = -10
    if token.is_proxy:
        s.penalty_proxy = -10
    if token.can_take_back_ownership or token.hidden_owner:
        s.penalty_owner_risk = -20

    s.compute_total()
    return s


async def check_exit_signals(
    session: aiohttp.ClientSession,
    token: Token,
    history: list[dict],
    entry_price: float = 0,
) -> list[ExitSignal]:
    signals: list[ExitSignal] = []

    if token.is_honeypot:
        signals.append(ExitSignal(
            coin_id=0,
            signal_type="HONEYPOT",
            severity="critical",
            message="Контракт помечен как honeypot — продать невозможно",
            detected_at=datetime.utcnow(),
        ))

    if token.price_change_1h <= -20:
        signals.append(ExitSignal(
            coin_id=0,
            signal_type="DUMP_1H",
            severity="critical",
            message=f"Цена -{abs(token.price_change_1h):.1f}% за 1 час",
            detected_at=datetime.utcnow(),
        ))

    if history and len(history) >= 2:
        latest = history[-1]
        oldest = history[0]
        latest_liq = latest.get("liquidity_usd") or 0
        oldest_liq = oldest.get("liquidity_usd") or 0
        if oldest_liq > 0 and latest_liq < oldest_liq * 0.7:
            drop_pct = (1 - latest_liq / oldest_liq) * 100
            signals.append(ExitSignal(
                coin_id=0,
                signal_type="LIQUIDITY_DRAIN",
                severity="critical",
                message=f"Ликвидность упала на {drop_pct:.0f}% — возможный rug",
                detected_at=datetime.utcnow(),
            ))

    if token.audit_coverage == "full" and token.lp_locked_pct < 5 and token.liquidity_usd > 0:
        signals.append(ExitSignal(
            coin_id=0,
            signal_type="LP_UNLOCKED",
            severity="warning",
            message=f"LP не залочен ({token.lp_locked_pct:.0f}%) — риск rug-pull",
            detected_at=datetime.utcnow(),
        ))

    if entry_price > 0 and token.price_usd > 0:
        change = (token.price_usd / entry_price - 1) * 100
        if change <= -50:
            signals.append(ExitSignal(
                coin_id=0,
                signal_type="STOPLOSS",
                severity="critical",
                message=f"От входа {change:+.0f}%",
                detected_at=datetime.utcnow(),
            ))

    return signals
