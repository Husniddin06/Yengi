
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_ID, SPB_PAYMENT_LINK
from database import db
from utils.openai_utils import get_chat_response, generate_image

user_router = Router()

class UserStates(StatesGroup):
    chatting = State()
    waiting_for_payment_confirmation = State()
    waiting_for_image_prompt = State()

# --- Localization dictionaries ---
# Uzbek
UZ_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Assalomu alaykum, {name}! 👋 SmartAI botga xush kelibsiz.\n\nMen sizning shaxsiy AI yordamchingizman. Men bilan suhbatlashishingiz, savollar berishingiz va hatto rasmlar yaratishingiz mumkin.\n\nSizda kunlik {daily_limit} ta bepul so'rov mavjud. Premium obuna orqali cheksiz imkoniyatlarga ega bo'ling! ✨ /premium",
    "welcome_premium": lambda name: f"Assalomu alaykum, {name}! 👋 SmartAI botga xush kelibsiz.\n\nMen sizning shaxsiy AI yordamchingizman. Men bilan suhbatlashishingiz, savollar berishingiz va hatto rasmlar yaratishingiz mumkin.\n\nSiz premium foydalanuvchisiz va cheksiz imkoniyatlarga egasiz! 🚀",
    "premium_exists": lambda until: f"Sizda allaqachon premium obuna mavjud. Obunangiz {until} gacha amal qiladi. 🗓️",
    "choose_premium": "Premium obunani tanlang: 👇",
    "payment_info": lambda period, amount, link: f"Siz {period} uchun {amount} RUB miqdorida premium obuna sotib olmoqchisiz.\n\nTo'lovni amalga oshirish uchun quyidagi SPB havolasidan foydalaning: 🔗 {link}\n\nTo'lovni amalga oshirganingizdan so'ng, 'To'ladim' tugmasini bosing. Admin to'lovingizni tasdiqlagandan so'ng, premium obunangiz faollashadi. ✅",
    "payment_received": "To'lovingiz qabul qilindi va admin tasdiqlashini kutmoqda. Rahmat! 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"Sizning balansingiz: 📊\nStatus: {status}\nKunlik limit: {daily_limit}\nPremium gacha: {premium_until}",
    "not_registered": "Siz ro'yxatdan o'tmagansiz. /start buyrug'ini bosing. ↩️",
    "referral_info": lambda link, count: f"Sizning referral havolangiz: 🤝 {link}\n\nSiz {count} ta do'stingizni taklif qildingiz. 3 ta do'st taklif qilsangiz, 7 kunlik premium olasiz! 🎁",
    "awaiting_response": "Javob kutilmoqda... ⏳",
    "daily_limit_exceeded": "Sizning kunlik limitingiz tugadi. Premium obuna sotib oling yoki ertaga qayta urinib ko'ring. /premium 😔",
    "premium_only_feature": "Faqat premium foydalanuvchilar bu funksiyadan foydalana oladi. /premium 🚫",
    "image_prompt_request": "Iltimos, rasm yaratish uchun tavsif bering: 🖼️",
    "image_generating": "Rasm yaratilmoqda... 🎨",
    "image_error": lambda error: f"Rasm yaratishda xatolik yuz berdi: {error} ❌",
    "image_ready": "Sizning rasmingiz tayyor! ✨",
    "referrer_premium_granted": "🎉 Siz 3 ta do'stingizni taklif qildingiz va 7 kunlik premium obunaga ega bo'ldingiz!",
    "payment_approved_user": lambda until: f"Tabriklaymiz! Sizning premium obunangiz faollashdi va {until} gacha amal qiladi. 🎉",
    "error_occurred": "Kechirasiz, kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring. 😔",
    "unlimited": "Cheksiz",
    "7_days": "7 kun (50 RUB)",
    "1_month": "1 oy (150 RUB)",
    "3_months": "3 oy (350 RUB)",
    "paid_button": "To'ladim"
}

