from __future__ import annotations

import logging
from html import escape as _esc

import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from db.queries import TokenQueries, TokenWatchlistQueries, PointsQueries
from keyboards.callbacks import TokenAction, TokenChainPick
from keyboards.main_menu import token_actions_kb, token_chain_pick_kb, back_to_menu_kb
from models.token import Token
from services import geckoterminal, dexscreener
from services.token_scorer import enrich_token, compute_score
from utils.address_detect import EVM_CANDIDATE_CHAINS
from utils.formatting import format_token_card, format_token_score_breakdown
from utils import token_cache

log = logging.getLogger(__name__)
router = Router()


async def _persist_and_show(message_or_cb, token: Token, user_id: int, edit: bool = False) -> None:
    score = compute_score(token)
    await TokenQueries.upsert_token(token)
    await TokenQueries.save_score(score)
    await TokenQueries.record_price(token.chain, token.address, token.price_usd, token.liquidity_usd)

    key = token_cache.put(token.chain, token.address)
    is_watching = await TokenWatchlistQueries.is_watching(user_id, token.chain, token.address)
    text = format_token_card(token, score)
    kb = token_actions_kb(key, is_watching=is_watching)

    if edit:
        await message_or_cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message_or_cb.answer(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)


async def handle_token_address(message: Message, family: str, address: str) -> None:
    """Called from check_coin.handle_coin_input when an address is detected."""
    user_id = message.from_user.id
    await PointsQueries.award(user_id, 1)

    async with aiohttp.ClientSession() as session:
        if family == "evm":
            status = await message.answer(
                f"\U0001f50d Ищу токен <code>{_esc(address)}</code> на EVM-сетях…",
                parse_mode="HTML",
            )
            tokens = await geckoterminal.find_token_multi_chain(session, address, EVM_CANDIDATE_CHAINS)
            if not tokens:
                ds_tokens = await dexscreener.fetch_token_pairs(session, address)
                tokens = [t for t in ds_tokens if t.chain in EVM_CANDIDATE_CHAINS]
            await status.delete()
            if not tokens:
                await message.answer(
                    f"❌ Адрес <code>{_esc(address)}</code> не найден ни на одной EVM-сети с торгуемой парой.\n\n"
                    f"Возможно, токен делистнут или без активной ликвидности.",
                    reply_markup=back_to_menu_kb(),
                    parse_mode="HTML",
                )
                return
            if len(tokens) == 1:
                t = tokens[0]
                t = await enrich_token(session, t)
                await _persist_and_show(message, t, user_id)
                return

            chains_by_liq = sorted(tokens, key=lambda t: t.liquidity_usd, reverse=True)
            key = token_cache.put("__multi__", address)
            lines = [
                f"\U0001f50e Адрес найден на {len(tokens)} сетях. Выберите:",
                "",
            ]
            for t in chains_by_liq:
                lines.append(
                    f"• <b>{t.chain.title()}</b> — "
                    f"${t.liquidity_usd:,.0f} liq, {t.symbol or 'unknown'}"
                )
            await message.answer(
                "\n".join(lines),
                reply_markup=token_chain_pick_kb(key, [t.chain for t in chains_by_liq]),
                parse_mode="HTML",
            )
            return

        if family == "solana":
            status = await message.answer("\U0001f50d Ищу токен в Solana…", parse_mode="HTML")
            t = await geckoterminal.fetch_token_on_chain(session, "solana", address)
            if not t:
                ds = await dexscreener.fetch_token_pairs(session, address)
                t = next((x for x in ds if x.chain == "solana"), None)
            await status.delete()
            if not t:
                await message.answer(
                    f"❌ Solana-токен <code>{_esc(address)}</code> не найден или нет торгуемой пары.",
                    reply_markup=back_to_menu_kb(),
                    parse_mode="HTML",
                )
                return
            t = await enrich_token(session, t)
            await _persist_and_show(message, t, user_id)
            return

        if family == "ton":
            status = await message.answer("\U0001f50d Ищу jetton в TON…", parse_mode="HTML")
            t = await geckoterminal.fetch_token_on_chain(session, "ton", address)
            if not t:
                ds = await dexscreener.fetch_token_pairs(session, address)
                t = next((x for x in ds if x.chain == "ton"), None)
            if not t:
                t = Token(chain="ton", address=address)
            t = await enrich_token(session, t)
            await status.delete()
            if not t.symbol and not t.name and not t.liquidity_usd:
                await message.answer(
                    f"❌ TON jetton <code>{_esc(address)}</code> не найден.",
                    reply_markup=back_to_menu_kb(),
                    parse_mode="HTML",
                )
                return
            await _persist_and_show(message, t, user_id)
            return


