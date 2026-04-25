from __future__ import annotations

from models.coin import Coin

PARTNER_POOLS = [
    {
        "name": "2Miners",
        "url": "https://2miners.com",
        "algorithms": ["Ethash", "KawPow", "Autolykos2", "ZelHash", "ProgPow"],
        "description": "Крупный мультиалго пул, PPLNS/SOLO",
        "fee": "1%",
    },
    {
        "name": "HeroMiners",
        "url": "https://herominers.com",
        "algorithms": ["RandomX", "KawPow", "Ethash", "Autolykos2", "kHeavyHash", "ZelHash"],
        "description": "Пул с поддержкой 70+ монет",
        "fee": "0.9%",
    },
    {
        "name": "WoolyPooly",
        "url": "https://woolypooly.com",
        "algorithms": ["Ethash", "KawPow", "Autolykos2", "kHeavyHash", "ZelHash", "vProgPow"],
        "description": "Дружелюбный пул для мелких майнеров",
        "fee": "0.9%",
    },
    {
        "name": "MiningPoolHub",
        "url": "https://miningpoolhub.com",
        "algorithms": ["Ethash", "Equihash", "Lyra2REv3", "X16R", "NeoScrypt"],
        "description": "Авто-свитч между монетами",
        "fee": "0.9%",
    },
    {
        "name": "Unmineable",
        "url": "https://unmineable.com",
        "algorithms": ["Ethash", "KawPow", "RandomX"],
        "description": "Майнинг любого токена через конверсию",
        "fee": "1%",
    },
]

PARTNER_EXCHANGES = [
{
        "name": "MEXC",
        "url": "https://www.mexc.com",
        "focus": "Раннее листинг мелких PoW-монет",
    },
    {
        "name": "XeggeX",
        "url": "https://xeggex.com",
        "focus": "Новые PoW-монеты, листинг за часы",
    },
    {
        "name": "NonKYC",
        "url": "https://nonkyc.io",
        "focus": "Без KYC, мелкие PoW-монеты",
    },
    {
        "name": "CoinEx",
        "url": "https://www.coinex.com",
        "focus": "Широкий выбор альткоинов",
    },
    {
        "name": "OKX",
        "url": "https://okx.com/join/37933329",
        "focus": "Топ-3 биржа, много торговых пар",
    },
    {
        "name": "Binance",
        "url": "https://www.binance.com/referral/earn-together/refer2earn-usdc/claim?hl=en&ref=GRO_28502_QF3F4&utm_source=referral_entrance",
        "focus": "Крупнейшая биржа, высокая ликвидность",
    },
]


def get_relevant_pools(coin: Coin) -> list[dict]:
    if not coin.algorithm:
        return PARTNER_POOLS[:3]
    return [p for p in PARTNER_POOLS if coin.algorithm in p["algorithms"]] or PARTNER_POOLS[:2]


def format_partners_overview() -> str:
    lines = ["\U0001f91d <b>Партнёры</b>\n"]

    lines.append("<b>⛏️ Пулы для майнинга:</b>\n")
    for p in PARTNER_POOLS:
        lines.append(
            f'• <a href="{p["url"]}">{p["name"]}</a> — {p["description"]} (fee {p["fee"]})'
        )

    lines.append("\n<b>\U0001f4b1 Биржи для продажи:</b>\n")
    for e in PARTNER_EXCHANGES:
        lines.append(f'• <a href="{e["url"]}">{e["name"]}</a> — {e["focus"]}')

    lines.append(
        "\n<i>Некоторые ссылки содержат реферальные коды.</i>"
    )
    return "\n".join(lines)


def format_coin_partners(coin: Coin) -> str:
    pools = get_relevant_pools(coin)
    lines = [f"\U0001f91d <b>Где майнить {coin.tag}:</b>\n"]

    if pools:
        for p in pools:
            lines.append(f'• <a href="{p["url"]}">{p["name"]}</a> — fee {p["fee"]}')
    else:
        lines.append("Подходящих партнёрских пулов не найдено.")

    lines.append(f"\n<b>Где продать {coin.tag}:</b>\n")
    for e in PARTNER_EXCHANGES[:3]:
        lines.append(f'• <a href="{e["url"]}">{e["name"]}</a> — {e["focus"]}')

    return "\n".join(lines)