# Russian
RU_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Здравствуйте, {name}! 👋 Добро пожаловать в SmartAI бот.\n\nЯ ваш личный AI-помощник. Вы можете общаться со мной, задавать вопросы и даже создавать изображения.\n\nУ вас есть {daily_limit} бесплатных запросов в день. Получите неограниченные возможности с премиум-подпиской! ✨ /premium",
    "welcome_premium": lambda name: f"Здравствуйте, {name}! 👋 Добро пожаловать в SmartAI бот.\n\nЯ ваш личный AI-помощник. Вы можете общаться со мной, задавать вопросы и даже создавать изображения.\n\nВы являетесь премиум-пользователем и имеете неограниченные возможности! 🚀",
    "premium_exists": lambda until: f"У вас уже есть премиум-подписка. Ваша подписка действует до {until}. 🗓️",
    "choose_premium": "Выберите премиум-подписку: 👇",
    "payment_info": lambda period, amount, link: f"Вы собираетесь приобрести премиум-подписку на {period} за {amount} RUB.\n\nДля совершения платежа используйте следующую ссылку СБП: 🔗 {link}\n\nПосле совершения платежа нажмите кнопку 'Я оплатил'. После подтверждения администратором ваша премиум-подписка будет активирована. ✅",
    "payment_received": "Ваш платеж принят и ожидает подтверждения администратором. Спасибо! 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"Ваш баланс: 📊\nСтатус: {status}\nЕжедневный лимит: {daily_limit}\nПремиум до: {premium_until}",
    "not_registered": "Вы не зарегистрированы. Нажмите /start. ↩️",
    "referral_info": lambda link, count: f"Ваша реферальная ссылка: 🤝 {link}\n\nВы пригласили {count} друзей. Пригласите 3 друзей и получите 7 дней премиума! 🎁",
    "awaiting_response": "Ожидаю ответа... ⏳",
    "daily_limit_exceeded": "Ваш ежедневный лимит исчерпан. Приобретите премиум-подписку или попробуйте снова завтра. /premium 😔",
    "premium_only_feature": "Только премиум-пользователи могут использовать эту функцию. /premium 🚫",
    "image_prompt_request": "Пожалуйста, опишите изображение, которое вы хотите создать: 🖼️",
    "image_generating": "Генерирую изображение... 🎨",
    "image_error": lambda error: f"Произошла ошибка при создании изображения: {error} ❌",
    "image_ready": "Ваше изображение готово! ✨",
    "referrer_premium_granted": "🎉 Вы пригласили 3 друзей и получили 7 дней премиум-подписки!",
    "payment_approved_user": lambda until: f"Поздравляем! Ваша премиум-подписка активирована и действует до {until}. 🎉",
    "error_occurred": "Извините, произошла непредвиденная ошибка. Пожалуйста, попробуйте позже. 😔",
    "unlimited": "Безлимитный",
    "7_days": "7 дней (50 RUB)",
    "1_month": "1 месяц (150 RUB)",
    "3_months": "3 месяца (350 RUB)",
    "paid_button": "Я оплатил"
}

# English
EN_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Hello, {name}! 👋 Welcome to SmartAI bot.\n\nI am your personal AI assistant. You can chat with me, ask questions, and even create images.\n\nYou have {daily_limit} free requests per day. Get unlimited possibilities with a premium subscription! ✨ /premium",
    "welcome_premium": lambda name: f"Hello, {name}! 👋 Welcome to SmartAI bot.\n\nI am your personal AI assistant. You can chat with me, ask questions, and even create images.\n\nYou are a premium user and have unlimited possibilities! 🚀",
    "premium_exists": lambda until: f"You already have a premium subscription. Your subscription is valid until {until}. 🗓️",
    "choose_premium": "Choose a premium subscription: 👇",
    "payment_info": lambda period, amount, link: f"You are about to purchase a premium subscription for {period} for {amount} RUB.\n\nTo make a payment, use the following SPB link: 🔗 {link}\n\nAfter making the payment, click the 'I have paid' button. Your premium subscription will be activated after admin confirmation. ✅",
    "payment_received": "Your payment has been received and is awaiting admin confirmation. Thank you! 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"Your balance: 📊\nStatus: {status}\nDaily limit: {daily_limit}\nPremium until: {premium_until}",
    "not_registered": "You are not registered. Please type /start. ↩️",
    "referral_info": lambda link, count: f"Your referral link: 🤝 {link}\n\n You have invited {count} friends. Invite 3 friends and get 7 days of premium! 🎁",
    "awaiting_response": "Awaiting response... ⏳",
    "daily_limit_exceeded": "Your daily limit has been exceeded. Purchase a premium subscription or try again tomorrow. /premium 😔",
    "premium_only_feature": "Only premium users can use this feature. /premium 🚫",
    "image_prompt_request": "Please provide a description for the image you want to create: 🖼️",
    "image_generating": "Generating image... 🎨",
    "image_error": lambda error: f"An error occurred while generating the image: {error} ❌",
    "image_ready": "Your image is ready! ✨",
    "referrer_premium_granted": "🎉 You have invited 3 friends and received a 7-day premium subscription!",
    "payment_approved_user": lambda until: f"Congratulations! Your premium subscription has been activated and is valid until {until}. 🎉",
    "error_occurred": "Sorry, an unexpected error occurred. Please try again later. 😔",
    "unlimited": "Unlimited",
    "7_days": "7 days (50 RUB)",
    "1_month": "1 month (150 RUB)",
    "3_months": "3 months (350 RUB)",
    "paid_button": "I have paid"
}

