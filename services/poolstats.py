from __future__ import annotations

import logging
import re

import aiohttp
from bs4 import BeautifulSoup

import config
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.3)


async def _fetch_page(session: aiohttp.ClientSession, coin_tag: str) -> str | None:
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
                return None
            return await resp.text()
    except Exception:
        log.debug("MiningPoolStats fetch failed for %s", coin_tag, exc_info=True)
        return None


def _parse_pools(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    pools: list[dict] = []

    rows = soup.select("table.table tbody tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        name_el = cells[0]
        link = name_el.find("a")
        pool = {
            "name": (link.get_text(strip=True) if link else name_el.get_text(strip=True)),
            "url": link["href"] if link and link.get("href") else "",
            "hashrate": 0.0,
            "workers": 0,
        }
        for i, cell in enumerate(cells[1:], 1):
            text = cell.get_text(strip=True).lower()
            if "h/s" in text:
                pool["hashrate"] = _parse_hashrate(text)
            elif text.isdigit():
                pool["workers"] = int(text)
        pools.append(pool)

    if not pools:
        cards = soup.select(".pool-card, .pool-row, [class*='pool']")
        for card in cards:
            name = card.get_text(strip=True)[:50]
            if name:
                pools.append({"name": name, "url": "", "hashrate": 0, "workers": 0})

    return pools


def _parse_hashrate(text: str) -> float:
    text = text.strip().lower().replace(",", "")
    multipliers = {"eh/s": 1e18, "ph/s": 1e15, "th/s": 1e12, "gh/s": 1e9, "mh/s": 1e6, "kh/s": 1e3, "h/s": 1}
    for suffix, mult in multipliers.items():
        if suffix in text:
            num_str = text.replace(suffix, "").strip()
            try:
                return float(num_str) * mult
            except ValueError:
                return 0
    m = re.search(r"[\d.]+", text)
    return float(m.group()) if m else 0


async def get_pool_count(
    session: aiohttp.ClientSession, coin_tag: str
) -> int:
    html = await _fetch_page(session, coin_tag)
    if not html:
        return 0
    pools = _parse_pools(html)
    return len(pools)


async def get_pool_details(
    session: aiohttp.ClientSession, coin_tag: str
) -> list[dict]:
    html = await _fetch_page(session, coin_tag)
    if not html:
        return []
    return _parse_pools(html)


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
