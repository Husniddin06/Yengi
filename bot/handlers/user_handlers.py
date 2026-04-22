from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction
from datetime import datetime, timedelta
from config import ADMIN_ID, SPB_PAYMENT_LINK, DAILY_BONUS
from database import db
from utils.openai_utils import get_chat_response, generate_image
from utils.text_utils import split_message, markdown_to_html
from utils.keyboards import (
    main_menu, lang_keyboard,
    BTN_BALANCE, BTN_PREMIUM, BTN_REF, BTN_HELP, BTN_CLEAR,
    BTN_IMAGE, BTN_LANG, BTN_BONUS,
)

user_router = Router()

class UserStates(StatesGroup):
    chatting = State()
    waiting_for_payment_confirmation = State()
    waiting_for_image_prompt = State()

# ---------------- Localization ----------------
UZ_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Assalomu alaykum, {name}! 👋 SmartAI botga xush kelibsiz.\n\nMen sizning shaxsiy AI yordamchingizman. Savol bering, suhbatlashing yoki rasm yarating.\n\nKunlik {daily_limit} ta bepul so'rov bor. Cheksiz uchun /premium ✨",
    "welcome_premium": lambda name: f"Assalomu alaykum, {name}! 👋 Siz premium foydalanuvchisiz — cheksiz imkoniyatlar! 🚀",
    "premium_exists": lambda until: f"Sizda allaqachon premium mavjud. {until} gacha amal qiladi. 🗓️",
    "choose_premium": "Premium obunani tanlang: 👇",
    "payment_info": lambda period, amount, link: f"Siz {period} uchun {amount} RUB miqdorida premium sotib olmoqchisiz.\n\nTo'lovni amalga oshiring: 🔗 {link}\n\nKeyin 'To'ladim' tugmasini bosing. ✅",
    "payment_received": "To'lovingiz qabul qilindi va tasdiqlash kutilmoqda. 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"📊 Balans:\nStatus: {status}\nKunlik limit: {daily_limit}\nPremium gacha: {premium_until}",
    "not_registered": "Avval /start buyrug'ini bosing. ↩️",
    "referral_info": lambda link, count: f"🤝 Sizning referral havolangiz:\n{link}\n\nSiz {count} ta do'st taklif qildingiz. 3 ta = 7 kunlik premium! 🎁",
    "daily_limit_exceeded": "Kunlik limit tugadi. /premium yoki /bonus 😔",
    "premium_only_feature": "Bu funksiya faqat premium uchun. /premium 🚫",
    "image_prompt_request": "Rasm uchun tavsif bering: 🖼️",
    "image_generating": "Rasm yaratilmoqda... 🎨",
    "image_error": lambda error: f"Rasm xatosi: {error} ❌",
    "image_ready": "Rasm tayyor! ✨",
    "referrer_premium_granted": "🎉 3 ta do'st taklif qildingiz va 7 kunlik premium oldingiz!",
    "payment_approved_user": lambda until: f"🎉 Premium faollashdi, {until} gacha amal qiladi.",
    "error_occurred": "Kutilmagan xatolik. Keyinroq urinib ko'ring. 😔",
    "unlimited": "Cheksiz",
    "7_days": "7 kun (50 RUB)",
    "1_month": "1 oy (150 RUB)",
    "3_months": "3 oy (350 RUB)",
    "paid_button": "To'ladim",
    "help": (
        "<b>SmartAI — yordam</b>\n\n"
        "💬 Oddiy yozing — AI javob beradi\n"
        "🎨 /image — rasm yaratish (Pollinations)\n"
        "📊 /balance — balansingiz\n"
        "💎 /premium — premium obuna\n"
        "👥 /referral — do'stlarni taklif qilish\n"
        "🎁 /bonus — kunlik bepul so'rov bonusi\n"
        "🎟 /promo CODE — promokod kiritish\n"
        "🗑 /clear — suhbatni tozalash\n"
        "🌐 /lang — til almashtirish\n"
        "🆘 /help — bu yordam"
    ),
    "cleared": "Suhbat tarixi tozalandi. ✅",
    "choose_lang": "Tilni tanlang: 🌐",
    "lang_set": "Til o'zgartirildi. ✅",
    "bonus_claimed": lambda n: f"🎁 Sizga {n} ta qo'shimcha so'rov berildi!",
    "bonus_already": "Bugungi bonusni allaqachon olgansiz. Ertaga qayting. ⏰",
    "promo_usage": "Foydalanish: <code>/promo CODE</code>",
    "promo_invalid": "Bunday promokod yo'q yoki muddati tugagan. ❌",
    "promo_already": "Bu promokoddan allaqachon foydalangansiz. 🔁",
    "promo_success": lambda days, reqs: f"✅ Promokod qo'llanildi! Premium kunlari: +{days}, qo'shimcha so'rov: +{reqs}",
    "typing_now": "✍️ Yozyapman...",
}

