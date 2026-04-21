
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

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    referred_by = None
    if message.get_args():
        try:
            referred_by = int(message.get_args())
            if referred_by == user_id:
                referred_by = None # User cannot refer themselves
        except ValueError:
            pass

    await db.add_user(user_id, username, first_name, last_name, referred_by)
    user = await db.get_user(user_id)

    if referred_by and referred_by != user_id:
        await db.add_referral(referred_by, user_id)
        await db.increment_referrals_count(referred_by)
        # Check if referrer gets premium
        referrer = await db.get_user(referred_by)
        if referrer and referrer["referrals_count"] >= 3 and not referrer["is_premium"]:
            premium_until = datetime.now() + timedelta(days=7)
            await db.update_user_premium(referred_by, True, premium_until)
            await message.bot.send_message(referred_by, "🎉 Siz 3 ta do'stingizni taklif qildingiz va 7 kunlik premium obunaga ega bo'ldingiz!")

    welcome_text = (
        f"Assalomu alaykum, {first_name}! SmartAI botga xush kelibsiz.\n\n"
        "Men sizning shaxsiy AI yordamchingizman. Men bilan suhbatlashishingiz, savollar berishingiz va hatto rasmlar yaratishingiz mumkin.\n\n"
    )
    if user and user["is_premium"]:
        welcome_text += "Siz premium foydalanuvchisiz va cheksiz imkoniyatlarga egasiz!"
    else:
        welcome_text += f"Sizda kunlik {user["daily_limit"]} ta bepul so'rov mavjud. Premium obuna orqali cheksiz imkoniyatlarga ega bo'ling! /premium"

    await message.answer(welcome_text)
    await state.set_state(UserStates.chatting)

@user_router.message(Command("premium"))
async def cmd_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if user and user["is_premium"] and user["premium_until"] and datetime.strptime(user["premium_until"], "%Y-%m-%d %H:%M:%S.%f") > datetime.now():
        await message.answer(f"Sizda allaqachon premium obuna mavjud. Obunangiz {datetime.strptime(user["premium_until"], "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M")} gacha amal qiladi.")
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="7 kun (50 RUB)", callback_data="buy_premium_7_days")],
        [types.InlineKeyboardButton(text="1 oy (150 RUB)", callback_data="buy_premium_1_month")],
        [types.InlineKeyboardButton(text="3 oy (350 RUB)", callback_data="buy_premium_3_months")]
    ])
    await message.answer("Premium obunani tanlang:", reply_markup=keyboard)

@user_router.callback_query(F.data.startswith("buy_premium_"))
async def process_premium_purchase(callback: CallbackQuery, state: FSMContext):
    period_data = callback.data.split("_")
    period_value = period_data[2]
    period_unit = period_data[3] if len(period_data) > 3 else "days"

    amount = 0
    if period_value == "7" and period_unit == "days":
        amount = 50
        period_str = "7 kun"
    elif period_value == "1" and period_unit == "month":
        amount = 150
        period_str = "1 oy"
    elif period_value == "3" and period_unit == "months":
        amount = 350
        period_str = "3 oy"
    else:
        await callback.message.answer("Noto'g'ri obuna tanlandi.")
        await callback.answer()
        return

    payment_text = (
        f"Siz {period_str} uchun {amount} RUB miqdorida premium obuna sotib olmoqchisiz.\n\n"
        f"To'lovni amalga oshirish uchun quyidagi SPB havolasidan foydalaning:\n{SPB_PAYMENT_LINK}\n\n"
        "To'lovni amalga oshirganingizdan so'ng, 'To'ladim' tugmasini bosing. Admin to'lovingizni tasdiqlagandan so'ng, premium obunangiz faollashadi."
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="To'ladim", callback_data=f"payment_done_{amount}_{period_value}_{period_unit}")]
    ])

    await callback.message.answer(payment_text, reply_markup=keyboard)
    await state.set_state(UserStates.waiting_for_payment_confirmation)
    await callback.answer()

