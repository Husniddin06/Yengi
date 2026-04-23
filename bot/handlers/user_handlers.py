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
    tasks_keyboard, admin_payment_confirm_keyboard
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
        "profile": "👤 <b>Мой профиль:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Баланс: {coins} монет\n💎 Premium: {premium}\n👥 Друзей: {refs}",
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
    },
    "en": {
        "welcome": "👋 Hello! I am your personal AI assistant.\n\n— homework, posts, ideas.\n👁 Analyze photo — send a picture, and I'll tell you everything!\n🎨 Draw arts (Nano Banana) — avatars, covers.\n🎬 Face swap on photo (DeepFake) — coming soon!\n\n👇 Click the buttons below, don't be shy:",
        "lang_set": "Language set to English 🇬🇧",
        "profile": "👤 <b>My Profile:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Balance: {coins} coins\n💎 Premium: {premium}\n👥 Friends: {refs}",
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

@user_router.callback_query(F.data == "menu_lang")
async def menu_lang(cb: CallbackQuery):
    await cb.message.edit_text("Choose language / Выберите язык:", reply_markup=lang_keyboard())
    await cb.answer()

@user_router.callback_query(F.data.startswith("setlang_"))
async def set_language(cb: CallbackQuery):
    lang = cb.data.split("_")[1]
    await db.update_user_language(cb.from_user.id, lang)
    await cb.message.edit_text(TEXTS[lang]["lang_set"])
    await cb.message.answer(TEXTS[lang]["welcome"], reply_markup=main_inline_menu(lang))
    await cb.answer()

@user_router.callback_query(F.data == "menu_profile")
async def menu_profile(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    premium_status = "✅" if user['is_premium'] else "❌"
    text = TEXTS[lang]["profile"].format(
        id=user['id'], coins=user['coins'], premium=premium_status, refs=user['referrals_count']
    )
    await cb.message.edit_text(text, reply_markup=main_inline_menu(lang), parse_mode="HTML")
    await cb.answer()

@user_router.callback_query(F.data == "menu_tasks")
async def menu_tasks(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    tasks = await db.get_active_tasks()
    await cb.message.edit_text(TEXTS[lang]["tasks_title"], reply_markup=tasks_keyboard(tasks, lang), parse_mode="HTML")
    await cb.answer()

@user_router.callback_query(F.data.startswith("check_task_"))
async def check_task(cb: CallbackQuery):
    task_id = int(cb.data.split("_")[2])
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    
    # In a real bot, you would check if user is actually in the channel
    # For now, we assume they did it if they clicked check
    success = await db.complete_task(cb.from_user.id, task_id)
    if success:
        await cb.answer(TEXTS[lang]["task_completed"].format(reward=5), show_alert=True)
    else:
        await cb.answer(TEXTS[lang]["task_already"], show_alert=True)

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

@user_router.callback_query(F.data == "menu_vision")
async def menu_vision(cb: CallbackQuery, state: FSMContext):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.answer(TEXTS[lang]["vision_prompt"])
    await state.set_state(UserStates.waiting_for_vision_image)
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

@user_router.message(UserStates.waiting_for_vision_image, F.photo)
async def process_vision_image(message: Message, state: FSMContext):
    photo: PhotoSize = message.photo[-1]
    await state.update_data(photo_id=photo.file_id)
    await message.answer("📸 Photo received! Now send a prompt or description of what to do with it.")
    await state.set_state(UserStates.waiting_for_vision_prompt)

@user_router.message(UserStates.waiting_for_vision_prompt)
async def process_vision_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("photo_id")
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    try:
        # Get photo file
        file = await message.bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status == 200:
                    image_bytes = await resp.read()
                    # Analyze image and get a detailed prompt
                    analysis = await analyze_image_and_chat(f"Describe this image in detail for AI image generation, then add this modification: {message.text}", image_bytes)
                    # Generate new image based on analysis (Image-to-Image effect)
                    new_image_url = await generate_image(analysis, style="banana")
                    await message.answer_photo(photo=new_image_url, caption=f"🍌 Nano Banana (Image-to-Image): {message.text[:100]}")
                    await db.update_user_coins(message.from_user.id, -10)
    except Exception as e:
        logger.error(f"Error in vision generation: {e}")
        await message.answer(TEXTS[lang]["error"])
    
    await state.clear()

@user_router.callback_query(F.data == "menu_tariffs")
async def menu_tariffs(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    await cb.message.edit_text(TEXTS[lang]["premium_info"], reply_markup=payment_options_keyboard(lang))
    await cb.answer()

@user_router.callback_query(F.data == "pay_sbp_request")
async def pay_sbp_request(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    payment_id = await db.add_payment(cb.from_user.id, 75, "SBP")
    
    admin_text = f"💳 <b>New SBP Payment Request!</b>\nUser: {cb.from_user.full_name} (@{cb.from_user.username})\nID: {cb.from_user.id}\nAmount: 75₽\nPayment ID: {payment_id}"
    await cb.bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_payment_confirm_keyboard(payment_id))
    
    await cb.message.answer(TEXTS[lang]["sbp_request_sent"])
    await cb.answer()

@user_router.message(F.text)
async def handle_message(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        history = await db.get_chat_history(message.from_user.id)
        response = await get_chat_response(message.text, history)
        await db.save_conversation(message.from_user.id, message.text, response)
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await message.answer(TEXTS[lang]["error"])
