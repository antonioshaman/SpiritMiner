from __future__ import annotations

import logging

import aiohttp

from db.queries import CoinQueries, PoolDetailQueries
from services.whattomine import fetch_all_coins
from services.scorer import compute_score, enrich_from_coingecko
from services.poolstats import get_pool_details

log = logging.getLogger(__name__)


async def scan_new_coins() -> None:
    log.info("Starting coin scan...")
    try:
        async with aiohttp.ClientSession() as session:
            coins = await fetch_all_coins(session)
            if not coins:
                log.warning("No coins returned from WhatToMine")
                return

            for coin in coins:
                existing = await CoinQueries.get_coin(coin.id)
                if existing:
                    coin.first_seen = existing.first_seen
                    coin.genesis_date = existing.genesis_date or coin.genesis_date
                    coin.github_url = existing.github_url or coin.github_url
                    coin.coingecko_id = existing.coingecko_id or coin.coingecko_id
                    coin.pool_count = max(existing.pool_count, coin.pool_count)
                    coin.exchange_count = max(existing.exchange_count, coin.exchange_count)
                    coin.has_explorer = existing.has_explorer or coin.has_explorer
                    coin.has_community = existing.has_community or coin.has_community
                    coin.has_premine = existing.has_premine or coin.has_premine

                await CoinQueries.upsert_coin(coin)

            log.info("Scan complete: %d coins processed", len(coins))
    except Exception:
        log.exception("Coin scan failed")


async def rescore_all() -> None:
    log.info("Starting rescore...")
    try:
        coins = await CoinQueries.list_all_coins()
        if not coins:
            log.info("No coins to rescore")
            return

        async with aiohttp.ClientSession() as session:
            for coin in coins:
                try:
                    coin = await enrich_from_coingecko(session, coin)
                    score = await compute_score(session, coin)
                    await CoinQueries.upsert_coin(coin)
                    await CoinQueries.save_score(score)
                    pools = await get_pool_details(session, coin.tag)
                    if pools:
                        await PoolDetailQueries.upsert_pools(coin.id, pools)
                except Exception:
                    log.debug("Rescore failed for %s", coin.tag, exc_info=True)

        log.info("Rescore complete: %d coins", len(coins))
    except Exception:
        log.exception("Rescore job failed")


async def record_difficulty_history() -> None:
    log.info("Recording difficulty history...")
    try:
        coins = await CoinQueries.list_all_coins()
        for coin in coins:
            if coin.difficulty > 0:
                await CoinQueries.record_difficulty(coin)
        log.info("Difficulty history recorded for %d coins", len(coins))
    except Exception:
        log.exception("Difficulty history recording failed")