RU_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Здравствуйте, {name}! 👋 Добро пожаловать в SmartAI.\n\nЯ ваш AI-помощник. Задавайте вопросы или создавайте картинки.\n\nУ вас {daily_limit} бесплатных запросов. Безлимит: /premium ✨",
    "welcome_premium": lambda name: f"Здравствуйте, {name}! 👋 Вы премиум — безлимит! 🚀",
    "premium_exists": lambda until: f"У вас уже есть премиум до {until}. 🗓️",
    "choose_premium": "Выберите подписку: 👇",
    "payment_info": lambda period, amount, link: f"Премиум на {period} за {amount} RUB.\n\nОплатите: 🔗 {link}\n\nЗатем нажмите 'Я оплатил'. ✅",
    "payment_received": "Платеж получен и ждёт подтверждения. 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"📊 Баланс:\nСтатус: {status}\nДневной лимит: {daily_limit}\nПремиум до: {premium_until}",
    "not_registered": "Сначала нажмите /start. ↩️",
    "referral_info": lambda link, count: f"🤝 Ваша ссылка:\n{link}\n\nПриглашено: {count}. 3 друга = 7 дней премиума! 🎁",
    "daily_limit_exceeded": "Дневной лимит исчерпан. /premium или /bonus 😔",
    "premium_only_feature": "Только для премиум. /premium 🚫",
    "image_prompt_request": "Опишите картинку: 🖼️",
    "image_generating": "Генерирую... 🎨",
    "image_error": lambda error: f"Ошибка: {error} ❌",
    "image_ready": "Готово! ✨",
    "referrer_premium_granted": "🎉 Вы пригласили 3 друзей и получили 7 дней премиума!",
    "payment_approved_user": lambda until: f"🎉 Премиум активирован до {until}.",
    "error_occurred": "Ошибка. Попробуйте позже. 😔",
    "unlimited": "Безлимит",
    "7_days": "7 дней (50 RUB)",
    "1_month": "1 месяц (150 RUB)",
    "3_months": "3 месяца (350 RUB)",
    "paid_button": "Я оплатил",
    "help": (
        "<b>SmartAI — помощь</b>\n\n"
        "💬 Просто пишите — AI ответит\n"
        "🎨 /image — генерация картинки\n"
        "📊 /balance — баланс\n"
        "💎 /premium — премиум\n"
        "👥 /referral — пригласить друзей\n"
        "🎁 /bonus — ежедневный бонус\n"
        "🎟 /promo CODE — промокод\n"
        "🗑 /clear — очистить историю\n"
        "🌐 /lang — сменить язык\n"
        "🆘 /help — помощь"
    ),
    "cleared": "История очищена. ✅",
    "choose_lang": "Выберите язык: 🌐",
    "lang_set": "Язык изменён. ✅",
    "bonus_claimed": lambda n: f"🎁 Вам начислено +{n} запросов!",
    "bonus_already": "Бонус уже получен сегодня. ⏰",
    "promo_usage": "Использование: <code>/promo CODE</code>",
    "promo_invalid": "Промокод не найден или истёк. ❌",
    "promo_already": "Вы уже использовали этот промокод. 🔁",
    "promo_success": lambda days, reqs: f"✅ Промокод применён! Премиум +{days} дн., запросов +{reqs}",
    "typing_now": "✍️ Печатаю...",
}

