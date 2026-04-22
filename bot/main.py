'''import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from database.db import init_db
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    await init_db()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started in polling mode")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
'''
