from __future__ import annotations

import logging
from datetime import datetime, timedelta

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


def _pick_baseline(history: list[dict], window_hours: int) -> dict | None:
    """Record closest to `window_hours` ago; None if history is too short."""
    if not history:
        return None
    now = datetime.utcnow()
    oldest = _parse_ts(history[0].get("recorded_at"))
    if oldest is None:
        return None
    # Need a data point old enough to represent the start of the window.
    if (now - oldest).total_seconds() < (window_hours - 1) * 3600:
        return None
    target = now - timedelta(hours=window_hours)
    best, best_gap = None, None
    for row in history:
        ts = _parse_ts(row.get("recorded_at"))
        if ts is None:
            continue
        gap = abs((ts - target).total_seconds())
        if best_gap is None or gap < best_gap:
            best, best_gap = row, gap
    return best


async def poll_ton_candle_signal(bot: Bot) -> None:
    """Hourly: record on-chain TON price and emit a 12h-candle signal on |Δ| >= threshold."""
    chain = config.TON_SIGNAL_CHAIN
    address = config.TON_SIGNAL_CONTRACT.lower()

    async with aiohttp.ClientSession() as session:
        token = await geckoterminal.fetch_token_on_chain(session, chain, address)

    if not token or token.price_usd <= 0:
        log.warning("Candle signal: no on-chain price for %s/%s, skipping", chain, address)
        return

    await TokenQueries.record_price(chain, address, token.price_usd, token.liquidity_usd)

    history = await TokenQueries.get_price_history(
        chain, address, hours=config.CANDLE_WINDOW_HOURS + 1
    )
    baseline = _pick_baseline(history, config.CANDLE_WINDOW_HOURS)
    if baseline is None:
        log.info("Candle signal: insufficient history (< %dh), skipping", config.CANDLE_WINDOW_HOURS)
        return

    old_price = float(baseline.get("price_usd") or 0)
    if old_price <= 0:
        log.info("Candle signal: invalid baseline price, skipping")
        return

    change_pct = (token.price_usd - old_price) / old_price * 100.0
    threshold = config.CANDLE_THRESHOLD_PCT

    if change_pct >= threshold:
        await _broadcast(bot, chain, address, GREEN_ALERT, old_price, token.price_usd, change_pct)
        await TokenWatchlistQueries.clear_alerts(chain, address, RED_ALERT)
    elif change_pct <= -threshold:
        await _broadcast(bot, chain, address, RED_ALERT, old_price, token.price_usd, change_pct)
        await TokenWatchlistQueries.clear_alerts(chain, address, GREEN_ALERT)
    else:
        # Movement fell back inside the band: reset both so the next crossing re-fires.
        await TokenWatchlistQueries.clear_alerts(chain, address, GREEN_ALERT)
        await TokenWatchlistQueries.clear_alerts(chain, address, RED_ALERT)


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