EN_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Hello, {name}! 👋 Welcome to SmartAI.\n\nI'm your AI assistant. Chat or generate images.\n\nYou have {daily_limit} free requests. Unlimited: /premium ✨",
    "welcome_premium": lambda name: f"Hello, {name}! 👋 You are premium — unlimited access! 🚀",
    "premium_exists": lambda until: f"You already have premium until {until}. 🗓️",
    "choose_premium": "Choose a subscription: 👇",
    "payment_info": lambda period, amount, link: f"Premium for {period} = {amount} RUB.\n\nPay here: 🔗 {link}\n\nThen tap 'I paid'. ✅",
    "payment_received": "Payment received, awaiting admin confirmation. 🙏",
    "balance_info": lambda status, daily_limit, premium_until: f"📊 Balance:\nStatus: {status}\nDaily limit: {daily_limit}\nPremium until: {premium_until}",
    "not_registered": "Please type /start first. ↩️",
    "referral_info": lambda link, count: f"🤝 Your referral link:\n{link}\n\nInvited: {count}. 3 friends = 7 days premium! 🎁",
    "daily_limit_exceeded": "Daily limit reached. /premium or /bonus 😔",
    "premium_only_feature": "Premium-only feature. /premium 🚫",
    "image_prompt_request": "Describe the image: 🖼️",
    "image_generating": "Generating... 🎨",
    "image_error": lambda error: f"Error: {error} ❌",
    "image_ready": "Ready! ✨",
    "referrer_premium_granted": "🎉 You invited 3 friends and got 7 days of premium!",
    "payment_approved_user": lambda until: f"🎉 Premium activated until {until}.",
    "error_occurred": "Error. Try again later. 😔",
    "unlimited": "Unlimited",
    "7_days": "7 days (50 RUB)",
    "1_month": "1 month (150 RUB)",
    "3_months": "3 months (350 RUB)",
    "paid_button": "I paid",
    "help": (
        "<b>SmartAI — help</b>\n\n"
        "💬 Just type — AI answers\n"
        "🎨 /image — generate image\n"
        "📊 /balance — your balance\n"
        "💎 /premium — premium plans\n"
        "👥 /referral — invite friends\n"
        "🎁 /bonus — daily bonus\n"
        "🎟 /promo CODE — redeem promo\n"
        "🗑 /clear — clear chat history\n"
        "🌐 /lang — change language\n"
        "🆘 /help — this help"
    ),
    "cleared": "Conversation cleared. ✅",
    "choose_lang": "Choose language: 🌐",
    "lang_set": "Language changed. ✅",
    "bonus_claimed": lambda n: f"🎁 +{n} extra requests added!",
    "bonus_already": "Bonus already claimed today. ⏰",
    "promo_usage": "Usage: <code>/promo CODE</code>",
    "promo_invalid": "Promo not found or expired. ❌",
    "promo_already": "You already used this promo. 🔁",
    "promo_success": lambda days, reqs: f"✅ Promo applied! Premium +{days} days, requests +{reqs}",
    "typing_now": "✍️ Typing...",
}

MESSAGE_MAP = {"uz": UZ_MESSAGES, "ru": RU_MESSAGES, "en": EN_MESSAGES}

