"""Compatibility entrypoint. Candle changes no longer trigger trade recommendations."""
from services.arbitrage import poll_arbitrage


async def poll_ton_candle_signal(bot):
    await poll_arbitrage(bot)
