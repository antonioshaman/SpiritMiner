from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from db.queries import CoinQueries
from keyboards.callbacks import MenuAction
from keyboards.main_menu import back_to_menu_kb
from services.calculator import (
    get_gpu_list, get_gpu_by_name, GPU_POWER,
    estimate_daily_revenue, estimate_pnl,
)

router = Router()


class GpuSelect(CallbackData, prefix="gpu"):
    name: str


class HardwareStates(StatesGroup):
    waiting_electricity = State()


@router.callback_query(MenuAction.filter(F.action == "hardware"))
async def cb_hardware(callback: CallbackQuery) -> None:
    gpus = get_gpu_list()
    buttons = []
    for gpu in gpus:
        buttons.append([InlineKeyboardButton(
            text=f"\U0001f4bb {gpu['name']}",
            callback_data=GpuSelect(name=gpu["name"]).pack(),
        )])
    buttons.append([InlineKeyboardButton(
        text="◀️ Главное меню",
        callback_data=MenuAction(action="main").pack(),
    )])

    await callback.message.edit_text(
        "\U0001f4bb <b>Калькулятор железа</b>\n\n"
        "Выбери свою видеокарту.\n"
        "Бот рассчитает доходность по всем PoW-монетам.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(GpuSelect.filter())
async def cb_gpu_selected(callback: CallbackQuery, callback_data: GpuSelect) -> None:
    gpu_name = callback_data.name
    gpu = get_gpu_by_name(gpu_name)
    if not gpu:
        await callback.answer("GPU не найдена", show_alert=True)
        return

    await callback.answer(f"Считаю для {gpu_name}...", show_alert=False)

    coins = await CoinQueries.list_all_coins()
    power = GPU_POWER.get(gpu_name, 300)
    electricity = 0.10

    results = []
    for coin in coins:
        algo = coin.algorithm
        hashrate_mhs = gpu["algos"].get(algo, 0)
        if not hashrate_mhs or not coin.exchange_rate_usd:
            continue

        hashrate_hs = hashrate_mhs * 1e6

        rev = estimate_daily_revenue(
            coin.difficulty, coin.nethash, coin.block_reward,
            coin.block_time, hashrate_hs, coin.exchange_rate_usd,
        )
        pnl = estimate_pnl(rev["revenue_usd"], power, electricity)

        if rev["revenue_usd"] > 0:
            results.append({
                "coin": coin,
                "revenue": rev["revenue_usd"],
                "profit": pnl["profit_usd"],
                "cost": pnl["electricity_cost"],
                "share": rev["share_pct"],
            })

    results.sort(key=lambda x: x["profit"], reverse=True)

    lines = [
        f"\U0001f4bb <b>Доходность: {gpu_name}</b>",
        f"⚡ Потребление: {power}W | \U0001f4b0 Электричество: ${electricity}/kWh\n",
    ]

    if not results:
        lines.append("Нет подходящих монет для этого GPU.")
    else:
        for i, r in enumerate(results[:15], 1):
            coin = r["coin"]
            profit_emoji = "\U0001f7e2" if r["profit"] > 0 else "\U0001f534"
            lines.append(
                f"{i}. {profit_emoji} <b>{coin.tag}</b> ({coin.algorithm})\n"
                f"   Доход: ${r['revenue']:.4f}/день | "
                f"Профит: ${r['profit']:.4f}/день"
            )

        profitable = sum(1 for r in results if r["profit"] > 0)
        lines.append(f"\n✅ Прибыльных: {profitable}/{len(results)}")

        if results[0]["profit"] > 0:
            best = results[0]
            lines.append(
                f"\n\U0001f3c6 <b>Лучший выбор: {best['coin'].tag}</b> — "
                f"${best['profit']:.4f}/день чистыми"
            )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