MESSAGE_MAP = {
    "uz": UZ_MESSAGES,
    "ru": RU_MESSAGES,
    "en": EN_MESSAGES
}

def get_message(lang_code, key, *args, **kwargs):
    return MESSAGE_MAP.get(lang_code, EN_MESSAGES).get(key, EN_MESSAGES[key])(*args, **kwargs)


@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language_code = message.from_user.language_code if message.from_user.language_code in MESSAGE_MAP else "en"

    referred_by = None
    if message.get_args():
        try:
            referred_by = int(message.get_args())
            if referred_by == user_id:
                referred_by = None # User cannot refer themselves
        except ValueError:
            pass

    await db.add_user(user_id, username, first_name, last_name, language_code, referred_by)
    user = await db.get_user(user_id)

    if referred_by and referred_by != user_id:
        await db.add_referral(referred_by, user_id)
        await db.increment_referrals_count(referred_by)
        # Check if referrer gets premium
        referrer = await db.get_user(referred_by)
        if referrer and referrer["referrals_count"] >= 3 and not referrer["is_premium"]:
            premium_until = datetime.now() + timedelta(days=7)
            await db.update_user_premium(referred_by, True, premium_until)
            await message.bot.send_message(referred_by, get_message(referrer["language_code"], "referrer_premium_granted"))

    if user and user["is_premium"]:
        welcome_text = get_message(language_code, "welcome_premium", first_name)
    else:
        welcome_text = get_message(language_code, "welcome", first_name, user["daily_limit"] if user else 10)

    await message.answer(welcome_text)
    await state.set_state(UserStates.chatting)

@user_router.message(Command("premium"))
async def cmd_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if user and user["is_premium"] and user["premium_until"] and datetime.strptime(str(user["premium_until"]), "%Y-%m-%d %H:%M:%S.%f") > datetime.now():
        premium_until = datetime.strptime(str(user["premium_until"]), "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M")
        await message.answer(get_message(language_code, "premium_exists", premium_until))
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message(language_code, "7_days"), callback_data="buy_premium_7_days")],
        [types.InlineKeyboardButton(text=get_message(language_code, "1_month"), callback_data="buy_premium_1_month")],
        [types.InlineKeyboardButton(text=get_message(language_code, "3_months"), callback_data="buy_premium_3_months")]
    ])
    await message.answer(get_message(language_code, "choose_premium"), reply_markup=keyboard)

@user_router.callback_query(F.data.startswith("buy_premium_"))
async def process_premium_purchase(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    period_data = callback.data.split("_")
    period_value = period_data[2]
    period_unit = period_data[3] if len(period_data) > 3 else "days"

    amount = 0
    period_str = ""
    if period_value == "7" and period_unit == "days":
        amount = 50
        period_str = get_message(language_code, "7_days").split(" (")[0]
    elif period_value == "1" and period_unit == "month":
        amount = 150
        period_str = get_message(language_code, "1_month").split(" (")[0]
    elif period_value == "3" and period_unit == "months":
        amount = 350
        period_str = get_message(language_code, "3_months").split(" (")[0]
    else:
        await callback.message.answer(get_message(language_code, "error_occurred"))
        await callback.answer()
        return

    payment_text = get_message(language_code, "payment_info", period_str, amount, SPB_PAYMENT_LINK)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message(language_code, "paid_button"), callback_data=f"payment_done_{amount}_{period_value}_{period_unit}")]
    ])

    await callback.message.answer(payment_text, reply_markup=keyboard)
    await state.set_state(UserStates.waiting_for_payment_confirmation)
    await callback.answer()

