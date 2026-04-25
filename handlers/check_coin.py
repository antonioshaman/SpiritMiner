from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import aiohttp

from db.queries import CoinQueries, VoteQueries, PointsQueries, PoolDetailQueries
from keyboards.callbacks import MenuAction, CoinAction
from keyboards.main_menu import coin_actions_kb, back_to_menu_kb, coin_list_kb
from services.scorer import compute_score, enrich_from_coingecko
from utils.formatting import format_coin_card, format_score_breakdown, format_pool_details

router = Router()


class CheckCoinStates(StatesGroup):
    waiting_for_input = State()


@router.callback_query(MenuAction.filter(F.action == "check_coin"))
async def cb_check_coin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "\U0001f50d <b>Проверить монету</b>\n\n"
        "Введите тикер или название монеты:",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await state.set_state(CheckCoinStates.waiting_for_input)
    await callback.answer()


@router.message(CheckCoinStates.waiting_for_input, ~Command("start"), ~Command("help"))
async def handle_coin_input(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    await state.clear()
    await PointsQueries.award(message.from_user.id, 1)

    coins = await CoinQueries.find_coin(query)

    if not coins:
        await message.answer(
            f"❌ Монета <b>{query}</b> не найдена.\n\n"
            "Попробуйте другой тикер или название.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        return

    if len(coins) == 1:
        coin = coins[0]
        score = await CoinQueries.get_latest_score(coin.id)
        sentiment = await VoteQueries.get_sentiment(coin.id)
        pools = await PoolDetailQueries.get_pools(coin.id)
        text = format_coin_card(coin, score, sentiment) + format_pool_details(pools)
        await message.answer(text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML")
        return

    await message.answer(
        f"\U0001f50e Найдено {len(coins)} монет по запросу <b>{query}</b>:",
        reply_markup=coin_list_kb(coins, 0, "search"),
        parse_mode="HTML",
    )


@router.callback_query(CoinAction.filter(F.action == "detail"))
async def cb_coin_detail(callback: CallbackQuery, callback_data: CoinAction) -> None:
    coin = await CoinQueries.get_coin(callback_data.coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    score = await CoinQueries.get_latest_score(coin.id)
    sentiment = await VoteQueries.get_sentiment(coin.id)
    pools = await PoolDetailQueries.get_pools(coin.id)
    text = format_coin_card(coin, score, sentiment) + format_pool_details(pools)
    await callback.message.edit_text(
        text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(CoinAction.filter(F.action == "score"))
async def cb_coin_score(callback: CallbackQuery, callback_data: CoinAction) -> None:
    coin = await CoinQueries.get_coin(callback_data.coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    await callback.answer("Считаю скоринг...", show_alert=False)
    await PointsQueries.award(callback.from_user.id, 2)

    async with aiohttp.ClientSession() as session:
        coin = await enrich_from_coingecko(session, coin)
        score = await compute_score(session, coin)

    await CoinQueries.save_score(score)
    await CoinQueries.upsert_coin(coin)

    text = format_coin_card(coin) + "\n\n" + format_score_breakdown(score)
    await callback.message.edit_text(
        text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML"
    )


@router.callback_query(CoinAction.filter(F.action == "refresh"))
async def cb_coin_refresh(callback: CallbackQuery, callback_data: CoinAction) -> None:
    coin = await CoinQueries.get_coin(callback_data.coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    await callback.answer("Обновляю данные...", show_alert=False)

    async with aiohttp.ClientSession() as session:
        from services.whattomine import fetch_coin_detail
        detail = await fetch_coin_detail(session, coin.id)
        if detail:
            detail.first_seen = coin.first_seen
            detail.github_url = coin.github_url
            detail.coingecko_id = coin.coingecko_id
            coin = detail

        coin = await enrich_from_coingecko(session, coin)
        score = await compute_score(session, coin)

    await CoinQueries.upsert_coin(coin)
    await CoinQueries.save_score(score)

    text = format_coin_card(coin, score)
    await callback.message.edit_text(
        text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML"
    )
