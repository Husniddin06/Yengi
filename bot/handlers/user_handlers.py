import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from datetime import datetime

from bot.database import db
from bot.utils.openai_utils import get_chat_response, generate_image
from bot.utils.keyboards import (
    main_menu, lang_keyboard,
    BTN_BALANCE, BTN_CLEAR, BTN_IMAGE, BTN_PREMIUM,
    BTN_HELP, BTN_REF, BTN_LANG, BTN_BONUS,
)

logger = logging.getLogger(__name__)
user_router = Router()

TEXTS = {
    "ru": {
        "welcome": "Привет! Я умный ИИ бот. Выберите язык или начните общение.",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "balance": "📊 Ваш баланс: {limit} запросов\n💎 Premium: {premium}",
        "premium_info": "💎 Premium дает безлимитные запросы и доступ к GPT-4o.\nКупить: {link}",
        "help": "🆘 Помощь:\n/start - Перезапуск\n/lang - Смена языка\nПросто отправьте текст или картинку для общения.",
        "history_cleared": "🗑 История диалога очищена.",
        "image_prompt": "🎨 Отправьте описание картинки, которую хотите создать.",
        "bonus_claimed": "🎁 Вы получили бонус: +{amount} запросов!",
        "bonus_already": "❌ Вы уже получили бонус сегодня.",
        "ref_info": "👥 Приглашайте друзей и получайте бонусы!\nВаша ссылка: {link}\nВсего приглашено: {count}",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_limit": "❌ У вас закончились запросы. Купите Premium или подождите обновления.",
    },
    "en": {
        "welcome": "Hello! I am a smart AI bot. Choose a language or start chatting.",
        "lang_set": "Language set to English 🇬🇧",
        "balance": "📊 Your balance: {limit} requests\n💎 Premium: {premium}",
        "premium_info": "💎 Premium gives unlimited requests and access to GPT-4o.\nBuy: {link}",
        "help": "🆘 Help:\n/start - Restart\n/lang - Change language\nJust send text or an image to start chatting.",
        "history_cleared": "🗑 Conversation history cleared.",
        "image_prompt": "🎨 Send a description of the image you want to create.",
        "bonus_claimed": "🎁 You received a bonus: +{amount} requests!",
        "bonus_already": "❌ You already claimed your bonus today.",
        "ref_info": "👥 Invite friends and get bonuses!\nYour link: {link}\nTotal invited: {count}",
        "error": "❌ An error occurred. Please try again later.",
        "no_limit": "❌ You have run out of requests. Buy Premium or wait for a reset.",
    }
}

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        # Check for referral
        ref_id = None
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
        await db.add_user(message.from_user.id, message.from_user.username, "en", ref_id)
        user = await db.get_user(message.from_user.id)
    
    lang = user['language_code'] if user else "en"
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    if not user or not user['language_code']:
        await message.answer("Choose language / Выберите язык:", reply_markup=lang_keyboard())

@user_router.message(Command("lang"))
@user_router.message(F.text.in_(BTN_LANG))
async def cmd_lang(message: Message):
    await message.answer("Choose language / Выберите язык:", reply_markup=lang_keyboard())

@user_router.callback_query(F.data.startswith("setlang_"))
async def set_language(cb: CallbackQuery):
    lang = cb.data.split("_")[1]
    await db.update_user_language(cb.from_user.id, lang)
    await cb.message.edit_text(TEXTS[lang]["lang_set"])
    await cb.message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    await cb.answer()

@user_router.message(F.text.in_(BTN_BALANCE))
async def show_balance(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    premium_status = "✅" if user['is_premium'] else "❌"
    await message.answer(TEXTS[lang]["balance"].format(limit=user['daily_limit'], premium=premium_status))

@user_router.message(F.text.in_(BTN_HELP))
async def show_help(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["help"])

@user_router.message(F.text.in_(BTN_CLEAR))
async def clear_history(message: Message):
    await db.clear_conversation_history(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["history_cleared"])

@user_router.message(F.text.in_(BTN_BONUS))
async def get_bonus(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    from bot.config import DAILY_BONUS
    success = await db.claim_daily_bonus(message.from_user.id, DAILY_BONUS)
    if success:
        await message.answer(TEXTS[lang]["bonus_claimed"].format(amount=DAILY_BONUS))
    else:
        await message.answer(TEXTS[lang]["bonus_already"])

@user_router.message(F.text.in_(BTN_IMAGE))
async def image_info(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["image_prompt"])

@user_router.message(F.text)
async def handle_message(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    
    if user['daily_limit'] <= 0 and not user['is_premium']:
        await message.answer(TEXTS[lang]["no_limit"])
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    try:
        history = await db.get_chat_history(message.from_user.id)
        response = await get_chat_response(message.text, history)
        await db.save_conversation(message.from_user.id, message.text, response)
        
        if not user['is_premium']:
            await db.update_user_limit(message.from_user.id, user['daily_limit'] - 1)
            
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await message.answer(TEXTS[lang]["error"])