ADMIN_MESSAGES = {
    "admin_welcome": lambda: "Admin panel: 👇",
    "stats_button": lambda: "📊 Statistics",
    "broadcast_button": lambda: "📣 Broadcast",
    "payments_button": lambda: "💳 Pending payments",
    "user_management_button": lambda: "👥 User management",
    "admin_stats": lambda total_users, premium_users: f"Total users: {total_users}\nPremium users: {premium_users}",
    "broadcast_prompt": lambda: "Send the message to broadcast to all users:",
    "broadcast_sent": lambda: "Broadcast sent. ✅",
    "no_pending_payments": lambda: "No pending payments.",
    "new_payment_admin": lambda user_id, username, amount, period, payment_id: (
        f"New payment 💰\nUser ID: {user_id}\nUsername: @{username}\n"
        f"Amount: {amount} RUB\nPeriod: {period}\nPayment ID: {payment_id}"
    ),
    "approve_button": lambda: "✅ Approve",
    "reject_button": lambda: "❌ Reject",
    "payment_approved_admin": lambda payment_id, user_id: f"Payment {payment_id} approved for user {user_id}.",
    "payment_rejected_admin": lambda payment_id: f"Payment {payment_id} rejected.",
    "give_premium_button": lambda: "🎁 Give premium",
    "block_user_button": lambda: "🚫 Block user",
    "unblock_user_button": lambda: "✅ Unblock user",
    "user_management_welcome": lambda: "User management: 👇",
    "give_premium_prompt": lambda: "Send the user ID to grant 30 days of premium:",
    "premium_given_admin": lambda user_id: f"Premium granted to user {user_id}. 🎉",
    "user_not_found": lambda: "User not found.",
    "invalid_user_id": lambda: "Invalid user ID.",
    "block_user_prompt": lambda: "Send the user ID to block:",
    "user_blocked_admin": lambda user_id: f"User {user_id} blocked.",
    "user_blocked_user": lambda: "Your account has been blocked by the administrator. 🚫",
    "unblock_user_prompt": lambda: "Send the user ID to unblock:",
    "user_unblocked_admin": lambda user_id: f"User {user_id} unblocked.",
    "user_unblocked_user": lambda: "Your account has been unblocked. ✅",
}

def get_message(lang_code, key, *args, **kwargs):
    lang_dict = MESSAGE_MAP.get(lang_code, EN_MESSAGES)
    value = lang_dict.get(key)
    if value is None:
        value = EN_MESSAGES.get(key)
    if value is None:
        value = ADMIN_MESSAGES.get(key)
    if value is None:
        return key
    if callable(value):
        return value(*args, **kwargs)
    return value

async def _user_lang(user_id: int) -> str:
    user = await db.get_user(user_id)
    if user and user.get("language_code") in MESSAGE_MAP:
        return user["language_code"]
    return "en"

async def _send_long(message: Message, text: str):
    html = markdown_to_html(text)
    for chunk in split_message(html):
        try:
            await message.answer(chunk)
        except Exception:
            await message.answer(chunk, parse_mode=None)

# ---------------- Commands ----------------
@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language_code = message.from_user.language_code if message.from_user.language_code in MESSAGE_MAP else "en"
    referred_by = None
    args = command.args
    if args:
        try:
            referred_by = int(args)
            if referred_by == user_id:
                referred_by = None
        except ValueError:
            pass
    await db.add_user(user_id, username, first_name, last_name, language_code, referred_by)
    user = await db.get_user(user_id)
    if referred_by and referred_by != user_id:
        await db.add_referral(referred_by, user_id)
        await db.increment_referrals_count(referred_by)
        referrer = await db.get_user(referred_by)
        if referrer and referrer["referrals_count"] >= 3 and not referrer["is_premium"]:
            premium_until = datetime.now() + timedelta(days=7)
            await db.update_user_premium(referred_by, True, premium_until)
            await message.bot.send_message(
                referred_by,
                get_message(referrer["language_code"], "referrer_premium_granted")
            )
    if user and user["is_premium"]:
        welcome_text = get_message(language_code, "welcome_premium", first_name)
    else:
        welcome_text = get_message(language_code, "welcome", first_name, user["daily_limit"] if user else 10)
    await message.answer(welcome_text, reply_markup=main_menu(language_code))
    await state.set_state(UserStates.chatting)

@user_router.message(Command("help"))
async def cmd_help(message: Message):
    lang = await _user_lang(message.from_user.id)
    await message.answer(get_message(lang, "help"), reply_markup=main_menu(lang))

@user_router.message(Command("clear"))
async def cmd_clear(message: Message):
    user_id = message.from_user.id
    lang = await _user_lang(user_id)
    await db.clear_conversation_history(user_id)
    await message.answer(get_message(lang, "cleared"))

@user_router.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = await _user_lang(message.from_user.id)
    await message.answer(get_message(lang, "choose_lang"), reply_markup=lang_keyboard())