@router.callback_query(TokenChainPick.filter())
async def cb_token_chain_pick(callback: CallbackQuery, callback_data: TokenChainPick) -> None:
    entry = token_cache.get(callback_data.key)
    if not entry:
        await callback.answer("Адрес устарел, введите снова", show_alert=True)
        return
    _multi, address = entry
    chain = callback_data.chain
    await callback.answer("Загружаю…")
    async with aiohttp.ClientSession() as session:
        t = await geckoterminal.fetch_token_on_chain(session, chain, address)
        if not t:
            await callback.message.edit_text(
                f"❌ Не удалось загрузить токен на {chain}",
                reply_markup=back_to_menu_kb(),
            )
            return
        t = await enrich_token(session, t)
    await _persist_and_show(callback, t, callback.from_user.id, edit=True)


@router.callback_query(TokenAction.filter(F.action == "refresh"))
async def cb_token_refresh(callback: CallbackQuery, callback_data: TokenAction) -> None:
    entry = token_cache.get(callback_data.key)
    if not entry:
        await callback.answer("Сессия устарела, введите адрес снова", show_alert=True)
        return
    chain, address = entry
    await callback.answer("Обновляю…")
    async with aiohttp.ClientSession() as session:
        t = await geckoterminal.fetch_token_on_chain(session, chain, address)
        if not t:
            await callback.answer("Не удалось обновить", show_alert=True)
            return
        t = await enrich_token(session, t)
    await _persist_and_show(callback, t, callback.from_user.id, edit=True)


@router.callback_query(TokenAction.filter(F.action == "score"))
async def cb_token_score(callback: CallbackQuery, callback_data: TokenAction) -> None:
    entry = token_cache.get(callback_data.key)
    if not entry:
        await callback.answer("Сессия устарела", show_alert=True)
        return
    chain, address = entry
    token = await TokenQueries.get_token(chain, address)
    score = await TokenQueries.get_latest_score(chain, address)
    if not token or not score:
        await callback.answer("Нет данных скоринга", show_alert=True)
        return
    text = format_token_card(token) + "\n\n" + format_token_score_breakdown(score)
    is_watching = await TokenWatchlistQueries.is_watching(callback.from_user.id, chain, address)
    await callback.message.edit_text(
        text,
        reply_markup=token_actions_kb(callback_data.key, is_watching=is_watching),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(TokenAction.filter(F.action == "watch"))
async def cb_token_watch(callback: CallbackQuery, callback_data: TokenAction) -> None:
    entry = token_cache.get(callback_data.key)
    if not entry:
        await callback.answer("Сессия устарела", show_alert=True)
        return
    chain, address = entry
    token = await TokenQueries.get_token(chain, address)
    entry_price = token.price_usd if token else 0
    await TokenWatchlistQueries.add(callback.from_user.id, chain, address, entry_price)
    await PointsQueries.award(callback.from_user.id, 2)
    await callback.answer("✅ Добавлено в watchlist")
    if token:
        score = await TokenQueries.get_latest_score(chain, address)
        await callback.message.edit_text(
            format_token_card(token, score),
            reply_markup=token_actions_kb(callback_data.key, is_watching=True),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


@router.callback_query(TokenAction.filter(F.action == "unwatch"))
async def cb_token_unwatch(callback: CallbackQuery, callback_data: TokenAction) -> None:
    entry = token_cache.get(callback_data.key)
    if not entry:
        await callback.answer("Сессия устарела", show_alert=True)
        return
    chain, address = entry
    await TokenWatchlistQueries.remove(callback.from_user.id, chain, address)
    await callback.answer("Удалено из watchlist")
    token = await TokenQueries.get_token(chain, address)
    if token:
        score = await TokenQueries.get_latest_score(chain, address)
        await callback.message.edit_text(
            format_token_card(token, score),
            reply_markup=token_actions_kb(callback_data.key, is_watching=False),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
