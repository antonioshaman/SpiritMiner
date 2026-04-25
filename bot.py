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
from scheduler.jobs import scan_new_coins, rescore_all, record_difficulty_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


async def main() -> None:
    if not config.BOT_TOKEN:
        log.error("SPIRITMINER_BOT_TOKEN not set")
        sys.exit(1)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_routers(
        start.router,
        new_coins.router,
        top_scoring.router,
        check_coin.router,
        calc_entry.router,
        exit_conditions.router,
    )

    await init_db()
    log.info("Database initialized")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(scan_new_coins, "interval", minutes=config.SCAN_INTERVAL)
    scheduler.add_job(rescore_all, "interval", minutes=config.RESCORE_INTERVAL)
    scheduler.add_job(record_difficulty_history, "interval", minutes=config.HISTORY_INTERVAL)
    scheduler.start()
    log.info("Scheduler started")

    log.info("Running initial coin scan...")
    await scan_new_coins()
    await rescore_all()

    log.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
