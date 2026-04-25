from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .callbacks import MenuAction, CoinAction, PageAction, VoteAction, TradeAction

ITEMS_PER_PAGE = 10


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\U0001f195 Новые монеты", callback_data=MenuAction(action="new_coins").pack()),
            InlineKeyboardButton(text="\U0001f3c6 Топ скоринг", callback_data=MenuAction(action="top_scoring").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f50d Проверить", callback_data=MenuAction(action="check_coin").pack()),
            InlineKeyboardButton(text="\U0001f4c8 Вход", callback_data=MenuAction(action="calc_entry").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f6aa Выход", callback_data=MenuAction(action="exit_cond").pack()),
            InlineKeyboardButton(text="\U0001f4bb Железо", callback_data=MenuAction(action="hardware").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f3e2 Провайдеры", callback_data=MenuAction(action="provider").pack()),
            InlineKeyboardButton(text="\U0001f3c5 Spirit Rank", callback_data=MenuAction(action="spirit_rank").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f91d Партнёры", callback_data=MenuAction(action="partners").pack()),
            InlineKeyboardButton(text="\U0001f4ca Spirit Index", callback_data=MenuAction(action="spirit_index").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f514 Алерты", callback_data=MenuAction(action="subscribe").pack()),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data=MenuAction(action="about").pack()),
        ],
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
        [
            InlineKeyboardButton(text="\U0001f44d Bull", callback_data=VoteAction(coin_id=coin_id, vote="bullish").pack()),
            InlineKeyboardButton(text="\U0001f440 Watch", callback_data=VoteAction(coin_id=coin_id, vote="watching").pack()),
            InlineKeyboardButton(text="❌ Bear", callback_data=VoteAction(coin_id=coin_id, vote="bearish").pack()),
        ],
        [
            InlineKeyboardButton(text="⛏️ Зашёл", callback_data=TradeAction(coin_id=coin_id, action="enter").pack()),
            InlineKeyboardButton(text="\U0001f3c1 Вышел", callback_data=TradeAction(coin_id=coin_id, action="exit").pack()),
            InlineKeyboardButton(text="\U0001f440 Watch", callback_data=CoinAction(coin_id=coin_id, action="watch").pack()),
        ],
        [
            InlineKeyboardButton(text="\U0001f91d Партнёры", callback_data=CoinAction(coin_id=coin_id, action="partners").pack()),
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
