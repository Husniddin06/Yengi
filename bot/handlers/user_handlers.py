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
    main_inline_menu, lang_keyboard, payment_options_keyboard,
    tasks_keyboard, admin_payment_confirm_keyboard, characters_keyboard
)
from bot.config import ADMIN_ID

logger = logging.getLogger(__name__)
user_router = Router()

class UserStates(StatesGroup):
    waiting_for_nano_prompt = State()
    waiting_for_vision_image = State()
    waiting_for_vision_prompt = State()

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Я твой персональный ИИ ассистент.\n\n— домашка, посты, идеи.\n👁 Анализировать фото — скинь картинку, и я всё расскажу!\n🎨 Рисовать арты (Nano Banana) — аватарки, обложки.\n🎬 Замена лица на фото (DeepFake) — скоро!\n\n👇 Тыкай кнопки внизу, не стесняйся:",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "profile": "👤 <b>Мой профиль:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Баланс: {coins} монет\n💎 Premium: {premium}\n👥 Друзей: {refs}\n🎭 Персонаж: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 монет сразу\n- Доступ к GPT-4o\n- Безлимитные запросы\nВыберите способ оплаты:",
        "help": "🆘 Помощь:\n/start - Перезапуск\nЧat с ботом БЕСПЛАТНЫЙ.\nNano Banana - 10 монет за фото.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nОтправьте описание для создания вирального бананового арта! (Например: 'кот-космонавт')",
        "vision_prompt": "📸 Отправьте фото, которое нужно проанализировать или использовать как референс.",
        "generating_image": "🎨 Генерирую изображение, пожалуйста подождите...",
        "bonus_claimed": "🎁 Вы получили бонус: +1 монета!",
        "bonus_already": "❌ Вы уже получили бонус сегодня.",
        "ref_info": "👥 Приглашайте друзей и получайте по 5 монет за каждого!\nВаша ссылка: {link}\nВсего приглашено: {count}",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_coins": "❌ У вас недостаточно монет (нужно 10). Выполните задания или купите Premium.",
        "stars_title": "Premium + 150 монет",
        "stars_desc": "Активация Premium и начисление 150 монет.",
        "payment_success": "✅ Оплата прошла успешно! Вам начислено 150 монет и активирован Premium.",
        "sbp_request_sent": "💳 Запрос на оплату через СБП отправлен админу. После перевода 75₽ на карту, админ подтвердит платеж и вам придет 150 монет.",
        "tasks_title": "🎁 <b>Задания:</b>\nВыполняйте задания и получайте монеты!",
        "task_completed": "✅ Задание выполнено! Вам начислено {reward} монет.",
        "task_already": "❌ Вы уже получили награду за это задание.",
        "tiktok_msg": "📱 <b>TikTok Режим:</b>\nДля прослушивания и скачивания музыки из TikTok используйте наш партнерский бот: @VkMuzicXbot",
        "hype_prompts": "🔥 <b>Хайп Промты для AI:</b>\n\n1. <code>Ultra-realistic cinematic night portrait of a cybernetic banana in Tokyo</code>\n2. <code>Funny banana minion style character as a CEO of a tech company</code>\n3. <code>3D render of a banana house in a tropical forest, 8k resolution</code>\n4. <code>Vintage oil painting of a banana philosopher thinking about life</code>\n\nСкопируйте и используйте в Nano Banana!",
        "char_set": "🎭 Персонаж изменен на: {name}",
        "vision_info": "📸 <b>Prompt from Photo:</b>\nОтправьте фото, и я составлю для него идеальный промт для генерации похожих изображений!",
    },
    "en": {
        "welcome": "👋 Hello! I am your personal AI assistant.\n\n— homework, posts, ideas.\n👁 Analyze photo — send a picture, and I'll tell you everything!\n🎨 Draw arts (Nano Banana) — avatars, covers.\n🎬 Face swap on photo (DeepFake) — coming soon!\n\n👇 Click the buttons below, don't be shy:",
        "lang_set": "Language set to English 🇬🇧",
        "profile": "👤 <b>My Profile:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Balance: {coins} coins\n💎 Premium: {premium}\n👥 Friends: {refs}\n🎭 Character: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 coins instantly\n- GPT-4o access\n- Unlimited requests\nChoose payment method:",
        "help": "🆘 Help:\n/start - Restart\nChatting is FREE.\nNano Banana - 10 coins per photo.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nSend a description to create viral banana art! (e.g., 'astronaut cat')",
        "vision_prompt": "📸 Send a photo to analyze or use as a reference.",
        "generating_image": "🎨 Generating image, please wait...",
        "bonus_claimed": "🎁 You received a bonus: +1 coin!",
        "bonus_already": "❌ You already claimed your bonus today.",
        "ref_info": "👥 Invite friends and get 5 coins for each!\nYour link: {link}\nTotal invited: {count}",
        "error": "❌ An error occurred. Please try again later.",
        "no_coins": "❌ You don't have enough coins (need 10). Complete tasks or buy Premium.",
        "stars_title": "Premium + 150 Coins",
        "stars_desc": "Activate Premium and get 150 coins.",
        "payment_success": "✅ Payment successful! 150 coins added and Premium activated.",
        "sbp_request_sent": "💳 SBP payment request sent to admin. After transferring 75₽, admin will confirm and you will receive 150 coins.",
        "tasks_title": "🎁 <b>Tasks:</b>\nComplete tasks and get coins!",
        "task_completed": "✅ Task completed! You received {reward} coins.",
        "task_already": "❌ You already received a reward for this task.",
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
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_inline_menu(lang))

