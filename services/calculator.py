from __future__ import annotations

import logging

import aiohttp

import config
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.5)

POPULAR_GPUS = [
    {"name": "RTX 4090", "algos": {"Ethash": 132, "KawPow": 62, "Autolykos2": 260, "kHeavyHash": 2000, "ZelHash": 65, "ProgPow": 34}},
    {"name": "RTX 4070 Ti", "algos": {"Ethash": 62, "KawPow": 32, "Autolykos2": 130, "kHeavyHash": 1200, "ZelHash": 38, "ProgPow": 20}},
    {"name": "RTX 3080", "algos": {"Ethash": 100, "KawPow": 48, "Autolykos2": 200, "kHeavyHash": 1400, "ZelHash": 56, "ProgPow": 28}},
    {"name": "RTX 3060 Ti", "algos": {"Ethash": 62, "KawPow": 30, "Autolykos2": 130, "kHeavyHash": 900, "ZelHash": 36, "ProgPow": 18}},
    {"name": "RX 7900 XTX", "algos": {"Ethash": 95, "KawPow": 44, "Autolykos2": 190, "kHeavyHash": 1100, "ZelHash": 48, "ProgPow": 26}},
    {"name": "RX 6800 XT", "algos": {"Ethash": 64, "KawPow": 30, "Autolykos2": 130, "kHeavyHash": 700, "ZelHash": 32, "ProgPow": 16}},
]

GPU_POWER = {
    "RTX 4090": 350,
    "RTX 4070 Ti": 285,
    "RTX 3080": 320,
    "RTX 3060 Ti": 200,
    "RX 7900 XTX": 355,
    "RX 6800 XT": 300,
}


def get_gpu_list() -> list[dict]:
    return POPULAR_GPUS


def get_gpu_by_name(name: str) -> dict | None:
    for gpu in POPULAR_GPUS:
        if gpu["name"].lower() == name.lower():
            return gpu
    return None


async def calculate_profitability(
    session: aiohttp.ClientSession,
    algorithm: str,
    hashrate_mhs: float,
    power_watts: int = 300,
    electricity_cost: float = 0.10,
) -> dict | None:
    await _limiter.acquire()
    try:
        async with session.post(
            f"{config.WTM_API_BASE}/calculate",
            headers={"Authorization": f"Token {config.WTM_API_KEY}"},
            json={
                "algorithm": algorithm,
                "hashrate": hashrate_mhs,
                "power": power_watts,
                "electricity_cost": electricity_cost,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    except Exception:
        log.debug("Calculate failed for %s", algorithm, exc_info=True)
        return None


def estimate_daily_revenue(
    coin_difficulty: float,
    coin_nethash: float,
    block_reward: float,
    block_time: float,
    hashrate: float,
    exchange_rate_usd: float,
) -> dict:
    if not coin_nethash or not block_time or not hashrate:
        return {"revenue_usd": 0, "coins_per_day": 0, "blocks_per_day": 0}

    blocks_per_day = 86400 / block_time if block_time > 0 else 0
    share = hashrate / coin_nethash if coin_nethash > 0 else 0
    coins_per_day = blocks_per_day * block_reward * share
    revenue_usd = coins_per_day * exchange_rate_usd

    return {
        "revenue_usd": revenue_usd,
        "coins_per_day": coins_per_day,
        "blocks_per_day": blocks_per_day,
        "share_pct": share * 100,
    }


def estimate_pnl(
    revenue_usd: float,
    power_watts: int,
    electricity_cost: float,
    hours: int = 24,
) -> dict:
    kwh = (power_watts * hours) / 1000
    cost = kwh * electricity_cost
    profit = revenue_usd - cost

    return {
        "revenue_usd": revenue_usd,
        "electricity_cost": cost,
        "profit_usd": profit,
        "kwh": kwh,
        "profitable": profit > 0,
    }
