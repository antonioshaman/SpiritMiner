from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import CoinQueries, VoteQueries, ActionQueries
from keyboards.callbacks import MenuAction, VoteAction, TradeAction, CoinAction
from keyboards.main_menu import coin_actions_kb, back_to_menu_kb
from utils.formatting import format_coin_card

router = Router()


@router.callback_query(VoteAction.filter())
async def cb_vote(callback: CallbackQuery, callback_data: VoteAction) -> None:
    user_id = callback.from_user.id
    coin_id = callback_data.coin_id
    vote = callback_data.vote

    await VoteQueries.vote(user_id, coin_id, vote)

    sentiment = await VoteQueries.get_sentiment(coin_id)
    total = sentiment["total"]
    if total > 0:
        bull_pct = sentiment["bullish"] * 100 // total
        emoji_map = {"bullish": "\U0001f44d", "watching": "\U0001f440", "bearish": "❌"}
        await callback.answer(
            f"Голос принят! Sentiment: {bull_pct}% bullish ({total} голосов)",
            show_alert=True,
        )
    else:
        await callback.answer("Голос принят!", show_alert=True)


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
    await ActionQueries.record_action(user_id, coin_id, action, price)

    if action == "enter":
        await callback.answer(
            f"⛏️ Зашёл в {coin.tag} по ${price:.6f}. Удачи!",
            show_alert=True,
        )
    else:
        pairs = await ActionQueries.get_entry_exit_pairs(user_id)
        for p in pairs:
            if p["coin_id"] == coin_id and p["entry_price"]:
                entry = p["entry_price"]
                if entry > 0:
                    roi = ((price - entry) / entry) * 100
                    emoji = "\U0001f7e2" if roi > 0 else "\U0001f534"
                    await callback.answer(
                        f"\U0001f3c1 Вышел из {coin.tag}. ROI: {emoji} {roi:+.1f}%",
                        show_alert=True,
                    )
                    return
        await callback.answer(f"\U0001f3c1 Вышел из {coin.tag}", show_alert=True)


@router.callback_query(MenuAction.filter(F.action == "spirit_rank"))
async def cb_spirit_rank(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    pairs = await ActionQueries.get_entry_exit_pairs(user_id)

    lines = ["\U0001f3c6 <b>Spirit Rank</b>\n"]

    if not pairs:
        lines.append("Ты ещё не отмечал входы/выходы.")
        lines.append("Используй кнопки ⛏️ Зашёл / \U0001f3c1 Вышел в карточке монеты.")
        lines.append("")

        leaderboard = await ActionQueries.get_leaderboard(10)
        if leaderboard:
            lines.append("<b>\U0001f4ca Лидерборд:</b>\n")
            for i, entry in enumerate(leaderboard, 1):
                name = entry.get("username") or f"user_{entry['user_id']}"
                lines.append(f"{i}. @{name} — {entry['trades']} монет")
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

        rank = "Новичок"
        if completed >= 10:
            rank = "Разведчик"
        if completed >= 5 and total_roi > 0:
            rank = "Охотник"
        if completed >= 10 and total_roi / max(completed, 1) > 10:
            rank = "Мастер"

        lines.append(f"\n\U0001f396 <b>Ранг: {rank}</b>")

        leaderboard = await ActionQueries.get_leaderboard(10)
        if leaderboard:
            lines.append("\n<b>\U0001f4ca Лидерборд:</b>\n")
            for i, entry in enumerate(leaderboard, 1):
                name = entry.get("username") or f"user_{entry['user_id']}"
                you = " ← ты" if entry["user_id"] == user_id else ""
                lines.append(f"{i}. @{name} — {entry['trades']} монет{you}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
