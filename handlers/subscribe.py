from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import SubscriberQueries, WatchlistQueries, CoinQueries
from keyboards.callbacks import MenuAction, CoinAction
from keyboards.main_menu import back_to_menu_kb, coin_actions_kb

router = Router()


@router.callback_query(MenuAction.filter(F.action == "subscribe"))
async def cb_subscribe(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    is_sub = await SubscriberQueries.is_subscribed(user_id)

    if is_sub:
        await SubscriberQueries.unsubscribe(user_id)
        await callback.message.edit_text(
            "\U0001f515 <b>Подписка отключена</b>\n\n"
            "Ты больше не будешь получать алерты о новых монетах.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
    else:
        username = callback.from_user.username or ""
        await SubscriberQueries.subscribe(user_id, username)
        await callback.message.edit_text(
            "\U0001f514 <b>Подписка активирована!</b>\n\n"
            "Ты будешь получать уведомления:\n"
            "• Новая монета со скорингом 60+\n"
            "• Сигналы выхода для монет в твоём watchlist\n\n"
            "Добавляй монеты в watchlist через карточку монеты.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(CoinAction.filter(F.action == "watch"))
async def cb_watch_coin(callback: CallbackQuery, callback_data: CoinAction) -> None:
    user_id = callback.from_user.id
    coin_id = callback_data.coin_id

    coin = await CoinQueries.get_coin(coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    watchlist = await WatchlistQueries.get_user_watchlist(user_id)

    if coin_id in watchlist:
        await WatchlistQueries.remove(user_id, coin_id)
        await callback.answer(f"{coin.tag} убран из watchlist", show_alert=True)
    else:
        await WatchlistQueries.add(user_id, coin_id)
        if not await SubscriberQueries.is_subscribed(user_id):
            username = callback.from_user.username or ""
            await SubscriberQueries.subscribe(user_id, username)
        await callback.answer(f"{coin.tag} добавлен в watchlist! Алерты включены.", show_alert=True)
