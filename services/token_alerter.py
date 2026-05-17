from __future__ import annotations

import logging

import aiohttp
from aiogram import Bot

from db.queries import TokenQueries, TokenWatchlistQueries, SubscriberQueries
from services import geckoterminal
from services.token_scorer import enrich_token, compute_score, check_exit_signals
from utils.formatting import format_token_card, format_exit_signals

log = logging.getLogger(__name__)


async def poll_watched_tokens() -> None:
    """Refresh all watched tokens once: market data + security + history record."""
    watched = await TokenWatchlistQueries.all_watched()
    if not watched:
        return

    log.info("Polling %d watched tokens", len(watched))
    async with aiohttp.ClientSession() as session:
        for row in watched:
            chain, address = row["chain"], row["address"]
            try:
                t = await geckoterminal.fetch_token_on_chain(session, chain, address)
                if not t:
                    log.debug("Watch: %s/%s — no data", chain, address)
                    continue
                t = await enrich_token(session, t)
                score = compute_score(t)
                await TokenQueries.upsert_token(t)
                await TokenQueries.save_score(score)
                await TokenQueries.record_price(chain, address, t.price_usd, t.liquidity_usd)
            except Exception:
                log.warning("Watch poll failed for %s/%s", chain, address, exc_info=True)


async def send_token_exit_alerts(bot: Bot) -> None:
    """For each (user, token) in watchlist, check exit signals and notify."""
    watched = await TokenWatchlistQueries.all_watched()
    if not watched:
        return

    async with aiohttp.ClientSession() as session:
        for row in watched:
            chain, address = row["chain"], row["address"]
            token = await TokenQueries.get_token(chain, address)
            if not token:
                continue

            history = await TokenQueries.get_price_history(chain, address, hours=24)
            watchers = await TokenWatchlistQueries.get_watchers(chain, address)

            for w in watchers:
                user_id = w["user_id"]
                entry_price = w.get("entry_price_usd") or 0
                sub = await _get_sub(user_id)
                if sub and not sub.get("alert_exit_signals", 1):
                    continue

                signals = await check_exit_signals(session, token, history, entry_price)
                critical = [s for s in signals if s.severity == "critical"]
                if not critical:
                    continue

                already = await TokenWatchlistQueries.was_alert_sent(
                    user_id, chain, address, "exit"
                )
                if already:
                    continue

                text = (
                    f"\U0001f6a8 <b>Сигнал выхода (токен)</b>\n\n"
                    f"{format_token_card(token)}\n\n"
                    f"{format_exit_signals(critical)}"
                )
                try:
                    await bot.send_message(
                        user_id, text, parse_mode="HTML", disable_web_page_preview=True
                    )
                    await TokenWatchlistQueries.mark_alert_sent(
                        user_id, chain, address, "exit"
                    )
                    log.info("Token exit alert: %s/%s -> user %d", chain, address, user_id)
                except Exception:
                    log.debug("Token alert send failed to %d", user_id, exc_info=True)


_sub_cache: dict[int, dict] = {}


async def _get_sub(user_id: int) -> dict | None:
    if user_id in _sub_cache:
        return _sub_cache[user_id]
    subs = await SubscriberQueries.get_all_subscribers()
    _sub_cache.clear()
    for s in subs:
        _sub_cache[s["user_id"]] = s
    return _sub_cache.get(user_id)
