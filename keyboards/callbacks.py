from aiogram.filters.callback_data import CallbackData


class MenuAction(CallbackData, prefix="menu"):
    action: str


class CoinAction(CallbackData, prefix="coin"):
    coin_id: int
    action: str  # detail, score, entry, exit


class PageAction(CallbackData, prefix="page"):
    list_type: str
    page: int


class VoteAction(CallbackData, prefix="vote"):
    coin_id: int
    vote: str  # bullish, watching, bearish


class TradeAction(CallbackData, prefix="trade"):
    coin_id: int
    action: str  # enter, exit


class TokenAction(CallbackData, prefix="tok"):
    # Token addresses are too long for callback_data (64-byte limit).
    # We store a short hash and look up the (chain, address) from a request-scoped cache.
    key: str   # short hash, see TokenLookupCache
    action: str  # detail, score, watch, unwatch, refresh, pick


class TokenChainPick(CallbackData, prefix="tokc"):
    key: str   # address hash
    chain: str
