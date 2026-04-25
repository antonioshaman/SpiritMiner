from aiogram.filters.callback_data import CallbackData


class MenuAction(CallbackData, prefix="menu"):
    action: str


class CoinAction(CallbackData, prefix="coin"):
    coin_id: int
    action: str  # detail, score, entry, exit


class PageAction(CallbackData, prefix="page"):
    list_type: str
    page: int
