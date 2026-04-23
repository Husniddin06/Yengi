import os
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, PhotoSize
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from bot.database import db
from bot.utils.openai_utils import get_chat_response, generate_image, analyze_image_and_chat
from bot.utils.keyboards import (
    main_reply_menu, lang_keyboard, payment_options_keyboard,
    tasks_keyboard, admin_payment_confirm_keyboard, characters_keyboard,
    MENU_LABELS
)
from bot.config import ADMIN_ID

logger = logging.getLogger(__name__)
user_router = Router()

class UserStates(StatesGroup):
    waiting_for_nano_prompt = State()
    waiting_for_vision_image = State()

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Я твой персональный ИИ ассистент.\n\n— домашка, посты, идеи.\n👁 Анализировать фото — скинь картинку, и я всё расскажу!\n🎨 Рисовать арты (Nano Banana) — аватарки, обложки.\n\n👇 Выбирай функции в меню ниже:",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "profile": "👤 <b>Мой профиль:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Баланс: {coins} монет\n💎 Premium: {premium}\n👥 Друзей: {refs}\n🎭 Персонаж: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 монет сразу\n- Доступ к GPT-4o\n- Безлимитные запросы\nВыберите способ оплаты:",
        "help": "🆘 Помощь:\n/start - Перезапуск\nЧat с ботом БЕСПЛАТНЫЙ.\nNano Banana - 10 монет за фото.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nОтправьте описание для создания вирального бананового арта! (Например: 'кот-космонавт')",
        "generating_image": "🎨 Генерирую изображение, пожалуйста подождите...",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_coins": "❌ У вас недостаточно монет (нужно 10). Выполните задания или купите Premium.",
        "sbp_request_sent": "💳 Запрос на оплату через СБП отправлен админу. После перевода 75₽ на карту, админ подтвердит платеж и вам придет 150 монет.",
        "tasks_title": "🎁 <b>Задания:</b>\nВыполняйте задания и получайте монеты!",
        "tiktok_msg": "📱 <b>TikTok Режим:</b>\nДля прослушивания и скачивания музыки из TikTok используйте наш партнерский бот: @VkMuzicXbot",
        "hype_prompts": "🔥 <b>Хайп Промты для AI:</b>\n\n1. <code>Ultra-realistic cinematic night portrait of a cybernetic banana in Tokyo</code>\n2. <code>Funny banana minion style character as a CEO of a tech company</code>\n3. <code>3D render of a banana house in a tropical forest, 8k resolution</code>\n4. <code>Vintage oil painting of a banana philosopher thinking about life</code>\n\nСкопируйте и используйте в Nano Banana!",
        "char_set": "🎭 Персонаж изменен на: {name}",
        "vision_info": "📸 <b>Prompt from Photo:</b>\nОтправьте фото, и я составлю для него идеальный промт для генерации похожих изображений!",
    },
    "en": {
        "welcome": "👋 Hello! I am your personal AI assistant.\n\n— homework, posts, ideas.\n👁 Analyze photo — send a picture, and I'll tell you everything!\n🎨 Draw arts (Nano Banana) — avatars, covers.\n\n👇 Choose functions in the menu below:",
        "lang_set": "Language set to English 🇬🇧",
        "profile": "👤 <b>My Profile:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Balance: {coins} coins\n💎 Premium: {premium}\n👥 Friends: {refs}\n🎭 Character: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 coins instantly\n- GPT-4o access\n- Unlimited requests\nChoose payment method:",
        "help": "🆘 Help:\n/start - Restart\nChatting is FREE.\nNano Banana - 10 coins per photo.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nSend a description to create viral banana art! (e.g., 'astronaut cat')",
        "generating_image": "🎨 Generating image, please wait...",
        "error": "❌ An error occurred. Please try again later.",
        "no_coins": "❌ You don't have enough coins (need 10). Complete tasks or buy Premium.",
        "sbp_request_sent": "💳 SBP payment request sent to admin. After transferring 75₽, admin will confirm and you will receive 150 coins.",
        "tasks_title": "🎁 <b>Tasks:</b>\nComplete tasks and get coins!",
        "tiktok_msg": "📱 <b>TikTok Mode:</b>\nTo listen and download music from TikTok, use our partner bot: @VkMuzicXbot",
        "hype_prompts": "🔥 <b>Hype Prompts for AI:</b>\n\n1. <code>Ultra-realistic cinematic night portrait of a cybernetic banana in Tokyo</code>\n2. <code>Funny banana minion style character as a CEO of a tech company</code>\n3. <code>3D render of a banana house in a tropical forest, 8k resolution</code>\n4. <code>Vintage oil painting of a banana philosopher thinking about life</code>\n\nCopy and use in Nano Banana!",
        "char_set": "🎭 Character changed to: {name}",
        "vision_info": "📸 <b>Prompt from Photo:</b>\nSend a photo, and I will create the perfect prompt for generating similar images!",
    }
}

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        ref_id = None
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
        await db.add_user(
            user_id=message.from_user.id, 
            username=message.from_user.username, 
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code="en", 
            referred_by=ref_id
        )
        user = await db.get_user(message.from_user.id)
    
    lang = user['language_code'] if user and user['language_code'] else "en"
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_reply_menu(lang))

