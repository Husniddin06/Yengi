import os
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, PhotoSize, ContentType
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from bot.database import db
from bot.utils.openai_utils import get_chat_response, generate_image, analyze_image_and_chat, transcribe_audio, edit_image_with_face
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
    waiting_for_face_swap_prompt = State()

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Я твой <b>MAX AI</b> ассистент.\n\n🚀 <b>Что я умею:</b>\n— Умный поиск в интернете (новости, цены).\n👁 Анализ фото и создание промтов.\n🎨 Nano Banana Trend (DALL-E 3).\n🎙 Голосовые сообщения в текст.\n🎭 <b>Face Identity</b>: Пришли фото, а затем описание!",
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
        "vision_info": "📸 <b>Face Identity / Prompt:</b>\n1. Отправьте фото.\n2. Затем напишите описание (например: 'в стиле киберпанк').\nЯ создам арт, сохранив ваше лицо!",
        "voice_processing": "🎙 Обрабатываю голосовое сообщение...",
        "stars_title": "Premium + 150 монет",
        "stars_desc": "Активация Premium и начисление 150 монет.",
        "payment_success": "✅ Оплата прошла успешно! Вам начислено 150 монет и активирован Premium.",
        "photo_saved": "✅ Фото сохранено! Теперь напишите описание (промт) для обработки:",
    },
    "en": {
        "welcome": "👋 Hello! I am your <b>MAX AI</b> assistant.\n\n🚀 <b>What I can do:</b>\n— Smart Web Search (news, prices).\n👁 Photo analysis and prompt creation.\n🎨 Nano Banana Trend (DALL-E 3).\n🎙 Voice-to-Text conversion.\n🎭 <b>Face Identity</b>: Send photo, then a prompt!",
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
        "vision_info": "📸 <b>Face Identity / Prompt:</b>\n1. Send a photo.\n2. Then write a description (e.g., 'cyberpunk style').\nI will create art while keeping your face!",
        "voice_processing": "🎙 Processing voice message...",
        "stars_title": "Premium + 150 Coins",
        "stars_desc": "Activate Premium and get 150 coins.",
        "payment_success": "✅ Payment successful! 150 coins added and Premium activated.",
        "photo_saved": "✅ Photo saved! Now write a description (prompt) for processing:",
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
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_reply_menu(lang), parse_mode="HTML")

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
    await message.answer(TEXTS[lang]["tiktok_msg"], parse_mode="HTML")

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
    await message.answer(TEXTS[lang]["premium_info"], reply_markup=payment_options_keyboard(lang), parse_mode="HTML")

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

# --- Payment Handlers ---
@user_router.callback_query(F.data == "pay_sbp_request")
async def pay_sbp_request(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    payment_id = await db.add_payment(cb.from_user.id, 75, "SBP")
    await cb.bot.send_message(
        ADMIN_ID,
        f"💳 <b>New SBP Payment Request</b>\nUser: {cb.from_user.username} (ID: {cb.from_user.id})\nAmount: 75₽\n\nUse /admin to confirm.",
        reply_markup=admin_payment_confirm_keyboard(payment_id)
    )
    await cb.message.answer(TEXTS[lang]["sbp_request_sent"])
    await cb.answer()

@user_router.callback_query(F.data == "pay_stars_1month")
async def pay_stars_1month(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    prices = [LabeledPrice(label="Premium", amount=50)]
    await cb.bot.send_invoice(
        chat_id=cb.from_user.id,
        title=TEXTS[lang]["stars_title"],
        description=TEXTS[lang]["stars_desc"],
        payload="premium_1month_stars",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    await cb.answer()

@user_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@user_router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    lang = user['language_code']
    await db.update_user_coins(user_id, 150)
    await db.update_user_premium(user_id, True, datetime.now() + timedelta(days=30))
    await message.answer(TEXTS[lang]["payment_success"])

# --- Voice Message Handler ---
@user_router.message(F.voice)
async def handle_voice(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["voice_processing"])
    try:
        file_id = message.voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = f"voice_{file_id}.ogg"
        await message.bot.download_file(file.file_path, file_path)
        text = await transcribe_audio(file_path)
        os.remove(file_path)
        if text:
            await message.answer(f"🎙 <b>Transcription:</b>\n\n{text}", parse_mode="HTML")
            history = await db.get_chat_history(message.from_user.id)
            response = await get_chat_response(text, history, character=user.get('current_character', 'default'))
            await db.save_conversation(message.from_user.id, text, response)
            await message.answer(response, parse_mode="Markdown")
        else:
            await message.answer(TEXTS[lang]["error"])
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        await message.answer(TEXTS[lang]["error"])

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
    
    # Save photo for Face Identity
    file = await message.bot.get_file(photo.file_id)
    file_path = f"face_{message.from_user.id}.jpg"
    await message.bot.download_file(file.file_path, file_path)
    
    await state.update_data(face_photo_path=file_path)
    await message.answer(TEXTS[lang]["photo_saved"])
    await state.set_state(UserStates.waiting_for_face_swap_prompt)

@user_router.message(UserStates.waiting_for_face_swap_prompt)
async def process_face_swap(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    if user['coins'] < 10:
        await message.answer(TEXTS[lang]["no_coins"])
        await state.clear()
        return
        
    data = await state.get_data()
    photo_path = data.get("face_photo_path")
    
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    try:
        image_url = await edit_image_with_face(photo_path, message.text)
        await message.answer_photo(photo=image_url, caption=f"🎭 Face Identity: {message.text[:100]}")
        await db.update_user_coins(message.from_user.id, -10)
    except Exception as e:
        logger.error(f"Error in face swap: {e}")
        await message.answer(TEXTS[lang]["error"])
    finally:
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
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
