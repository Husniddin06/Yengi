
import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_webhook
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID
from database.db import init_db, add_user, get_user
from handlers.user_handlers import user_router, get_message
from handlers.admin_handlers import admin_router

# Webhook settings
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8000
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "my-secret"
BASE_WEBHOOK_URL = "https://your-domain.com" # Replace with your actual domain

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret=WEBHOOK_SECRET)
    logging.info("Bot started and webhook set!")

async def on_shutdown(bot: Bot):
    logging.info("Bot shutting down and webhook deleted!")
    await bot.delete_webhook()

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(user_router)
    dp.include_router(admin_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_webhook(app, path=WEBHOOK_PATH)

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    asyncio.run(main())