# --- Reply Keyboard Handlers ---
@user_router.message(F.text.in_([MENU_LABELS["ru"]["nano"], MENU_LABELS["en"]["nano"]]))
async def handle_nano(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    if user['coins'] < 10:
        await message.answer(TEXTS[lang]["no_coins"])
        return
    await message.answer(TEXTS[lang]["nano_prompt"], parse_mode="HTML")
    await state.set_state(UserStates.waiting_for_nano_prompt)

@user_router.message(F.text.in_([MENU_LABELS["ru"]["vision"], MENU_LABELS["en"]["vision"]]))
async def handle_vision(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["vision_info"], parse_mode="HTML")
    await state.set_state(UserStates.waiting_for_vision_image)

@user_router.message(F.text.in_([MENU_LABELS["ru"]["characters"], MENU_LABELS["en"]["characters"]]))
async def handle_characters(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer("🎭 Choose your AI Character:", reply_markup=characters_keyboard(lang))

@user_router.message(F.text.in_([MENU_LABELS["ru"]["tiktok"], MENU_LABELS["en"]["tiktok"]]))
async def handle_tiktok(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["tiktok_msg"])

@user_router.message(F.text.in_([MENU_LABELS["ru"]["profile"], MENU_LABELS["en"]["profile"]]))
async def handle_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    premium_status = "✅" if user['is_premium'] else "❌"
    char_name = user.get('current_character', 'default').replace('_', ' ').title()
    text = TEXTS[lang]["profile"].format(
        id=user['id'], coins=user['coins'], premium=premium_status, refs=user['referrals_count'], char=char_name
    )
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["vip"], MENU_LABELS["en"]["vip"]]))
async def handle_vip(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["premium_info"], reply_markup=payment_options_keyboard(lang))

@user_router.message(F.text.in_([MENU_LABELS["ru"]["hype"], MENU_LABELS["en"]["hype"]]))
async def handle_hype(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["hype_prompts"], parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["tasks"], MENU_LABELS["en"]["tasks"]]))
async def handle_tasks(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    tasks = await db.get_active_tasks()
    await message.answer(TEXTS[lang]["tasks_title"], reply_markup=tasks_keyboard(tasks, lang), parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["lang"], MENU_LABELS["en"]["lang"]]))
async def handle_lang(message: Message):
    await message.answer("🌐 Choose language:", reply_markup=lang_keyboard())

@user_router.message(F.text.in_([MENU_LABELS["ru"]["help"], MENU_LABELS["en"]["help"]]))
async def handle_help(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["help"])

# --- State Handlers ---
@user_router.message(UserStates.waiting_for_nano_prompt)
async def process_nano_generation(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    if user['coins'] < 10:
        await message.answer(TEXTS[lang]["no_coins"])
        await state.clear()
        return
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    try:
        image_url = await generate_image(message.text, style="banana")
        await message.answer_photo(photo=image_url, caption=f"🍌 Nano Banana Trend: {message.text[:100]}")
        await db.update_user_coins(message.from_user.id, -10)
    except Exception as e:
        logger.error(f"Error in banana generation: {e}")
        await message.answer(TEXTS[lang]["error"])
    await state.clear()

@user_router.message(UserStates.waiting_for_vision_image, F.photo)
async def process_vision_image(message: Message, state: FSMContext):
    photo: PhotoSize = message.photo[-1]
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["generating_image"])
    try:
        file = await message.bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    prompt = await analyze_image_and_chat("Create a highly detailed AI generation prompt for this image. Output ONLY the prompt text.", image_bytes)
                    await message.answer(f"✅ <b>Generated Prompt:</b>\n\n<code>{prompt}</code>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in vision: {e}")
        await message.answer(TEXTS[lang]["error"])
    await state.clear()

@user_router.message(F.text)
async def handle_chat(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    char = user.get('current_character', 'default')
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        history = await db.get_chat_history(message.from_user.id)
        response = await get_chat_response(message.text, history, character=char)
        await db.save_conversation(message.from_user.id, message.text, response)
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_chat: {e}")
        await message.answer(TEXTS[lang]["error"])
