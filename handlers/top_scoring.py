from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import CoinQueries
from keyboards.callbacks import MenuAction, PageAction
from keyboards.main_menu import coin_list_kb, back_to_menu_kb
from utils.formatting import format_coin_list_item

router = Router()

_cache: list = []


@router.callback_query(MenuAction.filter(F.action == "top_scoring"))
async def cb_top_scoring(callback: CallbackQuery) -> None:
    global _cache
    results = await CoinQueries.top_scored(limit=50)

    if not results:
        await callback.message.edit_text(
            "\U0001f3c6 Скоринг ещё не рассчитан.\n\n"
            "Данные обновляются каждый час после первого сканирования.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    _cache = results

    lines = ["\U0001f3c6 <b>Топ по раннему скорингу:</b>\n"]
    for i, (coin, score) in enumerate(results[:10], 1):
        lines.append(format_coin_list_item(coin, score, i))

    coins_for_kb = [item for item in results]
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=coin_list_kb(coins_for_kb, 0, "top"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(PageAction.filter(F.list_type == "top"))
async def cb_top_page(callback: CallbackQuery, callback_data: PageAction) -> None:
    page = callback_data.page
    results = _cache if _cache else await CoinQueries.top_scored(limit=50)

    start = page * 10
    page_items = results[start:start + 10]

    lines = [f"\U0001f3c6 <b>Топ по скорингу (стр. {page + 1}):</b>\n"]
    for i, (coin, score) in enumerate(page_items, start + 1):
        lines.append(format_coin_list_item(coin, score, i))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=coin_list_kb(results, page, "top"),
        parse_mode="HTML",
    )
    await callback.answer()
