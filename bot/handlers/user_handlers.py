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
    BTN_HELP, BTN_REF, BTN_LANG, BTN_BONUS, BTN_BANANA,
)
from bot.config import ADMIN_ID

logger = logging.getLogger(__name__)
user_router = Router()

class UserStates(StatesGroup):
    waiting_for_image_prompt = State()
    waiting_for_banana_prompt = State()

TEXTS = {
    "ru": {
        "welcome": "Привет! Я умный ИИ бот. Выберите язык или начните общение.",
        "lang_set": "Язык изменен на Русский 🇷🇺",
        "balance": "📊 Ваш баланс: {coins} монет\n💎 Premium: {premium}\n🖼 Лимит Nano Image: {limit}/3",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 монет сразу\n- Доступ к GPT-4o\n- Безлимитные запросы\nВыберите способ оплаты:",
        "help": "🆘 Помощь:\n/start - Перезапуск\n/lang - Смена языка\nЧат с ботом БЕСПЛАТНЫЙ. Nano Image - 3 раза в день.",
        "history_cleared": "🗑 История диалога очищена.",
        "image_prompt": "🎨 Nano Image: Отправьте описание картинки (Лимит: 3 в день).",
        "banana_prompt": "🍌 Nano Banana: Отправьте описание для создания бананового арта!",
        "generating_image": "🎨 Генерирую изображение, пожалуйста подождите...",
        "bonus_claimed": "🎁 Вы получили бонус: +1 монета!",
        "bonus_already": "❌ Вы уже получили бонус сегодня.",
        "ref_info": "👥 Приглашайте друзей и получайте по 5 монет за каждого!\nВаша ссылка: {link}\nВсего приглашено: {count}",
        "error": "❌ Произошла ошибка. Попробуйте позже.",
        "no_image_limit": "❌ Вы исчерпали лимит Nano Image (3 в день).",
        "stars_title": "Premium + 150 монет",
        "stars_desc": "Активация Premium и начисление 150 монет.",
        "payment_success": "✅ Оплата прошла успешно! Вам начислено 150 монет и активирован Premium.",
        "sbp_request_sent": "💳 Запрос на оплату через СБП отправлен админу. После перевода 75₽ на карту, админ подтвердит платеж и вам придет 150 монет.",
    },
    "en": {
        "welcome": "Hello! I am a smart AI bot. Choose a language or start chatting.",
        "lang_set": "Language set to English 🇬🇧",
        "balance": "📊 Your balance: {coins} coins\n💎 Premium: {premium}\n🖼 Nano Image limit: {limit}/3",
        "premium_info": "💎 Premium (75₽ / 50⭐️):\n- 150 coins instantly\n- GPT-4o access\n- Unlimited requests\nChoose payment method:",
        "help": "🆘 Help:\n/start - Restart\n/lang - Change language\nChatting is FREE. Nano Image limit: 3 per day.",
        "history_cleared": "🗑 Conversation history cleared.",
        "image_prompt": "🎨 Nano Image: Send a description (Limit: 3 per day).",
        "banana_prompt": "🍌 Nano Banana: Send a description to create banana art!",
        "generating_image": "🎨 Generating image, please wait...",
        "bonus_claimed": "🎁 You received a bonus: +1 coin!",
        "bonus_already": "❌ You already claimed your bonus today.",
        "ref_info": "👥 Invite friends and get 5 coins for each!\nYour link: {link}\nTotal invited: {count}",
        "error": "❌ An error occurred. Please try again later.",
        "no_image_limit": "❌ You have reached your Nano Image limit (3 per day).",
        "stars_title": "Premium + 150 Coins",
        "stars_desc": "Activate Premium and get 150 coins.",
        "payment_success": "✅ Payment successful! 150 coins added and Premium activated.",
        "sbp_request_sent": "💳 SBP payment request sent to admin. After transferring 75₽, admin will confirm and you will receive 150 coins.",
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
    await message.answer(TEXTS[lang]["balance"].format(coins=user['coins'], premium=premium_status, limit=user['daily_image_limit']))

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
    success = await db.claim_daily_bonus(message.from_user.id, 1)
    if success:
        await message.answer(TEXTS[lang]["bonus_claimed"])
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

@user_router.callback_query(F.data == "pay_sbp_request")
async def pay_sbp_request(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    payment_id = await db.add_payment(cb.from_user.id, 75, "SBP")
    
    # Admin xabari
    from bot.utils.keyboards import admin_payment_confirm_keyboard
    admin_text = f"💳 <b>New SBP Payment Request!</b>\nUser: {cb.from_user.full_name} (@{cb.from_user.username})\nID: {cb.from_user.id}\nAmount: 75₽\nPayment ID: {payment_id}"
    await cb.bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_payment_confirm_keyboard(payment_id))
    
    await cb.message.answer(TEXTS[lang]["sbp_request_sent"])
    await cb.answer()

@user_router.callback_query(F.data == "pay_stars_1month")
async def pay_stars(cb: CallbackQuery):
    user = await db.get_user(cb.from_user.id)
    lang = user['language_code']
    prices = [LabeledPrice(label="XTR", amount=50)]
    await cb.message.answer_invoice(
        title=TEXTS[lang]["stars_title"],
        description=TEXTS[lang]["stars_desc"],
        prices=prices,
        provider_token="", 
        payload="premium_150coins",
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
    if payload == "premium_150coins":
        await db.update_user_coins(message.from_user.id, 150)
        new_until = datetime.now() + timedelta(days=30)
        await db.update_user_premium(message.from_user.id, True, new_until)
        await message.answer(TEXTS[lang]["payment_success"])

@user_router.message(F.text.in_(BTN_IMAGE))
async def image_prompt_request(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    if user['daily_image_limit'] <= 0:
        await message.answer(TEXTS[lang]["no_image_limit"])
        return
    await message.answer(TEXTS[lang]["image_prompt"])
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(F.text.in_(BTN_BANANA))
async def banana_prompt_request(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["banana_prompt"])
    await state.set_state(UserStates.waiting_for_banana_prompt)

@user_router.message(UserStates.waiting_for_image_prompt)
async def process_image_generation(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    try:
        image_url = await generate_image(message.text)
        await message.answer_photo(photo=image_url, caption=f"🎨 Nano Image: {message.text[:100]}")
        await db.update_user_image_limit(message.from_user.id, user['daily_image_limit'] - 1)
    except Exception as e:
        logger.error(f"Error in image generation: {e}")
        await message.answer(TEXTS[lang]["error"])
    await state.clear()

@user_router.message(UserStates.waiting_for_banana_prompt)
async def process_banana_generation(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user['language_code']
    await message.answer(TEXTS[lang]["generating_image"])
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO)
    try:
        banana_prompt = f"Banana style art: {message.text}"
        image_url = await generate_image(banana_prompt)
        await message.answer_photo(photo=image_url, caption=f"🍌 Nano Banana: {message.text[:100]}")
    except Exception as e:
        logger.error(f"Error in banana generation: {e}")
        await message.answer(TEXTS[lang]["error"])
    await state.clear()

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
