from __future__ import annotations

import logging

from aiogram import Bot

from db.queries import CoinQueries, SubscriberQueries, WatchlistQueries
from models.coin import Coin
from models.score import ScoreBreakdown
from services.scorer import check_exit_signals
from utils.formatting import format_coin_card, format_exit_signals

log = logging.getLogger(__name__)


async def send_new_coin_alerts(bot: Bot) -> None:
    subscribers = await SubscriberQueries.get_all_subscribers()
    if not subscribers:
        return

    results = await CoinQueries.top_scored(limit=50)

    for coin, score in results:
        if score.total < 60:
            continue

        for sub in subscribers:
            user_id = sub["user_id"]
            min_score = sub.get("min_score", 60)
            if score.total < min_score:
                continue
            if not sub.get("alert_new_coins", 1):
                continue

            already_sent = await SubscriberQueries.was_alert_sent(
                user_id, coin.id, "new_coin"
            )
            if already_sent:
                continue

            text = (
                f"\U0001f4e2 <b>Новый сигнал!</b>\n\n"
                f"{format_coin_card(coin, score)}"
            )
            try:
                await bot.send_message(user_id, text, parse_mode="HTML")
                await SubscriberQueries.mark_alert_sent(user_id, coin.id, "new_coin")
                log.info("Alert sent: %s -> user %d", coin.tag, user_id)
            except Exception:
                log.debug("Failed to send alert to %d", user_id, exc_info=True)


async def send_exit_alerts(bot: Bot) -> None:
    subscribers = await SubscriberQueries.get_all_subscribers()
    if not subscribers:
        return

    for sub in subscribers:
        user_id = sub["user_id"]
        if not sub.get("alert_exit_signals", 1):
            continue

        watchlist = await WatchlistQueries.get_user_watchlist(user_id)
        if not watchlist:
            continue

        for coin_id in watchlist:
            coin = await CoinQueries.get_coin(coin_id)
            if not coin:
                continue

            signals = await check_exit_signals(coin)
            critical = [s for s in signals if s.severity == "critical"]
            if not critical:
                continue

            already_sent = await SubscriberQueries.was_alert_sent(
                user_id, coin_id, "exit"
            )
            if already_sent:
                continue

            text = (
                f"\U0001f6a8 <b>Сигнал выхода!</b>\n\n"
                f"<b>{coin.name} ({coin.tag})</b>\n\n"
                f"{format_exit_signals(critical)}"
            )
            try:
                await bot.send_message(user_id, text, parse_mode="HTML")
                await SubscriberQueries.mark_alert_sent(user_id, coin_id, "exit")
                log.info("Exit alert sent: %s -> user %d", coin.tag, user_id)
            except Exception:
                log.debug("Failed to send exit alert to %d", user_id, exc_info=True)
