from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_ID
from database import db
from handlers.user_handlers import get_message

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_user_id_to_set_premium = State()

@admin_router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="admin_broadcast")],
        [types.InlineKeyboardButton(text="💎 Premium berish", callback_data="admin_give_premium")],
        [types.InlineKeyboardButton(text="🌐 Web Dashboard", url="https://yengi-admin.vercel.app")]
    ])
    await message.answer("Admin paneliga xush kelibsiz:", reply_markup=keyboard)

@admin_router.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats(callback: CallbackQuery):
    total_users = await db.get_total_users()
    premium_users = await db.get_premium_users_count()
    await callback.message.answer(f"📊 Statistika:\nJami foydalanuvchilar: {total_users}\nPremium foydalanuvchilar: {premium_users}")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Barcha foydalanuvchilarga yuboriladigan xabarni yozing:")
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_broadcast_message, F.from_user.id == ADMIN_ID)
async def admin_broadcast_message(message: Message, state: FSMContext):
    all_users = await db.get_all_users()
    count = 0
    for user in all_users:
        try:
            await message.bot.send_message(user["id"], message.text)
            count += 1
        except: pass
    await message.answer(f"Xabar {count} ta foydalanuvchiga yuborildi. ✅")
    await state.clear()

@admin_router.callback_query(F.data == "admin_give_premium", F.from_user.id == ADMIN_ID)
async def admin_give_premium_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Premium beriladigan foydalanuvchi ID sini yozing:")
    await state.set_state(AdminStates.waiting_for_user_id_to_set_premium)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_to_set_premium, F.from_user.id == ADMIN_ID)
async def admin_give_premium_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        premium_until = datetime.now() + timedelta(days=30)
        await db.update_user_premium(user_id, True, premium_until)
        await message.answer(f"Foydalanuvchi {user_id} ga 30 kunlik premium berildi. 🎉")
    except ValueError:
        await message.answer("ID raqam bo'lishi kerak.")
    await state.clear()
