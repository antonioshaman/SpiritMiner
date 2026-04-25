from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.callbacks import MenuAction
from keyboards.main_menu import back_to_menu_kb
from services.spirit_index import compute_spirit_index

router = Router()


@router.callback_query(MenuAction.filter(F.action == "spirit_index"))
async def cb_spirit_index(callback: CallbackQuery) -> None:
    await callback.answer("Считаю Spirit Index...", show_alert=False)

    data = await compute_spirit_index()
    c = data["components"]

    lines = [
        f"\U0001f4ca <b>Spirit Index: {data['index']}/100</b>",
        f"{data['mood']} — {data['mood_desc']}",
        "",
        "<b>Компоненты:</b>",
        f"  \U0001f4b0 Качество рынка: {c['market_quality']}/100",
        f"  \U0001f4ca Sentiment: {c['sentiment']}/100 ({data['bullish_pct']}% bullish)",
        f"  \U0001f465 Активность: {c['activity']}/100",
        f"  \U0001f50d Новые монеты: {c['discovery']}/100",
        "",
        "<b>Статистика:</b>",
        f"  ⛏️ Всего монет: {data['total_coins']}",
        f"  \U0001f195 Новых за 7д: {data['new_7d']}",
        f"  \U0001f195 Новых за 30д: {data['new_30d']}",
        f"  \U0001f7e2 Зелёных (60+): {data['green_count']}",
        f"  \U0001f4ca Голосов: {data['total_votes']}",
        f"  \U0001f465 Трейдеров: {data['active_traders']}",
        f"  \U0001f514 Подписчиков: {data['total_subs']}",
    ]

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
