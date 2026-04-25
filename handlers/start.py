from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.callbacks import MenuAction
from keyboards.main_menu import main_menu_kb

router = Router()

WELCOME = (
    "⛏️ <b>SpiritMiner</b> — разведчик ранних PoW-возможностей\n\n"
    "Нахожу новые PoW-монеты раньше толпы.\n"
    "Считаю скоринг, оцениваю риск, показываю окно входа и момент выхода.\n\n"
    "Не <i>\"что выгодно сейчас\"</i> — а <b>\"что станет выгодным "
    "через 12–72 часа\"</b>.\n\n"
    "Выбери действие:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(MenuAction.filter(F.action == "main"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "about"))
async def cb_about(callback: CallbackQuery) -> None:
    text = (
        "ℹ️ <b>SpiritMiner v1.3</b>\n\n"
        "Разведчик ранних PoW-возможностей.\n"
        "Нахожу новые монеты, считаю скоринг, "
        "показываю окно входа и момент выхода.\n\n"
        "<b>Что умею:</b>\n"
        "\U0001f195 Новые PoW-монеты — свежие находки\n"
        "\U0001f3c6 Топ по скорингу — рейтинг 100 баллов\n"
        "\U0001f50d Проверить монету — полный анализ\n"
        "\U0001f4c8 Рассчитать вход — стратегия входа\n"
        "\U0001f6aa Условия выхода — когда пора уходить\n"
        "\U0001f4bb Калькулятор железа — PnL твоего GPU\n"
        "\U0001f3e2 Провайдер-чекер — где можно майнить\n"
        "\U0001f514 Алерты — уведомления о сигналах\n\n"
        "<b>Сигналы:</b>\n"
        "\U0001f7e2 60+ — Можно пробовать\n"
        "\U0001f7e1 35-59 — Только тестовым объёмом\n"
        "\U0001f534 &lt;35 — Не лезть"
    )
    from keyboards.main_menu import back_to_menu_kb
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()