@user_router.callback_query(F.data.startswith("setlang_"))
async def cb_set_lang(callback: CallbackQuery):
    new_lang = callback.data.split("_", 1)[1]
    if new_lang not in MESSAGE_MAP:
        new_lang = "en"
    await db.set_user_language(callback.from_user.id, new_lang)
    await callback.message.answer(
        get_message(new_lang, "lang_set"),
        reply_markup=main_menu(new_lang)
    )
    await callback.answer()

@user_router.message(Command("bonus"))
async def cmd_bonus(message: Message):
    user_id = message.from_user.id
    lang = await _user_lang(user_id)
    user = await db.get_user(user_id)
    if not user:
        await message.answer(get_message(lang, "not_registered"))
        return
    granted = await db.claim_daily_bonus(user_id, DAILY_BONUS)
    if granted:
        await message.answer(get_message(lang, "bonus_claimed", DAILY_BONUS))
    else:
        await message.answer(get_message(lang, "bonus_already"))

@user_router.message(Command("promo"))
async def cmd_promo(message: Message, command: CommandObject):
    user_id = message.from_user.id
    lang = await _user_lang(user_id)
    if not command.args:
        await message.answer(get_message(lang, "promo_usage"))
        return
    code = command.args.strip().split()[0]
    result = await db.redeem_promo(user_id, code)
    if result is None:
        await message.answer(get_message(lang, "promo_invalid"))
    elif result == "already":
        await message.answer(get_message(lang, "promo_already"))
    else:
        await message.answer(get_message(
            lang, "promo_success",
            result.get("premium_days", 0), result.get("extra_requests", 0)
        ))
    await state.clear()

@user_router.message(Command("premium"))
async def cmd_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"
    if user and user["is_premium"] and user["premium_until"]:
        try:
            until_dt = datetime.strptime(str(user["premium_until"]), "%Y-%m-%d %H:%M:%S.%f")
            if until_dt > datetime.now():
                await message.answer(
                    get_message(language_code, "premium_exists", until_dt.strftime("%Y-%m-%d %H:%M"))
                )
                return
        except ValueError:
            pass
    # Narx tugmalarini bosganda to'g'ridan-to'g'ri saytga (Sber link) o'tib ketadigan qilamiz
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message(language_code, "7_days"), url=SPB_PAYMENT_LINK)],
        [types.InlineKeyboardButton(text=get_message(language_code, "1_month"), url=SPB_PAYMENT_LINK)],
        [types.InlineKeyboardButton(text=get_message(language_code, "3_months"), url=SPB_PAYMENT_LINK)],
        [types.InlineKeyboardButton(text=get_message(language_code, "paid_button"), callback_data="manual_payment_confirm")]
    ])
    await message.answer(get_message(language_code, "choose_premium"), reply_markup=keyboard)

@user_router.callback_query(F.data == "manual_payment_confirm")
async def manual_payment_confirm(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"
    
    # Foydalanuvchidan qaysi paketni sotib olganini so'rash yoki standart 1 oylik deb hisoblash
    # Bu yerda biz shunchaki admin xabar yuboramiz
    payment_id = await db.add_payment(user_id, 0, "Manual Check")
    await db.update_payment_status(payment_id, "pending")
    
    await callback.message.answer(get_message(language_code, "payment_received"))
    
    admin_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Approve 1 Month", callback_data=f"admin_approve_manual_{user_id}_1_month")],
        [types.InlineKeyboardButton(text="Approve 7 Days", callback_data=f"admin_approve_manual_{user_id}_7_days")],
        [types.InlineKeyboardButton(text="Reject", callback_data=f"admin_reject_manual_{user_id}")]
    ])
    
    await callback.bot.send_message(
        ADMIN_ID,
        f"Manual Payment Confirmation Required 💰\nUser: @{user['username']}\nID: {user_id}",
        reply_markup=admin_kb
    )
    await callback.answer()

