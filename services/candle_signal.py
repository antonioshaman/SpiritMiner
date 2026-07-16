from __future__ import annotations

import logging
from datetime import datetime, timedelta
from statistics import median

import aiohttp
from aiogram import Bot

import config
from db.queries import SubscriberQueries, TokenQueries, TokenWatchlistQueries
from models.token import chain_explorer_url
from services import geckoterminal

log = logging.getLogger(__name__)

GREEN_ALERT = "green12h"
RED_ALERT = "red12h"

# Both directions recommend the SAME action: the ERC-20 (MetaMask) price lags the main
# course, so it stays above native on a rise (overshoots) AND on a fall (slow to correct
# down). Selling in MetaMask + buying native is favourable either way. Do NOT mirror.
RECOMMENDATION = "продать ERC-20 TON в MetaMask, купить в нативном кошельке"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _baseline_price(history: list[dict], window_hours: int, tolerance_hours: int) -> float | None:
    """Median price of records within `tolerance_hours` of the -window target.

    Median (not the single closest point) makes the baseline robust to one bad print, while
    staying compatible with the MetaMask-lag thesis (median of 2-3 nearby ticks preserves lag).
    Returns None when no record falls inside the tolerance window — i.e. history is too short
    to represent the start of the window, so no signal should fire.
    """
    if not history:
        return None
    target = datetime.utcnow() - timedelta(hours=window_hours)
    tol = tolerance_hours * 3600
    prices: list[float] = []
    for row in history:
        ts = _parse_ts(row.get("recorded_at"))
        if ts is None:
            continue
        if abs((ts - target).total_seconds()) <= tol:
            price = float(row.get("price_usd") or 0)
            if price > 0:
                prices.append(price)
    if not prices:
        return None
    return float(median(prices))


async def poll_ton_candle_signal(bot: Bot) -> None:
    """Hourly: record on-chain TON price and emit a 12h-candle signal on |Δ| >= threshold."""
    chain = config.TON_SIGNAL_CHAIN
    address = config.TON_SIGNAL_CONTRACT.lower()

    async with aiohttp.ClientSession() as session:
        token = await geckoterminal.fetch_token_on_chain(session, chain, address)

    if not token or token.price_usd <= 0:
        log.warning("Candle signal: no on-chain price for %s/%s, skipping", chain, address)
        return

    history = await TokenQueries.get_price_history(
        chain, address, hours=config.CANDLE_WINDOW_HOURS + 1
    )

    # Outlier guard: one wild print (API glitch) must not be recorded or signalled — otherwise it
    # both fires a false alert now and poisons the rolling baseline for the whole window.
    if history:
        last = float(history[-1].get("price_usd") or 0)
        if last > 0:
            dev = abs(token.price_usd - last) / last * 100.0
            if dev > config.CANDLE_OUTLIER_PCT:
                log.warning(
                    "Candle signal: outlier price %.6f vs last %.6f (%.0f%%), skipping",
                    token.price_usd, last, dev,
                )
                return

    await TokenQueries.record_price(chain, address, token.price_usd, token.liquidity_usd)
    await TokenQueries.prune_price_history(chain, address, config.CANDLE_HISTORY_RETENTION_DAYS)

    old_price = _baseline_price(
        history, config.CANDLE_WINDOW_HOURS, config.CANDLE_BASELINE_TOLERANCE_HOURS
    )
    if old_price is None:
        log.info(
            "Candle signal: no baseline within +-%dh of -%dh (insufficient history), skipping",
            config.CANDLE_BASELINE_TOLERANCE_HOURS, config.CANDLE_WINDOW_HOURS,
        )
        return

    change_pct = (token.price_usd - old_price) / old_price * 100.0
    threshold = config.CANDLE_THRESHOLD_PCT

    # Dedup / cooldown: _broadcast marks each user via `was_alert_sent`, whose window is 6h — that
    # is the effective safety-net cooldown (not the 12h window). The primary re-fire control is
    # the hysteresis re-arm below: markers are only cleared once |Δ| retreats < CANDLE_REARM_PCT.
    if change_pct >= threshold:
        await _broadcast(bot, chain, address, GREEN_ALERT, old_price, token.price_usd, change_pct)
        await TokenWatchlistQueries.clear_alerts(chain, address, RED_ALERT)
    elif change_pct <= -threshold:
        await _broadcast(bot, chain, address, RED_ALERT, old_price, token.price_usd, change_pct)
        await TokenWatchlistQueries.clear_alerts(chain, address, GREEN_ALERT)
    elif abs(change_pct) < config.CANDLE_REARM_PCT:
        # Retreated well inside the band: re-arm both directions so the next crossing re-fires.
        await TokenWatchlistQueries.clear_alerts(chain, address, GREEN_ALERT)
        await TokenWatchlistQueries.clear_alerts(chain, address, RED_ALERT)
    # else: hysteresis dead-band [REARM, threshold) — hold markers, do not re-arm.


def _format_message(alert_type: str, old_price: float, new_price: float, change_pct: float, explorer: str) -> str:
    window = config.CANDLE_WINDOW_HOURS
    if alert_type == GREEN_ALERT:
        head = f"\U0001f7e2 <b>Зелёная {window}ч-свеча TON</b>"
        move = f"Курс вырос на <b>+{change_pct:.1f}%</b> за {window}ч"
    else:
        head = f"\U0001f534 <b>Красная {window}ч-свеча TON</b>"
        move = f"Курс упал на <b>{change_pct:.1f}%</b> за {window}ч"
    return (
        f"{head}\n\n"
        f"{move}\n"
        f"${old_price:.4f} → <b>${new_price:.4f}</b>\n\n"
        f"\U0001f4b0 Сигнал: {RECOMMENDATION}\n\n"
        f"<a href=\"{explorer}\">Контракт на Etherscan</a>"
    )


async def _broadcast(
    bot: Bot, chain: str, address: str, alert_type: str,
    old_price: float, new_price: float, change_pct: float,
) -> None:
    subscribers = await SubscriberQueries.get_all_subscribers()
    if not subscribers:
        return

    text = _format_message(alert_type, old_price, new_price, change_pct, chain_explorer_url(chain, address))

    sent = 0
    for sub in subscribers:
        user_id = sub["user_id"]
        if await TokenWatchlistQueries.was_alert_sent(user_id, chain, address, alert_type):
            continue
        try:
            await bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
            await TokenWatchlistQueries.mark_alert_sent(user_id, chain, address, alert_type)
            sent += 1
        except Exception:
            log.debug("Candle signal: send failed for %d", user_id, exc_info=True)

    log.info("Candle signal: %s %.1f%%, sent to %d subscribers", alert_type, change_pct, sent)
