from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.queries import CoinQueries
from keyboards.callbacks import MenuAction, CoinAction
from keyboards.main_menu import back_to_menu_kb, coin_actions_kb
from services.partnerships import format_partners_overview, format_coin_partners

router = Router()


@router.callback_query(MenuAction.filter(F.action == "partners"))
async def cb_partners(callback: CallbackQuery) -> None:
    text = format_partners_overview()
    await callback.message.edit_text(
        text, reply_markup=back_to_menu_kb(), parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(CoinAction.filter(F.action == "partners"))
async def cb_coin_partners(callback: CallbackQuery, callback_data: CoinAction) -> None:
    coin = await CoinQueries.get_coin(callback_data.coin_id)
    if not coin:
        await callback.answer("Монета не найдена", show_alert=True)
        return

    text = format_coin_partners(coin)
    await callback.message.edit_text(
        text, reply_markup=coin_actions_kb(coin.id), parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()
