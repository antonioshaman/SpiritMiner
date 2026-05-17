from __future__ import annotations

from datetime import datetime
from html import escape as _esc

from models.coin import Coin
from models.score import ScoreBreakdown, ExitSignal
from models.token import Token, TokenScoreBreakdown, SUPPORTED_CHAINS, chain_explorer_url


def format_price(value: float) -> str:
    if value >= 1000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:.4f}"
    if value >= 0.01:
        return f"${value:.6f}"
    return f"${value:.8f}"


def format_coin_card(coin: Coin, score: ScoreBreakdown | None = None, sentiment: dict | None = None) -> str:
    age = ""
    if coin.genesis_date:
        days = (datetime.utcnow() - coin.genesis_date).days
        if days > 365:
            age = f"\n\U0001f4c5 Возраст: {days // 365} лет"
        else:
            age = f"\n\U0001f4c5 Возраст: {days} дн."
    elif coin.first_seen:
        days = (datetime.utcnow() - coin.first_seen).days
        age = f"\n\U0001f4c5 В базе: {days} дн."

    price = ""
    if coin.exchange_rate_usd:
        price = format_price(coin.exchange_rate_usd)
    elif coin.exchange_rate_btc:
        price = f"{coin.exchange_rate_btc:.8f} BTC"

    lines = [
        f"<b>{_esc(coin.name)}</b> ({_esc(coin.tag)})",
        f"⚙️ Алгоритм: {_esc(coin.algorithm)}",
    ]
    if price:
        lines.append(f"\U0001f4b0 Цена: {price}")
    if coin.volume_24h:
        lines.append(f"\U0001f4ca Объём 24ч: ${coin.volume_24h:,.0f}")
    lines.append(f"⛏️ Сложность: {_fmt_number(coin.difficulty)}")
    if coin.nethash:
        lines.append(f"\U0001f310 Nethash: {_fmt_hashrate(coin.nethash)}")
    if coin.pool_count:
        lines.append(f"\U0001f3ca Пулы: {coin.pool_count}")
    if coin.exchange_count:
        lines.append(f"\U0001f4b1 Биржи: {coin.exchange_count}")
    if coin.has_community and coin.community_urls:
        lines.append("\U0001f4e3 Соцсети: " + " | ".join(
            f'<a href="{_esc(u)}">{_social_name(u)}</a>' for u in coin.community_urls[:3]
        ))
    if coin.github_url:
        lines.append(f"\U0001f4bb <a href=\"{_esc(coin.github_url)}\">GitHub</a>")
    if age:
        lines.append(age.strip())

    if score:
        lines.append("")
        lines.append(f"{score.signal_emoji} <b>{score.signal_text}</b> — {score.total}/100")

    if sentiment and sentiment.get("total", 0) > 0:
        total = sentiment["total"]
        bull = sentiment.get("bullish", 0)
        bull_pct = bull * 100 // total
        lines.append(f"\U0001f4ca Sentiment: {bull_pct}% bullish ({total} голосов)")

    return "\n".join(lines)


def format_pool_details(pools: list[dict]) -> str:
    if not pools:
        return ""
    lines = ["\n<b>⛏️ Пулы (MiningPoolStats):</b>"]
    for p in pools[:5]:
        name = p.get("pool_name") or p.get("name", "?")
        hr = p.get("hashrate", 0)
        workers = p.get("workers", 0)
        parts = [f"• {name}"]
        if hr:
            parts.append(f" — {_fmt_hashrate(hr)}")
        if workers:
            parts.append(f" ({workers} workers)")
        lines.append("".join(parts))
    if len(pools) > 5:
        lines.append(f"  ...и ещё {len(pools) - 5}")
    return "\n".join(lines)


def format_score_breakdown(s: ScoreBreakdown) -> str:
    parts = []
    if s.age_score:
        parts.append(f"+{s.age_score} новизна")
    if s.explorer_score:
        parts.append(f"+{s.explorer_score} explorer")
    if s.pool_score:
        parts.append(f"+{s.pool_score} пулы")
    if s.github_score:
        parts.append(f"+{s.github_score} GitHub")
    if s.community_score:
        parts.append(f"+{s.community_score} комьюнити")
    if s.exchange_score:
        parts.append(f"+{s.exchange_score} биржи")
    if s.difficulty_score:
        parts.append(f"+{s.difficulty_score} низкая сложность")
    if s.tokenomics_score:
        parts.append(f"+{s.tokenomics_score} токеномика")
    if s.penalty_premine:
        parts.append(f"{s.penalty_premine} премайн")
    if s.penalty_no_explorer:
        parts.append(f"{s.penalty_no_explorer} нет explorer")
    if s.penalty_no_liquidity:
        parts.append(f"{s.penalty_no_liquidity} нет ликвидности")
    if s.penalty_anon_fork:
        parts.append(f"{s.penalty_anon_fork} анон-форк")

    header = f"{s.signal_emoji} <b>Скоринг: {s.total}/100 — {s.signal_text}</b>\n"
    return header + "\n".join(parts)


