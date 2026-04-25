from __future__ import annotations

import logging
import re

import aiohttp
from bs4 import BeautifulSoup

import config
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.3)


async def get_pool_count(
    session: aiohttp.ClientSession, coin_tag: str
) -> int:
    await _limiter.acquire()
    tag_lower = coin_tag.lower()
    url = f"{config.MININGPOOLSTATS_BASE}/miners/{tag_lower}"

    try:
        async with session.get(
            url,
            headers={"User-Agent": "SpiritMiner/1.0"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return 0
            html = await resp.text()
    except Exception:
        log.debug("MiningPoolStats fetch failed for %s", coin_tag, exc_info=True)
        return 0

    try:
        soup = BeautifulSoup(html, "html.parser")
        pool_rows = soup.select("table.table tbody tr")
        if pool_rows:
            return len(pool_rows)

        pool_cards = soup.select(".pool-card, .pool-row, [class*='pool']")
        if pool_cards:
            return len(pool_cards)

        text = soup.get_text()
        match = re.search(r"(\d+)\s*(?:pools?|пулов)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        log.debug("MiningPoolStats parse failed for %s", coin_tag, exc_info=True)

    return 0


async def check_explorer(
    session: aiohttp.ClientSession, coin_tag: str, explorer_url: str = ""
) -> tuple[bool, str]:
    if explorer_url:
        try:
            async with session.head(
                explorer_url,
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=True,
            ) as resp:
                if resp.status < 400:
                    return True, explorer_url
        except Exception:
            pass

    common_explorers = [
        f"https://explorer.{coin_tag.lower()}.org",
        f"https://{coin_tag.lower()}.explorer.org",
        f"https://blockexplorer.{coin_tag.lower()}.org",
    ]

    for url in common_explorers:
        try:
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True,
            ) as resp:
                if resp.status < 400:
                    return True, url
        except Exception:
            continue

    return False, ""
