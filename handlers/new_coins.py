from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import CoinQueries
from keyboards.callbacks import MenuAction, PageAction
from keyboards.main_menu import coin_list_kb, back_to_menu_kb
from utils.formatting import format_coin_list_item

router = Router()

_cache: list = []


@router.callback_query(MenuAction.filter(F.action == "new_coins"))
async def cb_new_coins(callback: CallbackQuery) -> None:
    global _cache
    coins = await CoinQueries.list_new_coins(days=30, limit=50)

    if not coins:
        await callback.message.edit_text(
            "\U0001f50d Новых PoW-монет пока не обнаружено.\n\n"
            "Данные обновляются каждые 30 минут.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    _cache = coins
    scores = {}
    for c in coins[:10]:
        s = await CoinQueries.get_latest_score(c.id)
        scores[c.id] = s

    lines = ["\U0001f195 <b>Новые PoW-монеты:</b>\n"]
    for i, coin in enumerate(coins[:10], 1):
        lines.append(format_coin_list_item(coin, scores.get(coin.id), i))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=coin_list_kb(coins, 0, "new"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(PageAction.filter(F.list_type == "new"))
async def cb_new_coins_page(callback: CallbackQuery, callback_data: PageAction) -> None:
    page = callback_data.page
    coins = _cache if _cache else await CoinQueries.list_new_coins(days=30, limit=50)

    start = page * 10
    page_coins = coins[start:start + 10]

    scores = {}
    for c in page_coins:
        s = await CoinQueries.get_latest_score(c.id)
        scores[c.id] = s

    lines = [f"\U0001f195 <b>Новые PoW-монеты (стр. {page + 1}):</b>\n"]
    for i, coin in enumerate(page_coins, start + 1):
        lines.append(format_coin_list_item(coin, scores.get(coin.id), i))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=coin_list_kb(coins, page, "new"),
        parse_mode="HTML",
    )
    await callback.answer()
