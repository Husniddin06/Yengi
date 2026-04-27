import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, PhotoSize, BufferedInputFile
from aiogram.filters import Command, CommandStart
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction

from bot.database import db
from bot.utils.openai_utils import get_chat_response, edit_image_with_face, transcribe_audio, generate_image
from bot.utils.keyboards import (
    main_reply_menu, lang_keyboard, payment_options_keyboard,
    admin_payment_confirm_keyboard, MENU_LABELS
)
from bot.config import ADMIN_ID

logger = logging.getLogger(__name__)
user_router = Router()

MAX_FACE_PHOTOS = 6

class UserStates(StatesGroup):
    waiting_for_face_swap_prompt = State()

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Я твой <b>MAX AI</b> ассистент.\n\n🚀 <b>Что я умею:</b>\n— Умный поиск в интернете (новости, цены).\n👁 Анализ фото и создание промтов.\n🎨 Nano Banana Trend (DALL-E 3).\n🎙 Голосовые сообщения в текст.\n🎭 <b>Face Identity (InstantID)</b>: Просто пришли фото, а затем описание!",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "profile": "👤 <b>Мой профиль:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Баланс: {coins} монет\n💎 Premium: {premium}\n👥 Друзей: {refs}\n🎭 Персонаж: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 монет сразу\n- Доступ к GPT-4o\n- Безлимитные запросы\nВыберите способ оплаты:",
        "help": "🆘 Помощь:\n/start - Перезапуск\nЧat с ботом БЕСПЛАТНЫЙ.\nNano Banana - 10 монет за фото.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nОтправьте описание для создания вирального бананового арта! (Например: 'кот-космонавт')",
        "generating_image": "🎨 Генерирую изображение (InstantID), пожалуйста подождите 20-40 сек...",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_coins": "❌ У вас недостаточно монет (нужно 10). Выполните задания или купите Premium.",
        "sbp_request_sent": "💳 Запрос на оплату через СБП отправлен админу. После перевода 75₽ на карту, админ подтвердит платеж и вам придет 150 монет.",
        "tasks_title": "🎁 <b>Задания:</b>\nВыполняйте задания и получайте монеты!",
        "tiktok_msg": "📱 <b>TikTok Режим:</b>\nДля прослушивания и скачивания музыки из TikTok используйте наш партнерский бот: @VkMuzicXbot",
        "hype_prompts": "🔥 <b>Хайп Промты для AI:</b>\n\n1. <code>Ultra-realistic cinematic night portrait of a cybernetic banana in Tokyo</code>\n2. <code>Funny banana minion style character as a CEO of a tech company</code>\n3. <code>3D render of a banana house in a tropical forest, 8k resolution</code>\n4. <code>Vintage oil painting of a banana philosopher thinking about life</code>\n\nСкопируйте и используйте в Nano Banana!",
        "char_set": "🎭 Персонаж изменен на: {name}",
        "vision_info": "📸 <b>Face Identity (InstantID):</b>\n1. Отправьте фото.\n2. Затем напишите описание (например: 'мафиози в Дубае').\nЯ создам арт, сохранив ваше лицо на 100%!",
        "voice_processing": "🎙 Обрабатываю голосовое сообщение...",
        "stars_title": "Premium + 150 монет",
        "stars_desc": "Активация Premium и начисление 150 монет.",
        "payment_success": "✅ Оплата прошла успешно! Вам начислено 150 монет и активирован Premium.",
        "photo_saved": "✅ Фото сохранено! Теперь напишите описание (промт) или используйте /make [промт]:",
        "referral_info": "👥 <b>Реферальная система:</b>\n\nПриглашайте друзей и получайте <b>5 монет</b> за каждого!\n\n🔗 Ваша ссылка:\n<code>https://t.me/{bot_username}?start={id}</code>",
        "image_error": "❌ Ошибка при создании изображения. Проверьте API ключи в Railway (OPENROUTER_API_KEY).",
    },
    "en": {
        "welcome": "👋 Hello! I am your <b>MAX AI</b> assistant.\n\n🚀 <b>What I can do:</b>\n— Smart Web Search (news, prices).\n👁 Photo analysis and prompt creation.\n🎨 Nano Banana Trend (DALL-E 3).\n🎙 Voice-to-Text conversion.\n🎭 <b>Face Identity (InstantID)</b>: Just send a photo, then a prompt!",
        "lang_set": "Language set to English 🇬🇧",
        "profile": "👤 <b>My Profile:</b>\n\n🆔 ID: <code>{id}</code>\n🪙 Balance: {coins} coins\n💎 Premium: {premium}\n👥 Friends: {refs}\n🎭 Character: {char}",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 coins instantly\n- GPT-4o access\n- Unlimited requests\nChoose payment method:",
        "help": "🆘 Help:\n/start - Restart\nChatting is FREE.\nNano Banana - 10 coins per photo.",
        "nano_prompt": "🎨 <b>Nano Banana Trend:</b>\nSend a description to create viral banana art! (e.g., 'astronaut cat')",
        "generating_image": "🎨 Generating image (InstantID), please wait 20-40 sec...",
        "error": "❌ An error occurred. Please try again later.",
        "no_coins": "❌ You don't have enough coins (need 10). Complete tasks or buy Premium.",
        "sbp_request_sent": "💳 SBP payment request sent to admin. After transferring 75₽, admin will confirm and you will receive 150 coins.",
        "tasks_title": "🎁 <b>Tasks:</b>\nComplete tasks and get coins!",
        "tiktok_msg": "📱 <b>TikTok Mode:</b>\nTo listen and download music from TikTok, use our partner bot: @VkMuzicXbot",
        "hype_prompts": "🔥 <b>Hype Prompts for AI:</b>\n\n1. <code>Ultra-realistic cinematic night portrait of a cybernetic banana in Tokyo</code>\n2. <code>Funny banana minion style character as a CEO of a tech company</code>\n3. <code>3D render of a banana house in a tropical forest, 8k resolution</code>\n4. <code>Vintage oil painting of a banana philosopher thinking about life</code>\n\nCopy and use in Nano Banana!",
        "char_set": "🎭 Character changed to: {name}",
        "vision_info": "📸 <b>Face Identity (InstantID):</b>\n1. Send a photo.\n2. Then write a description (e.g., 'mafia boss in Dubai').\nI will create art while keeping your face 100%!",
        "voice_processing": "🎙 Processing voice message...",
        "stars_title": "Premium + 150 Coins",
        "stars_desc": "Activate Premium and get 150 coins.",
        "payment_success": "✅ Payment successful! 150 coins added and Premium activated.",
        "photo_saved": "✅ Photo saved! Now write a description (prompt) or use /make [prompt]:",
        "referral_info": "👥 <b>Referral System:</b>\n\nInvite friends and get <b>5 coins</b> for each!\n\n🔗 Your link:\n<code>https://t.me/{bot_username}?start={id}</code>",
        "image_error": "❌ Error creating image. Please check API keys in Railway (OPENROUTER_API_KEY).",
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
            await db.update_user_coins(ref_id, 5)
            try:
                await message.bot.send_message(ref_id, "👥 Someone joined using your link! You got 5 coins.")
            except: pass
            
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

@user_router.message(F.text.in_([MENU_LABELS["ru"]["vision"], MENU_LABELS["en"]["vision"]]))
async def handle_vision(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["vision_info"], parse_mode="HTML")
    await state.set_state(UserStates.waiting_for_face_swap_prompt)

@user_router.message(F.text.in_([MENU_LABELS["ru"]["profile"], MENU_LABELS["en"]["profile"]]))
async def handle_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    premium_status = "✅" if user['is_premium'] else "❌"
    char_name = user.get('current_character', 'default').replace('_', ' ').title()
    text = TEXTS[lang]["profile"].format(
        id=user['id'], coins=user['coins'], premium=premium_status, refs=user['referrals_count'], char=char_name
    )
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["friends"], MENU_LABELS["en"]["friends"]]))
async def handle_friends(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    bot_info = await message.bot.get_me()
    text = TEXTS[lang]["referral_info"].format(bot_username=bot_info.username, id=user['id'])
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["vip"], MENU_LABELS["en"]["vip"]]))
async def handle_vip(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    await message.answer(TEXTS[lang]["premium_info"], reply_markup=payment_options_keyboard(lang), parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["hype"], MENU_LABELS["en"]["hype"]]))
async def handle_hype(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    await message.answer(TEXTS[lang]["hype_prompts"], parse_mode="HTML")

@user_router.message(F.text.in_([MENU_LABELS["ru"]["lang"], MENU_LABELS["en"]["lang"]]))
async def handle_lang(message: Message):
    await message.answer("🌐 Choose language / Выберите язык:", reply_markup=lang_keyboard())

@user_router.message(F.text.in_([MENU_LABELS["ru"]["help"], MENU_LABELS["en"]["help"]]))
async def handle_help(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    await message.answer(TEXTS[lang]["help"])

@user_router.callback_query(F.data.startswith("setlang_"))
async def set_language(cb: CallbackQuery):
    lang = cb.data.split("_")[1]
    await db.update_user_language(cb.from_user.id, lang)
    await cb.message.answer(TEXTS[lang]["lang_set"], reply_markup=main_reply_menu(lang))
    await cb.answer()

@user_router.callback_query(F.data == "pay_sbp_request")
async def pay_sbp_request(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    if not user: return
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
    if not user: return
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
    await db.update_user_premium(user_id, True, datetime.now() + timedelta(days=30))
    await db.update_user_coins(user_id, 150)
    user = await db.get_user(user_id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["payment_success"])

@user_router.message(F.photo)
async def process_vision_image(message: Message, state: FSMContext):
    photo: PhotoSize = message.photo[-1]
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    
    # Check if it's a payment screenshot
    caption_lower = (message.caption or "").lower().strip()
    if caption_lower in ("pay", "payment", "оплата", "to'lov", "tolov") or caption_lower.startswith(("/pay", "payment ")):
        payment_id = await db.add_payment(message.from_user.id, 75, "SBP_SCREENSHOT")
        await message.bot.send_photo(
            ADMIN_ID,
            photo.file_id,
            caption=(
                f"💳 <b>Payment screenshot</b>\n"
                f"User: @{message.from_user.username} (ID: {message.from_user.id})\n"
                f"Amount: 75₽"
            ),
            reply_markup=admin_payment_confirm_keyboard(payment_id),
            parse_mode="HTML",
        )
        await message.answer("✅ Payment sent for verification.")
        return

    data = await state.get_data()
    photo_paths = list(data.get("face_photo_paths") or [])
    
    if len(photo_paths) >= MAX_FACE_PHOTOS:
        msg = (
            f"⚠️ Maksimum {MAX_FACE_PHOTOS} ta rasm. Endi promp yozing."
            if lang == "ru" else
            f"⚠️ Maximum {MAX_FACE_PHOTOS} photos. Now write the prompt."
        )
        await message.answer(msg)
        return
        
    file = await message.bot.get_file(photo.file_id)
    idx = len(photo_paths) + 1
    file_path = f"face_{message.from_user.id}_{idx}.jpg"
    await message.bot.download_file(file.file_path, file_path)
    photo_paths.append(file_path)
    
    await state.update_data(face_photo_paths=photo_paths)
    await state.set_state(UserStates.waiting_for_face_swap_prompt)
    
    if lang == "ru":
        text = (
            f"✅ Фото {len(photo_paths)}/{MAX_FACE_PHOTOS} сохранено.\n"
            "Отправьте ещё фото для лучшего распознавания лица "
            "или напишите описание (промт), либо используйте /make [промт]."
        )
    else:
        text = (
            f"✅ Photo {len(photo_paths)}/{MAX_FACE_PHOTOS} saved.\n"
            "Send more photos for better face accuracy, "
            "or write a description (prompt), or use /make [prompt]."
        )
    await message.answer(text)

@user_router.message(Command("make"))
async def handle_make_command(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    prompt = message.text.replace("/make", "").strip()
    if not prompt:
        await message.answer("❌ Write prompt after /make")
        return
    data = await state.get_data()
    photo_paths = [p for p in (data.get("face_photo_paths") or []) if os.path.exists(p)]
    if not photo_paths:
        await message.answer("❌ First send a photo.")
        return
    await process_face_swap_logic(message, state, photo_paths, prompt)

@user_router.message(UserStates.waiting_for_face_swap_prompt)
async def process_face_swap_input(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"): return
    data = await state.get_data()
    photo_paths = [p for p in (data.get("face_photo_paths") or []) if os.path.exists(p)]
    await process_face_swap_logic(message, state, photo_paths, message.text)

async def process_face_swap_logic(message: Message, state: FSMContext, photo_paths, prompt: str):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    if not photo_paths:
        await message.answer("❌ First send a photo.")
        return
    if user['coins'] < 10:
        await message.answer(TEXTS[lang]["no_coins"])
        await state.clear()
        return
    
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    try:
        image_result = await edit_image_with_face(photo_paths, prompt)
        if image_result:
            caption = f"🎨 Generated via Replicate: {prompt[:100]}"
            if isinstance(image_result, (bytes, bytearray)):
                photo = BufferedInputFile(bytes(image_result), filename="result.png")
                await message.answer_photo(photo=photo, caption=caption)
            else:
                await message.answer_photo(photo=image_result, caption=caption)
            await db.update_user_coins(message.from_user.id, -10)
        else:
            raise Exception("Image generation returned empty result")
    except Exception as e:
        logger.error(f"Error in face swap: {e}")
        if str(message.from_user.id) == str(ADMIN_ID):
            await message.answer(f"❌ Admin Error Info: {str(e)}")
        await message.answer(TEXTS[lang]["image_error"])
    finally:
        # Keep photos for further /make commands if user wants
        pass

@user_router.message(F.voice)
async def handle_voice(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    await message.answer(TEXTS[lang]["voice_processing"])
    
    file = await message.bot.get_file(message.voice.file_id)
    file_path = f"voice_{message.from_user.id}_{message.voice.file_id}.ogg"
    await message.bot.download_file(file.file_path, file_path)
    
    text = await transcribe_audio(file_path)
    if os.path.exists(file_path): os.remove(file_path)
    
    if text:
        await message.answer(f"🎤: {text}")
        history = await db.get_chat_history(message.from_user.id)
        char = user.get('current_character', 'default')
        response = await get_chat_response(text, history, character=char)
        await message.answer(response, parse_mode=None)
        await db.save_conversation(message.from_user.id, text, response)
    else:
        await message.answer("❌ Could not transcribe audio.")

@user_router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user: return
    lang = user['language_code']
    
    if message.text in ["🇷🇺 Русский", "🇺🇸 English"]: return
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    history = await db.get_chat_history(message.from_user.id)
    char = user.get('current_character', 'default')
    response = await get_chat_response(message.text, history, character=char)
    await message.answer(response, parse_mode=None)
    await db.save_conversation(message.from_user.id, message.text, response)
