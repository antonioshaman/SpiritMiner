from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.callbacks import MenuAction
from keyboards.main_menu import back_to_menu_kb

router = Router()

PROVIDERS = [
    {
        "name": "Hetzner",
        "mining_allowed": False,
        "gpu": False,
        "cpu_price": "$4-50/мес",
        "risk": "Бан аккаунта",
        "verdict": "\U0001f534",
        "note": "Запрещает майнинг в ToS. Мониторят CPU нагрузку.",
    },
    {
        "name": "Vast.ai",
        "mining_allowed": True,
        "gpu": True,
        "cpu_price": "$0.10-1.50/час GPU",
        "risk": "Высокая цена при низком профите",
        "verdict": "\U0001f7e1",
        "note": "GPU аренда, майнинг разрешён. Проверяй ROI — часто убыточно.",
    },
    {
        "name": "Salad.com",
        "mining_allowed": True,
        "gpu": True,
        "cpu_price": "Свои ресурсы",
        "risk": "Малый выбор монет",
        "verdict": "\U0001f7e1",
        "note": "Используешь своё железо, получаешь кредиты. Ограниченный выбор.",
    },
    {
        "name": "NiceHash",
        "mining_allowed": True,
        "gpu": True,
        "cpu_price": "Рыночная",
        "risk": "Продаёшь хешрейт, не монеты",
        "verdict": "\U0001f7e2",
        "note": "Marketplace хешрейта. Стабильный доход, но без upside новых монет.",
    },
    {
        "name": "Колокация",
        "mining_allowed": True,
        "gpu": True,
        "cpu_price": "$0.04-0.08/kWh",
        "risk": "Начальные инвестиции",
        "verdict": "\U0001f7e2",
        "note": "Лучший вариант для серьёзного майнинга. Своё железо, дешёвое электричество.",
    },
    {
        "name": "AWS / GCP / Azure",
        "mining_allowed": False,
        "gpu": True,
        "cpu_price": "$1-3/час GPU",
        "risk": "Бан + огромный счёт",
        "verdict": "\U0001f534",
        "note": "Запрещают майнинг. Цены делают это убыточным в любом случае.",
    },
]


class ProviderSelect(CallbackData, prefix="prov"):
    idx: int


@router.callback_query(MenuAction.filter(F.action == "provider"))
async def cb_provider(callback: CallbackQuery) -> None:
    lines = [
        "\U0001f3e2 <b>Провайдер-чекер</b>\n",
        "Где можно майнить, а где нельзя:\n",
    ]
    buttons = []
    for i, p in enumerate(PROVIDERS):
        allowed = "✅" if p["mining_allowed"] else "❌"
        lines.append(f"{p['verdict']} <b>{p['name']}</b> — майнинг: {allowed}")
        buttons.append([InlineKeyboardButton(
            text=f"{p['verdict']} {p['name']}",
            callback_data=ProviderSelect(idx=i).pack(),
        )])

    buttons.append([InlineKeyboardButton(
        text="◀️ Главное меню",
        callback_data=MenuAction(action="main").pack(),
    )])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ProviderSelect.filter())
async def cb_provider_detail(callback: CallbackQuery, callback_data: ProviderSelect) -> None:
    idx = callback_data.idx
    if idx >= len(PROVIDERS):
        await callback.answer("Не найден", show_alert=True)
        return

    p = PROVIDERS[idx]
    allowed = "✅ Разрешён" if p["mining_allowed"] else "❌ Запрещён"
    gpu = "✅" if p["gpu"] else "❌"

    text = (
        f"{p['verdict']} <b>{p['name']}</b>\n\n"
        f"⛏️ Майнинг: {allowed}\n"
        f"\U0001f4bb GPU: {gpu}\n"
        f"\U0001f4b0 Цена: {p['cpu_price']}\n"
        f"⚠️ Риск: {p['risk']}\n\n"
        f"\U0001f4dd {p['note']}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="◀️ К провайдерам",
                callback_data=MenuAction(action="provider").pack(),
            )],
            [InlineKeyboardButton(
                text="◀️ Главное меню",
                callback_data=MenuAction(action="main").pack(),
            )],
        ]),
        parse_mode="HTML",
    )
    await callback.answer()
