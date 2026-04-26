from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

import config
from utils.rate_limiter import RateLimiter

log = logging.getLogger(__name__)

_limiter = RateLimiter(calls_per_second=0.5)


async def check_repo_activity(
    session: aiohttp.ClientSession, repo_url: str
) -> tuple[bool, datetime | None]:
    if not repo_url:
        return False, None

    owner_repo = _extract_owner_repo(repo_url)
    if not owner_repo:
        return False, None

    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.GITHUB_API_BASE}/repos/{owner_repo}/commits",
            params={"per_page": "1"},
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return False, None
            data = await resp.json()
            if not data:
                return True, None
            commit_date_str = data[0].get("commit", {}).get("committer", {}).get("date", "")
            if commit_date_str:
                last_commit = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                return True, last_commit.replace(tzinfo=None)
            return True, None
    except Exception:
        log.debug("GitHub check failed for %s", repo_url, exc_info=True)
        return False, None


async def get_repo_created_at(
    session: aiohttp.ClientSession, repo_url: str
) -> datetime | None:
    owner_repo = _extract_owner_repo(repo_url)
    if not owner_repo:
        return None

    await _limiter.acquire()
    try:
        async with session.get(
            f"{config.GITHUB_API_BASE}/repos/{owner_repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            created_at = data.get("created_at", "")
            if created_at:
                return datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            return None
    except Exception:
        log.debug("GitHub repo info failed for %s", repo_url, exc_info=True)
        return None


async def search_repo(
    session: aiohttp.ClientSession, coin_name: str, coin_tag: str
) -> str:
    await _limiter.acquire()
    try:
        query = f"{coin_name} {coin_tag} cryptocurrency mining"
        async with session.get(
            f"{config.GITHUB_API_BASE}/search/repositories",
            params={"q": query, "per_page": "3", "sort": "updated"},
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return ""
            data = await resp.json()
            items = data.get("items", [])
            if not items:
                return ""
            best = items[0]
            return best.get("html_url", "")
    except Exception:
        log.debug("GitHub search failed for %s", coin_name, exc_info=True)
        return ""


def _extract_owner_repo(url: str) -> str:
    url = url.rstrip("/")
    if "github.com/" in url:
        parts = url.split("github.com/")[1].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    return ""
