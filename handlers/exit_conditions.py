from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db.queries import CoinQueries
from keyboards.callbacks import MenuAction, CoinAction
from keyboards.main_menu import coin_actions_kb, back_to_menu_kb, coin_list_kb
from services.scorer import check_exit_signals
from utils.formatting import format_exit_signals

router = Router()


class ExitStates(StatesGroup):
    waiting_for_input = State()


@router.callback_query(MenuAction.filter(F.action == "exit_cond"))
async def cb_exit_conditions(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "\U0001f6aa <b>Условия выхода</b>\n\n"
        "Введите тикер или название монеты:",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await state.set_state(ExitStates.waiting_for_input)
    await callback.answer()


@router.message(ExitStates.waiting_for_input, ~Command("start"), ~Command("help"))
async def handle_exit_input(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    await state.clear()

    coins = await CoinQueries.find_coin(query)

    if not coins:
        await message.answer(
            f"❌ Монета <b>{query}</b> не найдена.",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        return

    if len(coins) == 1:
        coin = coins[0]
        signals = await check_exit_signals(coin)
        text = f"<b>{coin.name} ({coin.tag})</b>\n\n" + format_exit_signals(signals)
        await message.answer(text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML")
        return

    await message.answer(
        f"\U0001f50e Найдено {len(coins)} монет — выберите:",
        reply_markup=coin_list_kb(coins, 0, "exit"),
        parse_mode="HTML",
    )


@router.callback_query(CoinAction.filter(F.action == "exit"))
async def cb_coin_exit(callback: CallbackQuery, callback_data: CoinAction) -> None:
    coin = await CoinQueries.get_coin(callback_data.coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    signals = await check_exit_signals(coin)
    text = f"<b>{coin.name} ({coin.tag})</b>\n\n" + format_exit_signals(signals)
    await callback.message.edit_text(
        text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML"
    )
    await callback.answer()
