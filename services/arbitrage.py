"""Read-only, amount-specific TON -> Ethereum -> TON cycle evaluation.

No private keys or transaction submission. Missing legs fail closed.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import escape

import aiohttp
import config

log = logging.getLogger(__name__)
D = Decimal
WRAPPED = '0x582d872a1b094fc48f5de31d3b73f2d9be47def1'
USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
QUOTER = '0x61ffe014ba17989e743c5f6cb21bf9697530b21e'
TIMEOUT = aiohttp.ClientTimeout(total=20)


def number(value, *, positive=False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError('boolean is not an amount')
    try:
        result = D(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError('invalid amount') from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('invalid amount')
    return result


@dataclass(frozen=True)
class Leg:
    amount_in: Decimal
    amount_out: Decimal
    external_cost_usdt: Decimal
    source: str
    timestamp: float
    evidence: str
    expires_at: float = float("inf")


def validate_leg(data: dict, amount: Decimal, asset_in: str, asset_out: str,
                 now: float) -> Leg:
    """Provider must quote net output and separately priced external gas costs."""
    if not isinstance(data, dict):
        raise ValueError('provider response must be an object')
    if data.get('executable') is not True:
        raise ValueError('route unavailable or indicative quote')
    if data.get('asset_in') != asset_in or data.get('asset_out') != asset_out:
        raise ValueError('wrong asset or network')
    quoted_in = number(data.get('amount_in'), positive=True)
    if quoted_in != amount:
        raise ValueError('quote is for a different trade size')
    stamp = float(number(data.get('timestamp'), positive=True))
    if not -5 <= now - stamp <= config.ARB_MAX_QUOTE_AGE_SECONDS:
        raise ValueError('stale or future quote')
    if float(number(data.get('expires_at'), positive=True)) <= now:
        raise ValueError('expired quote')
    source, evidence = data.get('source'), data.get('evidence')
    if not isinstance(source, str) or not source.strip() or not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('missing source or route evidence')
    return Leg(quoted_in, number(data.get('amount_out'), positive=True),
               number(data.get('external_cost_usdt')), source, stamp, evidence,
               float(number(data.get('expires_at'), positive=True)))


async def provider_leg(session, url: str, amount: Decimal,
                       asset_in: str, asset_out: str) -> Leg:
    if not url:
        raise ValueError(f'нет провайдера {asset_in} → {asset_out}')
    async with session.get(url, params={'amount_in': str(amount),
                           'asset_in': asset_in, 'asset_out': asset_out},
                           timeout=TIMEOUT) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return validate_leg(data, amount, asset_in, asset_out, time.time())


async def rpc(session, method: str, params: list):
    if not config.ARB_ETH_RPC_URL:
        raise ValueError('не настроен Ethereum RPC')
    async with session.post(config.ARB_ETH_RPC_URL,
                            json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params},
                            timeout=TIMEOUT) as resp:
        resp.raise_for_status()
        data = await resp.json()
    if not isinstance(data, dict) or data.get('error') or 'result' not in data:
        raise ValueError(f'RPC {method} failed')
    return data['result']


async def dex_sell(session, amount: Decimal) -> Leg:
    """QuoterV2 eth_call at a pinned block, TONCOIN -> WETH -> USDT.

    Fees and price impact are included in amountOut. Gas is deliberately supplied
    by an execution-specific cost provider (approvals, swap, transfers, claim).
    """
    stamp = time.time()
    if int(await rpc(session, 'eth_chainId', []), 16) != 1:
        raise ValueError('RPC is not Ethereum mainnet')
    block = await rpc(session, 'eth_blockNumber', [])
    raw_block = await rpc(session, 'eth_getBlockByNumber', [block, False])
    if not raw_block or not -5 <= time.time() - int(raw_block['timestamp'], 16) <= config.ARB_MAX_QUOTE_AGE_SECONDS:
        raise ValueError('Ethereum node has a stale block')
    decimals = int(await rpc(session, 'eth_call', [{'to': WRAPPED, 'data': '0x313ce567'}, block]), 16)
    if decimals > 36:
        raise ValueError('unexpected token decimals')
    units = amount * (D(10) ** decimals)
    if units != units.to_integral_value():
        raise ValueError('trade amount has too many decimals')
    outputs = []
    for fee in (500, 3000, 10000):
        path = WRAPPED[2:] + format(10000, '06x') + WETH[2:] + format(fee, '06x') + USDT[2:]
        # ABI quoteExactInput(bytes,uint256), selector cdca1753.
        length = len(path) // 2
        payload = '0xcdca1753' + format(64, '064x') + format(int(units), '064x')
        payload += format(length, '064x') + path.ljust(((length + 31) // 32) * 64, '0')
        try:
            result = await rpc(session, 'eth_call', [{'to': QUOTER, 'data': payload}, block])
            output = D(int(result[2:66], 16)) / D(10) ** 6
            if output > 0:
                outputs.append((output, fee))
        except (ValueError, aiohttp.ClientError):
            continue
    if not outputs:
        raise ValueError('нет котировки Uniswap для этого объёма')
    output, fee = max(outputs)
    return Leg(amount, output, D(0), f'Uniswap v3 1%/{fee / 10000:g}%', stamp,
               f'Ethereum block {block}; QuoterV2 {QUOTER}')


@dataclass(frozen=True)
class Report:
    start: Decimal
    status: str
    reason: str
    final: Decimal | None = None
    net_pct: Decimal | None = None
    legs: tuple[Leg, ...] = ()


def evaluate(start: Decimal, legs: tuple[Leg, ...], now: float) -> Report:
    bridge, sell, settlement, buy = legs
    if bridge.amount_in != start or sell.amount_in != bridge.amount_out or settlement.amount_in != sell.amount_out or buy.amount_in != settlement.amount_out:
        raise ValueError('cycle amounts do not connect')
    if any(not -5 <= now - x.timestamp <= config.ARB_MAX_QUOTE_AGE_SECONDS or x.expires_at <= now for x in legs):
        raise ValueError('cycle quotes became stale')
    # Convert all external gas/approval/claim costs to native units at the actual
    # buy quote's average price. This is an economic PnL, not spendable balance.
    costs = sum((x.external_cost_usdt for x in legs), D(0))
    if costs <= 0:
        raise ValueError('missing external gas and execution cost budget')
    final = buy.amount_out - costs * buy.amount_out / buy.amount_in
    reserve = number(config.ARB_SAFETY_BPS)
    if reserve >= 10000:
        raise ValueError('invalid safety reserve')
    final *= D(1) - reserve / D(10000)
    net = (final / start - D(1)) * D(100)
    status = 'NO_PROFIT'
    threshold = number(config.ARB_MIN_NET_PCT, positive=True)
    if net >= threshold:
        status = 'EXTREME' if net >= 15 else 'STRONG' if net >= 8 else 'PROFIT'
    return Report(start, status, 'Оценка после внешних расходов и резерва; цены не зафиксированы на время моста.', final, net, legs)


async def scan_amount(session, start: Decimal) -> Report:
    legs = []
    try:
        bridge = await provider_leg(session, config.ARB_BRIDGE_QUOTE_URL, start,
                                    'ton:native', 'ethereum:' + WRAPPED)
        legs.append(bridge)
        sell = await dex_sell(session, bridge.amount_out)
        legs.append(sell)
        settlement = await provider_leg(session, config.ARB_SETTLEMENT_QUOTE_URL, sell.amount_out,
                                        'ethereum:' + USDT, 'wallet:USDT')
        legs.append(settlement)
        buy = await provider_leg(session, config.ARB_NATIVE_QUOTE_URL, settlement.amount_out,
                                 'wallet:USDT', 'ton:native')
        legs.append(buy)
        return evaluate(start, tuple(legs), time.time())
    except (ValueError, aiohttp.ClientError, asyncio.TimeoutError, KeyError, TypeError, OverflowError):
        log.warning('Arbitrage quote unavailable for %s at leg %s', start, len(legs) + 1)
        # Do not expose URLs, API credentials, or raw provider exceptions in Telegram.
        return Report(start, 'BLOCKED', f'Не подтверждён этап {len(legs) + 1}/4. См. /arb_help.', legs=tuple(legs))


def format_report(report: Report) -> str:
    text = f'<b>TON/GRAM → ETH → TON/GRAM: {report.status}</b>\nОбъём: {report.start} native\n'
    if report.final is not None:
        text += f'Итог с резервом: {report.final:.4f} native\nЧистая оценка: {report.net_pct:+.2f}%\n'
    for label, leg in zip(('Мост: ERC20', 'DEX: USDT', 'Перевод: USDT', 'Покупка/вывод: native'), report.legs):
        text += f'{label}: {leg.amount_out:.6f} ({escape(leg.source[:100])})\n'
    return text + '\n' + escape(report.reason) + '\nРежим: наблюдение, сделки не отправляются.'


async def scan() -> list[Report]:
    async with aiohttp.ClientSession() as session:
        return [await scan_amount(session, number(size, positive=True)) for size in config.ARB_TRADE_SIZES]


async def poll_arbitrage(bot) -> None:
    from db.queries import SubscriberQueries, TokenWatchlistQueries
    for report in await scan():
        if report.status not in {'PROFIT', 'STRONG', 'EXTREME'}:
            log.info('Arbitrage %s: %s', report.start, report.status)
            continue
        key = f'arb_cycle_{report.start}'  # Same cooldown across changes of signal level.
        for sub in await SubscriberQueries.get_all_subscribers():
            user_id = sub['user_id']
            if await TokenWatchlistQueries.was_alert_sent(user_id, 'ethereum', WRAPPED, key):
                continue
            try:
                await bot.send_message(user_id, format_report(report), parse_mode='HTML')
                await TokenWatchlistQueries.mark_alert_sent(user_id, 'ethereum', WRAPPED, key)
            except Exception:
                log.warning('Arbitrage delivery failed for %s', user_id)