@user_router.callback_query(F.data.startswith("buy_premium_"))
async def process_premium_purchase(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"
    period_data = callback.data.split("_")
    period_value = period_data[2]
    amount = 50
    period_str = "7 days"
    if period_value == "1":
        amount = 150
        period_str = "1 month"
    elif period_value == "3":
        amount = 350
        period_str = "3 months"
    payment_id = await db.add_payment(user_id, amount, period_str)
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message(language_code, "paid_button"), callback_data=f"confirm_payment_{payment_id}")]
    ])
    await callback.message.answer(
        get_message(language_code, "payment_info", period_str, amount, SPB_PAYMENT_LINK),
        reply_markup=keyboard
    )
    await callback.answer()

@user_router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    language_code = user["language_code"] if user else "en"
    payment_id = int(callback.data.split("_")[2])
    await db.update_payment_status(payment_id, "pending")
    await callback.message.answer(get_message(language_code, "payment_received"))
    payment = await db.get_payment(payment_id)
    admin_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message("en", "approve_button"), callback_data=f"admin_approve_{payment_id}")],
        [types.InlineKeyboardButton(text=get_message("en", "reject_button"), callback_data=f"admin_reject_{payment_id}")]
    ])
    await callback.bot.send_message(
        ADMIN_ID,
        get_message("en", "new_payment_admin", user_id, user["username"], payment["amount"], payment["period"], payment_id),
        reply_markup=admin_kb
    )
    await callback.answer()

@user_router.message(Command("balance"))
@user_router.message(F.text.in_(BTN_BALANCE))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await message.answer("Not registered. /start")
        return
    language_code = user["language_code"]
    status = "Premium 🚀" if user["is_premium"] else "Free 🆓"
    daily_limit = get_message(language_code, "unlimited") if user["is_premium"] else user["daily_limit"]
    premium_until = user["premium_until"] if user["is_premium"] else "N/A"
    await message.answer(get_message(language_code, "balance_info", status, daily_limit, premium_until))

@user_router.message(Command("referral"))
@user_router.message(F.text.in_(BTN_REF))
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user: return
    bot_info = await message.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user_id}"
    await message.answer(get_message(user["language_code"], "referral_info", referral_link, user["referrals_count"]))

@user_router.message(Command("image"))
@user_router.message(F.text.in_(BTN_IMAGE))
async def cmd_image(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user: return
    if not user["is_premium"]:
        await message.answer(get_message(user["language_code"], "premium_only_feature"))
        return
    await message.answer(get_message(user["language_code"], "image_prompt_request"))
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(UserStates.waiting_for_image_prompt)
async def process_image_prompt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    prompt = message.text
    await message.answer(get_message(user["language_code"], "image_generating"))
    image_url = await generate_image(prompt)
    if image_url.startswith("http"):
        await message.answer_photo(image_url, caption=get_message(user["language_code"], "image_ready"))
    else:
        await message.answer(get_message(user["language_code"], "image_error", image_url))
    await state.set_state(UserStates.chatting)

@user_router.message(F.text.in_(BTN_HELP))
async def menu_help(message: Message):
    await cmd_help(message)

@user_router.message(F.text.in_(BTN_CLEAR))
async def menu_clear(message: Message):
    await cmd_clear(message)

@user_router.message(F.text.in_(BTN_LANG))
async def menu_lang(message: Message):
    await cmd_lang(message)

@user_router.message(F.text.in_(BTN_BONUS))
async def menu_bonus(message: Message):
    await cmd_bonus(message)

@user_router.message(F.text.in_(BTN_PREMIUM))
async def menu_premium(message: Message, state: FSMContext):
    await cmd_premium(message, state)

@user_router.message(F.text)
async def handle_chat(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await message.answer("Please /start first.")
        return
    if user["is_blocked"]:
        await message.answer(get_message(user["language_code"], "user_blocked_user"))
        return
    if not user["is_premium"] and user["daily_limit"] <= 0:
        await message.answer(get_message(user["language_code"], "daily_limit_exceeded"))
        return
    history = await db.get_chat_history(user_id)
    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message.text})
    await message.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    response = await get_chat_response(messages)
    await _send_long(message, response)
    await db.add_chat_history(user_id, message.text, response)
    if not user["is_premium"]:
        await db.decrement_daily_limit(user_id)
