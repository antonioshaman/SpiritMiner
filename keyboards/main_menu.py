from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .callbacks import MenuAction, CoinAction, PageAction

ITEMS_PER_PAGE = 10


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="\U0001f195 Новые PoW-монеты",
            callback_data=MenuAction(action="new_coins").pack(),
        )],
        [InlineKeyboardButton(
            text="\U0001f3c6 Топ по скорингу",
            callback_data=MenuAction(action="top_scoring").pack(),
        )],
        [InlineKeyboardButton(
            text="\U0001f50d Проверить монету",
            callback_data=MenuAction(action="check_coin").pack(),
        )],
        [InlineKeyboardButton(
            text="\U0001f4c8 Рассчитать вход",
            callback_data=MenuAction(action="calc_entry").pack(),
        )],
        [InlineKeyboardButton(
            text="\U0001f6aa Условия выхода",
            callback_data=MenuAction(action="exit_cond").pack(),
        )],
        [InlineKeyboardButton(
            text="ℹ️ О боте",
            callback_data=MenuAction(action="about").pack(),
        )],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="◀️ Главное меню",
            callback_data=MenuAction(action="main").pack(),
        )],
    ])


def coin_actions_kb(coin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="\U0001f4ca Скоринг",
                callback_data=CoinAction(coin_id=coin_id, action="score").pack(),
            ),
            InlineKeyboardButton(
                text="\U0001f4c8 Вход",
                callback_data=CoinAction(coin_id=coin_id, action="entry").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="\U0001f6aa Выход",
                callback_data=CoinAction(coin_id=coin_id, action="exit").pack(),
            ),
            InlineKeyboardButton(
                text="\U0001f504 Обновить",
                callback_data=CoinAction(coin_id=coin_id, action="refresh").pack(),
            ),
        ],
        [InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=MenuAction(action="main").pack(),
        )],
    ])


def coin_list_kb(coins: list, page: int, list_type: str) -> InlineKeyboardMarkup:
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_coins = coins[start:end]

    buttons = []
    for coin_data in page_coins:
        if isinstance(coin_data, tuple):
            coin = coin_data[0]
        else:
            coin = coin_data
        buttons.append([InlineKeyboardButton(
            text=f"{coin.tag} — {coin.name}",
            callback_data=CoinAction(coin_id=coin.id, action="detail").pack(),
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️",
            callback_data=PageAction(list_type=list_type, page=page - 1).pack(),
        ))
    if end < len(coins):
        nav.append(InlineKeyboardButton(
            text="▶️",
            callback_data=PageAction(list_type=list_type, page=page + 1).pack(),
        ))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(
        text="◀️ Главное меню",
        callback_data=MenuAction(action="main").pack(),
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
