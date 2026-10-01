from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from services.arbitrage import scan, format_report

router = Router()


@router.message(Command('arb'))
async def cmd_arb(message: Message):
    import config
    if message.from_user.id != config.ADMIN_ID:
        await message.answer('Проверка маршрутов доступна администратору. Сигналы доступны подписчикам.')
        return
    for report in await scan():
        await message.answer(format_report(report), parse_mode='HTML')


@router.message(Command('arb_help'))
async def cmd_arb_help(message: Message):
    await message.answer(
        '<b>Арбитраж TON/GRAM</b>\n\n'
        '/arb — проверка полного круга для настроенных объёмов (администратор).\n'
        '1. Native → именно старый Ethereum TONCOIN.\n'
        '2. TONCOIN → WETH → USDT: объёмная котировка Uniswap.\n'
        '3. USDT Ethereum → USDT в Wallet: комиссии, лимиты, доступность.\n'
        '4. USDT → native с выводом в TON.\n\n'
        'BLOCKED означает, что часть маршрута не подтверждена. '
        'Рост или падение свечи не является сигналом арбитража. '
        'Без действующего моста круг не замыкается. '
        'PROFIT — расчётная возможность, цены могут измениться до завершения моста. '
        'Настройка провайдеров описана в specs/arbitrage.md.', parse_mode='HTML')
