import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database.db import init_db
from handlers.user_handlers import user_router
from handlers.admin_handlers import admin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_PATH = f"/webhook/bot/{BOT_TOKEN}"
BASE_WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com")


async def on_startup(bot: Bot):
    await init_db()
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    logger.info(f"Bot started! Webhook set to {webhook_url}")


async def on_shutdown(bot: Bot):
    logger.info("Bot shutting down...")
    await bot.delete_webhook()


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(user_router)
    dp.include_router(admin_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()

    logger.info(f"Server started on {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
