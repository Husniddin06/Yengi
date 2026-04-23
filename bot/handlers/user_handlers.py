import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from bot.database import db
from bot.utils.openai_utils import get_chat_response, generate_image
from bot.utils.keyboards import (
    main_menu, lang_keyboard, payment_options_keyboard,
    BTN_BALANCE, BTN_CLEAR, BTN_IMAGE, BTN_PREMIUM,
    BTN_HELP, BTN_REF, BTN_LANG, BTN_BONUS,
)

logger = logging.getLogger(__name__)
user_router = Router()

class UserStates(StatesGroup):
    waiting_for_image_prompt = State()

TEXTS = {
    "ru": {
        "welcome": "Привет! Я умный ИИ бот. Выберите язык или начните общение.",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "balance": "📊 Ваш баланс: {limit} запросов\n💎 Premium: {premium}",
        "premium_info": "💎 Premium дает безлимитные запросы и доступ к GPT-4o.\nВыберите способ оплаты:",
        "help": "🆘 Помощь:\n/start - Перезапуск\n/lang - Смена языка\nПросто отправьте текст для общения или нажмите 'Rasm' для генерации.",
        "history_cleared": "🗑 История диалога очищена.",
        "image_prompt": "🎨 Отправьте описание картинки, которую хотите создать.",
        "generating_image": "🎨 Генерирую изображение, пожалуйста подождите...",
        "bonus_claimed": "🎁 Вы получили бонус: +{amount} запросов!",
        "bonus_already": "❌ Вы уже получили бонус сегодня.",
        "ref_info": "👥 Приглашайте друзей и получайте бонусы!\nВаша ссылка: {link}\nВсего приглашено: {count}",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_limit": "❌ У вас закончились запросы. Купите Premium или подождите обновления.",
        "stars_title": "Premium на 1 месяц",
        "stars_desc": "Безлимитные запросы и доступ к GPT-4o на 30 дней.",
        "payment_success": "✅ Оплата прошла успешно! Premium активирован на 30 дней.",
    },
    "en": {
        "welcome": "Hello! I am a smart AI bot. Choose a language or start chatting.",
        "lang_set": "Language set to English 🇬🇧",
        "balance": "📊 Your balance: {limit} requests\n💎 Premium: {premium}",
        "premium_info": "💎 Premium gives unlimited requests and access to GPT-4o.\nChoose payment method:",
        "help": "🆘 Help:\n/start - Restart\n/lang - Change language\nJust send text to start chatting or click 'Image' to generate.",
        "history_cleared": "🗑 Conversation history cleared.",
        "image_prompt": "🎨 Send a description of the image you want to create.",
        "generating_image": "🎨 Generating image, please wait...",
        "bonus_claimed": "🎁 You received a bonus: +{amount} requests!",
        "bonus_already": "❌ You already claimed your bonus today.",
        "ref_info": "👥 Invite friends and get bonuses!\nYour link: {link}\nTotal invited: {count}",
        "error": "❌ An error occurred. Please try again later.",
        "no_limit": "❌ You have run out of requests. Buy Premium or wait for a reset.",
        "stars_title": "Premium for 1 Month",
        "stars_desc": "Unlimited requests and GPT-4o access for 30 days.",
        "payment_success": "✅ Payment successful! Premium activated for 30 days.",
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

@user_router.message(F.text.in_(BTN_REF))
async def show_ref(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    await message.answer(TEXTS[lang]["ref_info"].format(link=ref_link, count=user['referrals_count']))

@user_router.message(F.text.in_(BTN_PREMIUM))
async def show_premium(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["premium_info"], reply_markup=payment_options_keyboard(lang))

@user_router.callback_query(F.data == "pay_stars_1month")
async def pay_stars(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    prices = [LabeledPrice(label="XTR", amount=50)]
    await cb.message.answer_invoice(
        title=TEXTS[lang]["stars_title"],
        description=TEXTS[lang]["stars_desc"],
        prices=prices,
        provider_token="", # Empty for Telegram Stars
        payload="premium_1month",
        currency="XTR"
    )
    await cb.answer()

@user_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@user_router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    payload = message.successful_payment.invoice_payload
    if payload == "premium_1month":
        new_until = datetime.now() + timedelta(days=30)
        await db.update_user_premium(message.from_user.id, True, new_until)
        await message.answer(TEXTS[lang]["payment_success"])

@user_router.message(F.text.in_(BTN_IMAGE))
async def image_prompt_request(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["image_prompt"])
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(UserStates.waiting_for_image_prompt)
async def process_image_generation(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    
    if user['daily_limit'] <= 0 and not user['is_premium']:
        await message.answer(TEXTS[lang]["no_limit"])
        await state.clear()
        return

    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    
    try:
        image_url = await generate_image(message.text)
        await message.answer_photo(photo=image_url, caption=f"🎨: {message.text[:100]}")
        if not user['is_premium']:
            await db.update_user_limit(message.from_user.id, user['daily_limit'] - 1)
    except Exception as e:
        logger.error(f"Error in image generation: {e}")
        await message.answer(TEXTS[lang]["error"])
    
    await state.clear()

@user_router.message(F.text)
async def handle_message(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user: return
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