def format_exit_signals(signals: list[ExitSignal]) -> str:
    if not signals:
        return "✅ Активных сигналов выхода нет"
    lines = ["<b>\U0001f6a8 Сигналы выхода:</b>", ""]
    for sig in signals:
        lines.append(f"{sig.emoji} <b>{sig.signal_type}</b>: {sig.message}")
    return "\n".join(lines)


def format_entry_strategy(coin: Coin, score: ScoreBreakdown | None) -> str:
    lines = [f"<b>\U0001f4cb Стратегия входа: {_esc(coin.name)} ({_esc(coin.tag)})</b>", ""]

    if score:
        lines.append(f"{score.signal_emoji} Скоринг: {score.total}/100")
        lines.append("")

    if score and score.total >= 60:
        lines.append("\U0001f7e2 <b>Рекомендация: Можно пробовать</b>")
        lines.append("⏰ Вход: майнить 12–24 часа")
        lines.append("\U0001f4b8 Фиксация: продать 50–70% при первом листинге")
        lines.append("\U0001f4e6 Холд: оставить 30–50%")
    elif score and score.total >= 35:
        lines.append("\U0001f7e1 <b>Рекомендация: Только тестовым объёмом</b>")
        lines.append("⏰ Вход: тестовые 6 часов")
        lines.append("\U0001f4b8 Фиксация: продать 70% сразу")
        lines.append("\U0001f4e6 Холд: максимум 30%")
    else:
        lines.append("\U0001f534 <b>Рекомендация: Не лезть</b>")
        lines.append("Слишком высокий риск для входа")

    lines.append("")
    lines.append("<b>Условия выхода:</b>")
    lines.append("• Сложность выросла x3+")
    lines.append("• Объём торгов не появился")
    lines.append("• Цена просела при росте сложности")
    lines.append("• Пул нестабилен / умер")
    return "\n".join(lines)


def format_coin_list_item(coin: Coin, score: ScoreBreakdown | None, idx: int) -> str:
    signal = score.signal_emoji if score else "❓"
    total = f"{score.total}/100" if score else "—"
    return f"{idx}. {signal} <b>{_esc(coin.tag)}</b> ({_esc(coin.name)}) — {total}"


def _social_name(url: str) -> str:
    if "twitter.com" in url or "x.com" in url:
        return "Twitter"
    if "reddit.com" in url:
        return "Reddit"
    if "t.me" in url:
        return "Telegram"
    if "discord" in url:
        return "Discord"
    return "Link"


def _fmt_number(n: float) -> str:
    if n >= 1e12:
        return f"{n / 1e12:.2f}T"
    if n >= 1e9:
        return f"{n / 1e9:.2f}G"
    if n >= 1e6:
        return f"{n / 1e6:.2f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}K"
    return f"{n:.2f}"


def _short_addr(addr: str) -> str:
    if len(addr) <= 12:
        return addr
    return f"{addr[:6]}…{addr[-4:]}"


def _chain_label(chain: str) -> str:
    labels = {
        "ethereum": "ETH", "bsc": "BSC", "base": "Base", "arbitrum": "Arb",
        "polygon": "Polygon", "optimism": "OP", "avalanche": "AVAX",
        "solana": "SOL", "ton": "TON",
    }
    return labels.get(chain, chain.upper())


