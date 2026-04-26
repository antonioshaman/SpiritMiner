import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from db.database import init_db, close_db
from handlers import start, new_coins, top_scoring, check_coin, calc_entry, exit_conditions
from handlers import subscribe, hardware, provider, community, partners, spirit_index
from scheduler.jobs import scan_new_coins, rescore_all, record_difficulty_history, enrich_pool_details
from services.alerter import send_new_coin_alerts, send_exit_alerts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

_bot: Bot | None = None


def get_bot() -> Bot:
    return _bot


async def main() -> None:
    global _bot
    if not config.BOT_TOKEN:
        log.error("SPIRITMINER_BOT_TOKEN not set")
        sys.exit(1)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    _bot = bot
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_routers(
        start.router,
        new_coins.router,
        top_scoring.router,
        check_coin.router,
        calc_entry.router,
        exit_conditions.router,
        subscribe.router,
        hardware.router,
        provider.router,
        community.router,
        partners.router,
        spirit_index.router,
    )

    await init_db()
    log.info("Database initialized")

    async def alert_job():
        await send_new_coin_alerts(bot)
        await send_exit_alerts(bot)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(scan_new_coins, "interval", minutes=config.SCAN_INTERVAL, max_instances=1, coalesce=True)
    scheduler.add_job(rescore_all, "interval", minutes=config.RESCORE_INTERVAL, max_instances=1, coalesce=True)
    scheduler.add_job(record_difficulty_history, "interval", minutes=config.HISTORY_INTERVAL)
    scheduler.add_job(enrich_pool_details, "interval", hours=6, max_instances=1, coalesce=True)
    scheduler.add_job(alert_job, "interval", minutes=config.RESCORE_INTERVAL)
    scheduler.start()
    log.info("Scheduler started")

    version = config.get_version()
    try:
        from db.queries import CoinQueries, SubscriberQueries
        coins = await CoinQueries.list_all_coins()
        subs = await SubscriberQueries.get_all_subscribers()
        await bot.send_message(
            config.ADMIN_ID,
            f"✅ <b>SpiritMiner v{version} запущен</b>\n\n"
            f"⛏️ Монет в базе: {len(coins)}\n"
            f"\U0001f465 Подписчиков: {len(subs)}\n"
            f"\U0001f4c5 Сканирование: каждые {config.SCAN_INTERVAL} мин\n"
            f"\U0001f504 Ресокринг: каждые {config.RESCORE_INTERVAL} мин",
            parse_mode="HTML",
        )
    except Exception:
        log.debug("Failed to send startup notification", exc_info=True)

    async def _background_startup():
        log.info("Running initial coin scan...")
        await scan_new_coins()
        log.info("Initial scan complete, starting rescore...")
        await rescore_all()
        log.info("Background startup complete")

    def _on_startup_done(task):
        if task.exception():
            log.error("Background startup failed: %s", task.exception())

    _startup_task = asyncio.create_task(_background_startup())
    _startup_task.add_done_callback(_on_startup_done)

    log.info("Starting bot polling v%s...", version)
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
