from html import escape as _esc

import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import CoinQueries, VoteQueries, ActionQueries, PointsQueries
from keyboards.callbacks import MenuAction, VoteAction, TradeAction, CoinAction
from keyboards.main_menu import coin_actions_kb, back_to_menu_kb
from services.market import fetch_simple_price
from utils.formatting import format_coin_card, format_price

router = Router()


@router.callback_query(VoteAction.filter())
async def cb_vote(callback: CallbackQuery, callback_data: VoteAction) -> None:
    user_id = callback.from_user.id
    coin_id = callback_data.coin_id
    vote = callback_data.vote

    await VoteQueries.vote(user_id, coin_id, vote)
    pts = await PointsQueries.award(user_id, 2)

    sentiment = await VoteQueries.get_sentiment(coin_id)
    total = sentiment["total"]
    if total > 0:
        bull_pct = sentiment["bullish"] * 100 // total
        await callback.answer(
            f"Голос принят! +2 SP ({pts}) | Sentiment: {bull_pct}% bullish ({total} голосов)",
            show_alert=True,
        )
    else:
        await callback.answer(f"Голос принят! +2 SP ({pts})", show_alert=True)


@router.callback_query(TradeAction.filter())
async def cb_trade(callback: CallbackQuery, callback_data: TradeAction) -> None:
    user_id = callback.from_user.id
    coin_id = callback_data.coin_id
    action = callback_data.action

    coin = await CoinQueries.get_coin(coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    price = coin.exchange_rate_usd or coin.exchange_rate_btc
    if not price and coin.coingecko_id:
        async with aiohttp.ClientSession() as session:
            usd, btc = await fetch_simple_price(session, coin.coingecko_id)
            if usd:
                price = usd
                coin.exchange_rate_usd = usd
                coin.exchange_rate_btc = btc
                await CoinQueries.upsert_coin(coin)
            elif btc:
                price = btc
    await ActionQueries.record_action(user_id, coin_id, action, price)
    pts = await PointsQueries.award(user_id, 5)

    if action == "enter":
        await callback.answer(
            f"⛏️ Зашёл в {coin.tag} по {format_price(price)}. +5 SP ({pts}). Удачи!",
            show_alert=True,
        )
    else:
        pairs = await ActionQueries.get_entry_exit_pairs(user_id)
        for p in pairs:
            if p["coin_id"] == coin_id and p["entry_price"]:
                entry = p["entry_price"]
                if entry > 0:
                    roi = ((price - entry) / entry) * 100
                    bonus = 10 if roi > 20 else 0
                    if bonus:
                        await PointsQueries.award(user_id, bonus)
                        pts += bonus
                    emoji = "\U0001f7e2" if roi > 0 else "\U0001f534"
                    await callback.answer(
                        f"\U0001f3c1 Вышел из {coin.tag}. ROI: {emoji} {roi:+.1f}% | +{5 + bonus} SP ({pts})",
                        show_alert=True,
                    )
                    return
        await callback.answer(f"\U0001f3c1 Вышел из {coin.tag}. +5 SP ({pts})", show_alert=True)


@router.callback_query(MenuAction.filter(F.action == "spirit_rank"))
async def cb_spirit_rank(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    points = await PointsQueries.get_points(user_id)
    level = PointsQueries.get_level(points)
    next_lvl = PointsQueries.get_next_level(points)
    pairs = await ActionQueries.get_entry_exit_pairs(user_id)

    lines = ["\U0001f3c6 <b>Spirit Rank</b>\n"]
    lines.append(f"\U0001f396 Уровень: <b>{level}</b>")
    lines.append(f"\U0001f4ab Spirit Points: <b>{points} SP</b>")
    if next_lvl:
        lines.append(f"\U0001f4a1 До <b>{next_lvl[0]}</b>: ещё {next_lvl[1]} SP")
    lines.append("")

    if not pairs:
        lines.append("Ты ещё не отмечал входы/выходы.")
        lines.append("Используй ⛏️ Зашёл / \U0001f3c1 Вышел в карточке монеты.")
        lines.append("\n<b>Как заработать SP:</b>")
        lines.append("+1 поиск монеты | +2 голос/скоринг")
        lines.append("+5 вход/выход | +10 бонус ROI>20%")
    else:
        total_roi = 0
        completed = 0
        active = 0

        for p in pairs:
            entry_price = p.get("entry_price", 0) or 0
            exit_price = p.get("exit_price")
            current = p.get("current_price", 0) or 0
            tag = p.get("tag", "?")

            if exit_price and entry_price > 0:
                roi = ((exit_price - entry_price) / entry_price) * 100
                total_roi += roi
                completed += 1
                emoji = "\U0001f7e2" if roi > 0 else "\U0001f534"
                lines.append(f"{emoji} <b>{tag}</b>: {roi:+.1f}% (закрыт)")
            elif entry_price > 0 and current > 0:
                roi = ((current - entry_price) / entry_price) * 100
                active += 1
                emoji = "\U0001f7e2" if roi > 0 else "\U0001f534"
                lines.append(f"{emoji} <b>{tag}</b>: {roi:+.1f}% (открыт)")

        lines.append("")
        if completed > 0:
            avg_roi = total_roi / completed
            lines.append(f"<b>Средний ROI:</b> {avg_roi:+.1f}%")
        lines.append(f"<b>Сделок:</b> {completed} закрыто, {active} открыто")

    top = await PointsQueries.get_top(10)
    if top:
        lines.append("\n<b>\U0001f4ca Лидерборд:</b>\n")
        for i, entry in enumerate(top, 1):
            name = _esc(entry.get("username") or f"Miner #{i}")
            you = " ← ты" if entry["user_id"] == user_id else ""
            lvl = PointsQueries.get_level(entry["points"])
            lines.append(f"{i}. {lvl} {name} — {entry['points']} SP{you}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
