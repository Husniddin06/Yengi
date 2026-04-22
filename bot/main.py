import asyncio
import logging
import sys
import os

# PYTHONPATH ni to'g'rilash (Railway uchun muhim)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from database.db import init_db, init_extras
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router
from utils.scheduler import start_scheduler

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Bot ishga tushmoqda...")
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! Railway Variables bo'limini tekshiring.")
        return

    try:
        await init_db()
        await init_extras()
        start_scheduler()
        
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher()
        dp.include_router(user_router)
        dp.include_router(admin_router)
        
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot muvaffaqiyatli ishga tushdi.")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Kritik xatolik: {e}")

if __name__ == "__main__":
    asyncio.run(main())