@user_router.callback_query(F.data.startswith("payment_done_"), UserStates.waiting_for_payment_confirmation)
async def payment_done(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    data = callback.data.split("_")
    amount = float(data[2])
    period_value = data[3]
    period_unit = data[4]
    period = f"{period_value} {period_unit}"

    payment_id = await db.add_payment(user_id, amount, "RUB", "pending", period)

    await callback.message.answer(get_message(language_code, "payment_received"))
    await callback.answer()
    await state.set_state(UserStates.chatting)

    # Notify admin
    admin_message = (
        f"Yangi to'lov! 💰\n"
        f"User ID: {user_id}\n"
        f"Username: @{callback.from_user.username if callback.from_user.username else 'N/A'}\n"
        f"Miqdor: {amount} RUB\n"
        f"Davr: {period}\n"
        f"To'lov ID: {payment_id}"
    )
    approve_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message("en", "approve_button"), callback_data=f"approve_payment_{payment_id}_{user_id}_{period_value}_{period_unit}")],
        [types.InlineKeyboardButton(text=get_message("en", "reject_button"), callback_data=f"reject_payment_{payment_id}")]
    ])
    await callback.bot.send_message(ADMIN_ID, admin_message, reply_markup=approve_keyboard)

@user_router.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if user:
        status = "Premium" if user["is_premium"] else "Free"
        premium_until_str = "Yo'q"
        if user["premium_until"]:
            premium_until = datetime.strptime(str(user["premium_until"]), "%Y-%m-%d %H:%M:%S.%f")
            premium_until_str = premium_until.strftime("%Y-%m-%d %H:%M")

        daily_limit_display = user["daily_limit"] if not user["is_premium"] else get_message(language_code, "unlimited")

        await message.answer(
            get_message(language_code, "balance_info", status=status, daily_limit=daily_limit_display, premium_until=premium_until_str)
        )
    else:
        await message.answer(get_message(language_code, "not_registered"))

@user_router.message(Command("referral"))
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    referral_link = f"https://t.me/SmartAiibot?start={user_id}"
    referrals_count = user["referrals_count"] if user else 0

    await message.answer(
        get_message(language_code, "referral_info", link=referral_link, count=referrals_count)
    )

@user_router.message(F.text, UserStates.chatting)
async def handle_text_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if not user:
        await message.answer(get_message(language_code, "not_registered"))
        return

    if user["is_premium"] or user["daily_limit"] > 0:
        await message.answer(get_message(language_code, "awaiting_response"))
        
        # Get conversation history
        history = await db.get_conversation_history(user_id, limit=10) # Last 10 messages for context
        messages_for_openai = []
        for msg in history:
            messages_for_openai.append({"role": msg["role"], "content": msg["content"]})
        messages_for_openai.append({"role": "user", "content": message.text})

        response = await get_chat_response(messages_for_openai)
        await message.answer(response)

        # Save conversation history
        await db.add_conversation_message(user_id, "user", message.text)
        await db.add_conversation_message(user_id, "assistant", response)

        if not user["is_premium"]:
            await db.update_user_daily_limit(user_id, user["daily_limit"] - 1)
    else:
        await message.answer(get_message(language_code, "daily_limit_exceeded"))

@user_router.message(F.photo, UserStates.chatting)
async def handle_photo_message(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if not user or not user["is_premium"]:
        await message.answer(get_message(language_code, "premium_only_feature"))
        return

    await message.answer(get_message(language_code, "premium_only_feature")) # Placeholder for actual file analysis logic.

@user_router.message(F.document, UserStates.chatting)
async def handle_document_message(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if not user or not user["is_premium"]:
        await message.answer(get_message(language_code, "premium_only_feature"))
        return

    await message.answer(get_message(language_code, "premium_only_feature")) # Placeholder for actual file analysis logic.

@user_router.message(Command("image"))
async def cmd_image(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    if not user or not user["is_premium"]:
        await message.answer(get_message(language_code, "premium_only_feature"))
        return

    await message.answer(get_message(language_code, "image_prompt_request"))
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(UserStates.waiting_for_image_prompt, F.text)
async def generate_image_prompt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"

    await message.answer(get_message(language_code, "image_generating"))
    image_url = await generate_image(message.text)
    if image_url.startswith("Error"):
        await message.answer(get_message(language_code, "image_error", error=image_url))
    else:
        await message.answer_photo(photo=image_url, caption=get_message(language_code, "image_ready"))
    await state.set_state(UserStates.chatting)
