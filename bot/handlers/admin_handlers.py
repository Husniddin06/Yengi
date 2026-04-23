import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database import db
from bot.config import ADMIN_ID

logger = logging.getLogger(__name__)
admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

def is_admin(user_id: int):
    return user_id == ADMIN_ID

def admin_menu():
    keyboard = [
        [InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💳 Pending Payments", callback_data="admin_pending_payments")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Welcome to Admin Panel:", reply_markup=admin_menu())

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    total = await db.get_total_users()
    premium = await db.get_premium_users_count()
    blocked = await db.get_blocked_users_count()
    text = (
        f"📊 <b>Bot Statistics:</b>\n\n"
        f"👥 Total Users: {total}\n"
        f"💎 Premium Users: {premium}\n"
        f"🚫 Blocked: {blocked}"
    )
    await cb.message.edit_text(text, reply_markup=admin_menu())

@admin_router.callback_query(F.data == "admin_pending_payments")
async def admin_pending_payments(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    payments = await db.get_pending_payments()
    if not payments:
        await cb.message.answer("No pending payments.")
        await cb.answer()
        return
    
    from bot.utils.keyboards import admin_payment_confirm_keyboard
    for p in payments:
        text = f"💳 <b>Payment Request</b>\nUser: {p['username']} (ID: {p['user_id']})\nAmount: {p['amount']}₽\nMethod: {p['method']}\nDate: {p['created_at']}"
        await cb.message.answer(text, reply_markup=admin_payment_confirm_keyboard(p['id']))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("admin_confirm_pay_"))
async def admin_confirm_payment(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    payment_id = int(cb.data.split("_")[3])
    user_id = await db.approve_payment(payment_id, cb.from_user.id)
    if user_id:
        await cb.message.edit_text(f"✅ Payment {payment_id} confirmed. 150 coins added to user {user_id}.")
        try:
            await cb.bot.send_message(user_id, "✅ Your SBP payment has been confirmed! 150 coins added and Premium activated.")
        except: pass
    else:
        await cb.message.edit_text("❌ Error confirming payment.")
    await cb.answer()

@admin_router.callback_query(F.data.startswith("admin_reject_pay_"))
async def admin_reject_payment(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    payment_id = int(cb.data.split("_")[3])
    # Shunchaki o'chirish yoki statusni o'zgartirish mumkin
    await cb.message.edit_text(f"❌ Payment {payment_id} rejected.")
    await cb.answer()

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await cb.message.answer("Send the message (text, photo, or video):")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await cb.answer()

@admin_router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    users = await db.get_all_users()
    count = 0
    await message.answer(f"Broadcast started... (Total: {len(users)})")
    for user in users:
        try:
            await message.copy_to(user["id"])
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"Message sent to {count} users.")
    await state.clear()