@user_router.callback_query(F.data == "menu_back")
async def menu_back(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.edit_text(TEXTS[lang]["welcome"], reply_markup=main_inline_menu(lang))
    await cb.answer()

@user_router.callback_query(F.data == "menu_tiktok")
async def menu_tiktok(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.answer(TEXTS[lang]["tiktok_msg"])
    await cb.answer()

@user_router.callback_query(F.data == "menu_hype")
async def menu_hype(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.answer(TEXTS[lang]["hype_prompts"], parse_mode="HTML")
    await cb.answer()

@user_router.callback_query(F.data == "menu_chars")
async def menu_chars(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.edit_text("🎭 Choose your AI Character:", reply_markup=characters_keyboard(lang))
    await cb.answer()

@user_router.callback_query(F.data.startswith("char_"))
async def set_character(cb: CallbackQuery):
    char = cb.data.split("_", 1)[1]
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await db.update_user_character(cb.from_user.id, char)
    
    char_names = {
        "funny_banana": "Funny Banana 🍌",
        "wise_advisor": "Wise Advisor 🧠",
        "art_designer": "Art Designer 🎨",
        "default": "Default AI 🤖"
    }
    name = char_names.get(char, "Default AI")
    await cb.message.edit_text(TEXTS[lang]["char_set"].format(name=name))
    await cb.message.answer(TEXTS[lang]["welcome"], reply_markup=main_inline_menu(lang))
    await cb.answer()

@user_router.callback_query(F.data == "menu_profile")
async def menu_profile(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    premium_status = "✅" if user['is_premium'] else "❌"
    char_name = user.get('current_character', 'default').replace('_', ' ').title()
    text = TEXTS[lang]["profile"].format(
        id=user['id'], coins=user['coins'], premium=premium_status, refs=user['referrals_count'], char=char_name
    )
    await cb.message.edit_text(text, reply_markup=main_inline_menu(lang), parse_mode="HTML")
    await cb.answer()

@user_router.callback_query(F.data == "menu_vision")
async def menu_vision(cb: CallbackQuery, state: FSMContext):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.answer(TEXTS[lang]["vision_info"], parse_mode="HTML")
    await state.set_state(UserStates.waiting_for_vision_image)
    await cb.answer()

@user_router.message(UserStates.waiting_for_vision_image, F.photo)
async def process_vision_image(message: Message, state: FSMContext):
    photo: PhotoSize = message.photo[-1]
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
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

@user_router.callback_query(F.data == "menu_nano")
async def menu_nano(cb: CallbackQuery, state: FSMContext):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    if user['coins'] < 10:
        await cb.answer(TEXTS[lang]["no_coins"], show_alert=True)
        return
    await cb.message.answer(TEXTS[lang]["nano_prompt"], parse_mode="HTML")
    await state.set_state(UserStates.waiting_for_nano_prompt)
    await cb.answer()

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

@user_router.message(F.text)
async def handle_message(message: Message):
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
        logger.error(f"Error in handle_message: {e}")
        await message.answer(TEXTS[lang]["error"])
