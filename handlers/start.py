from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.callbacks import MenuAction
from keyboards.main_menu import main_menu_kb

router = Router()

WELCOME = (
    "⛏️ <b>SpiritMiner</b> — разведчик ранних PoW-возможностей\n\n"
    "Бот ищет новые монеты, считает риск, окно входа и момент выхода.\n\n"
    "Не <i>\"что выгодно сейчас\"</i> — а <b>\"что может стать выгодным "
    "через 12–72 часа, пока толпа ещё не пришла\"</b>."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(MenuAction.filter(F.action == "main"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "about"))
async def cb_about(callback: CallbackQuery) -> None:
    text = (
        "ℹ️ <b>SpiritMiner v1.0</b>\n\n"
        "Источники данных:\n"
        "• WhatToMine API\n"
        "• MiningPoolStats\n"
        "• GitHub API\n"
        "• CoinGecko API\n\n"
        "<b>Скоринг: 100 баллов</b>\n"
        "+20 новизна | +15 explorer | +15 пулы\n"
        "+15 GitHub | +10 комьюнити | +10 биржи\n"
        "+10 сложность | +5 токеномика\n\n"
        "<b>Сигналы:</b>\n"
        "\U0001f7e2 60+ — Можно пробовать\n"
        "\U0001f7e1 35-59 — Только тестовым объёмом\n"
        "\U0001f534 &lt;35 — Не лезть"
    )
    from keyboards.main_menu import back_to_menu_kb
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()