def format_token_card(
    token: Token, score: TokenScoreBreakdown | None = None
) -> str:
    explorer = chain_explorer_url(token.chain, token.address)
    addr_link = (
        f'<a href="{_esc(explorer)}">{_short_addr(token.address)}</a>'
        if explorer else _esc(_short_addr(token.address))
    )

    title_name = token.name or token.symbol or "Unknown"
    title_sym = f" ({_esc(token.symbol)})" if token.symbol else ""
    lines = [
        f"<b>{_esc(title_name)}</b>{title_sym}",
        f"\U0001f517 {_chain_label(token.chain)} · {addr_link}",
    ]

    if token.price_usd:
        ch1h = ""
        if token.price_change_1h:
            arrow = "📈" if token.price_change_1h > 0 else "📉"
            ch1h = f" {arrow} {token.price_change_1h:+.1f}% 1ч"
        ch24 = ""
        if token.price_change_24h:
            arrow = "📈" if token.price_change_24h > 0 else "📉"
            ch24 = f" {arrow} {token.price_change_24h:+.1f}% 24ч"
        lines.append(f"\U0001f4b0 {format_price(token.price_usd)}{ch1h}{ch24}")

    if token.liquidity_usd:
        lines.append(f"\U0001f4a7 Ликвидность: ${_fmt_number(token.liquidity_usd)}")
    if token.volume_24h:
        lines.append(f"\U0001f4ca Объём 24ч: ${_fmt_number(token.volume_24h)}")
    if token.fdv:
        lines.append(f"\U0001f3db FDV: ${_fmt_number(token.fdv)}")
    if token.holder_count:
        lines.append(f"\U0001f465 Холдеров: {_fmt_number(token.holder_count)}")
    if token.pair_created_at:
        days = token.age_days
        lines.append(f"\U0001f4c5 Возраст пары: {days} дн.")
    if token.dex:
        lines.append(f"\U0001f504 DEX: {_esc(token.dex)}")

    sec_lines = []
    if token.is_honeypot:
        sec_lines.append("\U0001f6a8 <b>HONEYPOT</b>")
    if token.audit_coverage == "full":
        sec_lines.append("✅ Верифицирован" if token.is_verified else "⚠️ Не верифицирован")
    elif token.audit_coverage == "limited":
        sec_lines.append("\U0001f6e1 Аудит: ограниченный")
    else:
        sec_lines.append("❓ Аудит недоступен")

    if token.top10_concentration:
        emoji = "🔴" if token.top10_concentration > 50 else (
            "🟡" if token.top10_concentration > 30 else "🟢"
        )
        sec_lines.append(f"{emoji} Top10: {token.top10_concentration:.0f}%")
    if token.lp_locked_pct and token.audit_coverage == "full":
        emoji = "🟢" if token.lp_locked_pct >= 50 else "🟡" if token.lp_locked_pct >= 20 else "🔴"
        sec_lines.append(f"{emoji} LP locked: {token.lp_locked_pct:.0f}%")
    if token.is_mintable:
        sec_lines.append("⚠️ Mintable")
    if token.is_proxy:
        sec_lines.append("⚠️ Proxy-контракт")
    if token.can_take_back_ownership or token.hidden_owner:
        sec_lines.append("🚨 Owner risk")
    for flag in token.risk_flags[:4]:
        sec_lines.append(f"⚠️ {_esc(flag)}")

    if sec_lines:
        lines.append("")
        lines.extend(sec_lines)

    if score:
        lines.append("")
        lines.append(f"{score.signal_emoji} <b>{score.signal_text}</b> — {score.total}/100")

    return "\n".join(lines)


def format_token_score_breakdown(s: TokenScoreBreakdown) -> str:
    parts = []
    if s.liquidity_score:
        parts.append(f"+{s.liquidity_score} ликвидность")
    if s.age_score:
        parts.append(f"+{s.age_score} возраст")
    if s.holders_score:
        parts.append(f"+{s.holders_score} холдеры")
    if s.volume_score:
        parts.append(f"+{s.volume_score} объём")
    if s.security_score:
        parts.append(f"+{s.security_score} безопасность")
    if s.penalty_honeypot:
        parts.append(f"{s.penalty_honeypot} honeypot")
    if s.penalty_unverified:
        parts.append(f"{s.penalty_unverified} не верифицирован")
    if s.penalty_concentration:
        parts.append(f"{s.penalty_concentration} концентрация")
    if s.penalty_lp_unlocked:
        parts.append(f"{s.penalty_lp_unlocked} LP не залочен")
    if s.penalty_mintable:
        parts.append(f"{s.penalty_mintable} mintable")
    if s.penalty_proxy:
        parts.append(f"{s.penalty_proxy} proxy")
    if s.penalty_owner_risk:
        parts.append(f"{s.penalty_owner_risk} owner risk")

    header = f"{s.signal_emoji} <b>Скоринг: {s.total}/100 — {s.signal_text}</b>\n"
    return header + "\n".join(parts)


def _fmt_hashrate(h: float) -> str:
    if h >= 1e18:
        return f"{h / 1e18:.2f} EH/s"
    if h >= 1e15:
        return f"{h / 1e15:.2f} PH/s"
    if h >= 1e12:
        return f"{h / 1e12:.2f} TH/s"
    if h >= 1e9:
        return f"{h / 1e9:.2f} GH/s"
    if h >= 1e6:
        return f"{h / 1e6:.2f} MH/s"
    if h >= 1e3:
        return f"{h / 1e3:.2f} KH/s"
    return f"{h:.0f} H/s"
