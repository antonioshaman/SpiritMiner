from __future__ import annotations

import logging
from datetime import datetime

import aiohttp

import config
from models.coin import Coin
from models.score import ScoreBreakdown, ExitSignal
from db.queries import CoinQueries
from . import github_checker, market, poolstats

log = logging.getLogger(__name__)


async def compute_score(
    session: aiohttp.ClientSession, coin: Coin
) -> ScoreBreakdown:
    s = ScoreBreakdown(coin_id=coin.id, scored_at=datetime.utcnow())

    now = datetime.utcnow()

    # +20: coin age < 7 days (use genesis_date if known, else first_seen)
    coin_birth = coin.genesis_date or coin.first_seen
    if coin_birth:
        age_days = (now - coin_birth).days
        if age_days <= config.NEW_COIN_AGE_DAYS:
            s.age_score = 20
        elif age_days <= 30:
            s.age_score = 10

    # +15: working explorer
    if coin.has_explorer:
        s.explorer_score = 15
    else:
        has_exp, url = await poolstats.check_explorer(session, coin.tag, coin.explorer_url)
        if has_exp:
            s.explorer_score = 15
            coin.has_explorer = True
            coin.explorer_url = url

    # +15: 2+ pools
    if coin.pool_count >= 2:
        s.pool_score = 15
    else:
        pool_count = await poolstats.get_pool_count(session, coin.tag)
        if pool_count >= 2:
            s.pool_score = 15
            coin.pool_count = pool_count

    # +15: GitHub with fresh commits
    if coin.github_url:
        active, last_commit = await github_checker.check_repo_activity(session, coin.github_url)
        if active and last_commit:
            days_since = (now - last_commit).days
            if days_since <= config.FRESH_COMMIT_DAYS:
                s.github_score = 15
            coin.github_last_commit = last_commit
    else:
        repo_url = await github_checker.search_repo(session, coin.name, coin.tag)
        if repo_url:
            coin.github_url = repo_url
            active, last_commit = await github_checker.check_repo_activity(session, repo_url)
            if active and last_commit:
                days_since = (now - last_commit).days
                if days_since <= config.FRESH_COMMIT_DAYS:
                    s.github_score = 15
                coin.github_last_commit = last_commit

    # +10: community activity
    if coin.has_community:
        s.community_score = 10

    # +10: at least one exchange listing
    if coin.exchange_count >= 1:
        s.exchange_score = 10

    # +10: difficulty still low (compare to 7d average)
    if coin.difficulty_7d and coin.difficulty:
        if coin.difficulty <= coin.difficulty_7d * 1.5:
            s.difficulty_score = 10
    elif coin.difficulty_24h and coin.difficulty:
        if coin.difficulty <= coin.difficulty_24h * 2:
            s.difficulty_score = 10
    else:
        s.difficulty_score = 10

    # +5: tokenomics (heuristic)
    if coin.block_reward > 0 and coin.block_time > 0:
        s.tokenomics_score = 5

    # Penalties
    if coin.has_premine:
        s.penalty_premine = -20

    if not coin.has_explorer and s.explorer_score == 0:
        s.penalty_no_explorer = -20

    if coin.volume_24h < config.LOW_VOLUME_USD and coin.exchange_count == 0:
        s.penalty_no_liquidity = -30

    if (
        not coin.github_url
        and not coin.has_community
        and coin.algorithm
    ):
        s.penalty_anon_fork = -40

    s.compute_total()
    return s


async def enrich_from_coingecko(
    session: aiohttp.ClientSession, coin: Coin
) -> Coin:
    if not coin.coingecko_id:
        cg_id = await market.find_coingecko_id(session, coin.tag, coin.name)
        if cg_id:
            coin.coingecko_id = cg_id

    if coin.coingecko_id:
        data = await market.get_market_data(session, coin.coingecko_id)
        if data:
            price_usd = market.extract_price_usd(data)
            price_btc = market.extract_price_btc(data)
            if price_usd:
                coin.exchange_rate_usd = price_usd
            if price_btc:
                coin.exchange_rate_btc = price_btc
            coin.exchange_count = max(coin.exchange_count, market.extract_exchange_count(data))
            vol = market.extract_volume(data)
            if vol > coin.volume_24h:
                coin.volume_24h = vol
            community_stats = market.extract_community_stats(data)
            if market.extract_community_active(data):
                coin.has_community = True
                urls = []
                if community_stats.get("twitter_url"):
                    urls.append(f"https://twitter.com/{community_stats['twitter_url']}")
                if community_stats.get("reddit_url"):
                    urls.append(community_stats["reddit_url"])
                if community_stats.get("telegram_url"):
                    urls.append(f"https://t.me/{community_stats['telegram_url']}")
                coin.community_urls = urls
            gh = market.extract_github_url(data)
            if gh and not coin.github_url:
                coin.github_url = gh
            if market.extract_has_premine(data):
                coin.has_premine = True
            gd = market.extract_genesis_date(data)
            if gd and not coin.genesis_date:
                coin.genesis_date = gd

    return coin


async def check_exit_signals(coin: Coin) -> list[ExitSignal]:
    signals: list[ExitSignal] = []
    now = datetime.utcnow()

    history = await CoinQueries.get_difficulty_history(coin.id, limit=72)

    if len(history) >= 2:
        oldest = history[-1]
        newest = history[0]

        old_diff = oldest.get("difficulty", 0)
        new_diff = newest.get("difficulty", 0)

        if old_diff and new_diff:
            ratio = new_diff / old_diff
            if ratio >= config.DIFF_CRITICAL_MULTIPLIER:
                signals.append(ExitSignal(
                    coin_id=coin.id,
                    signal_type="Сложность x5+",
                    severity="critical",
                    message=f"Сложность выросла в {ratio:.1f}x — окно закрывается",
                    detected_at=now,
                ))
            elif ratio >= config.DIFF_SPIKE_MULTIPLIER:
                signals.append(ExitSignal(
                    coin_id=coin.id,
                    signal_type="Сложность x3+",
                    severity="warning",
                    message=f"Сложность выросла в {ratio:.1f}x — готовься к выходу",
                    detected_at=now,
                ))

        old_price = oldest.get("exchange_rate_btc", 0)
        new_price = newest.get("exchange_rate_btc", 0)
        if old_price and new_price and new_diff and old_diff:
            if new_price < old_price * 0.7 and new_diff > old_diff * 1.5:
                signals.append(ExitSignal(
                    coin_id=coin.id,
                    signal_type="Цена vs Сложность",
                    severity="critical",
                    message="Цена падает при росте сложности — убыточный майнинг",
                    detected_at=now,
                ))

        old_vol = oldest.get("volume_24h", 0) or 0
        new_vol = newest.get("volume_24h", 0) or 0
        if new_vol < config.LOW_VOLUME_USD and old_vol < config.LOW_VOLUME_USD:
            signals.append(ExitSignal(
                coin_id=coin.id,
                signal_type="Нет объёма",
                severity="warning",
                message=f"Объём торгов ${new_vol:,.0f} — некуда продавать",
                detected_at=now,
            ))

    if coin.profitability < config.MIN_PROFITABILITY and coin.profitability > 0:
        signals.append(ExitSignal(
            coin_id=coin.id,
            signal_type="Низкая доходность",
            severity="warning",
            message=f"Profitability {coin.profitability}% — ниже порога",
            detected_at=now,
        ))

    if coin.pool_count == 0:
        signals.append(ExitSignal(
            coin_id=coin.id,
            signal_type="Нет пулов",
            severity="critical",
            message="Пулы не обнаружены — майнить некуда",
            detected_at=now,
        ))

    return signals