@user_router.callback_query(F.data.startswith("payment_done_"), UserStates.waiting_for_payment_confirmation)
async def payment_done(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data.split("_")
    amount = float(data[2])
    period_value = data[3]
    period_unit = data[4]
    period = f"{period_value} {period_unit}"

    payment_id = await db.add_payment(user_id, amount, "RUB", "pending", period)

    await callback.message.answer("To'lovingiz qabul qilindi va admin tasdiqlashini kutmoqda. Rahmat!")
    await callback.answer()
    await state.set_state(UserStates.chatting)

    # Notify admin
    admin_message = (
        f"Yangi to'lov!\n"
        f"User ID: {user_id}\n"
        f"Username: @{callback.from_user.username if callback.from_user.username else 'N/A'}\n"
        f"Miqdor: {amount} RUB\n"
        f"Davr: {period}\n"
        f"To'lov ID: {payment_id}"
    )
    approve_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Tasdiqlash", callback_data=f"approve_payment_{payment_id}_{user_id}_{period_value}_{period_unit}")],
        [types.InlineKeyboardButton(text="Rad etish", callback_data=f"reject_payment_{payment_id}")]
    ])
    await callback.bot.send_message(ADMIN_ID, admin_message, reply_markup=approve_keyboard)

@user_router.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if user:
        status = "Premium" if user["is_premium"] else "Free"
        premium_until_str = "Yo'q"
        if user["premium_until"]:
            premium_until = datetime.strptime(user["premium_until"], "%Y-%m-%d %H:%M:%S.%f")
            premium_until_str = premium_until.strftime("%Y-%m-%d %H:%M")

        await message.answer(
            f"Sizning balansingiz:\n"
            f"Status: {status}\n"
            f"Kunlik limit: {user["daily_limit"] if not user["is_premium"] else 'Cheksiz'}\n"
            f"Premium gacha: {premium_until_str}"
        )
    else:
        await message.answer("Siz ro'yxatdan o'tmagansiz. /start buyrug'ini bosing.")

@user_router.message(Command("referral"))
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    referral_link = f"https://t.me/SmartAiibot?start={user_id}"
    user = await db.get_user(user_id)
    referrals_count = user["referrals_count"] if user else 0

    await message.answer(
        f"Sizning referral havolangiz:\n{referral_link}\n\n"
        f"Siz {referrals_count} ta do'stingizni taklif qildingiz. 3 ta do'st taklif qilsangiz, 7 kunlik premium olasiz!"
    )

@user_router.message(F.text, UserStates.chatting)
async def handle_text_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user:
        await message.answer("Iltimos, /start buyrug'ini bosing.")
        return

    if user["is_premium"] or user["daily_limit"] > 0:
        await message.answer("Javob kutilmoqda...")
        response = await get_chat_response(message.text)
        await message.answer(response)

        if not user["is_premium"]:
            await db.update_user_daily_limit(user_id, user["daily_limit"] - 1)
    else:
        await message.answer("Sizning kunlik limitingiz tugadi. Premium obuna sotib oling yoki ertaga qayta urinib ko'ring. /premium")

@user_router.message(F.photo, UserStates.chatting)
async def handle_photo_message(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user or not user["is_premium"]:
        await message.answer("Faqat premium foydalanuvchilar rasmlarni tahlil qila oladi. /premium")
        return

    await message.answer("Rasm tahlili funksiyasi hozircha mavjud emas.")

@user_router.message(F.document, UserStates.chatting)
async def handle_document_message(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user or not user["is_premium"]:
        await message.answer("Faqat premium foydalanuvchilar fayllarni tahlil qila oladi. /premium")
        return

    await message.answer("Fayl tahlili funksiyasi hozircha mavjud emas.")

@user_router.message(Command("image"))
async def cmd_image(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if not user or not user["is_premium"]:
        await message.answer("Faqat premium foydalanuvchilar rasm yaratishi mumkin. /premium")
        return

    await message.answer("Iltimos, rasm yaratish uchun tavsif bering:")
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(UserStates.waiting_for_image_prompt, F.text)
async def generate_image_prompt(message: Message, state: FSMContext):
    await message.answer("Rasm yaratilmoqda...")
    image_url = await generate_image(message.text)
    if image_url.startswith("Error"):
        await message.answer(f"Rasm yaratishda xatolik yuz berdi: {image_url}")
    else:
        await message.answer_photo(photo=image_url, caption="Sizning rasmingiz tayyor!")
    await state.set_state(UserStates.chatting)
