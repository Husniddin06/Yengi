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
    waiting_for_promo_code = State()

def is_admin(user_id: int):
    return user_id == ADMIN_ID

def admin_menu():
    keyboard = [
        [InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎟 Create Promo", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="🔄 Reset Limits", callback_data="admin_reset_limits")],
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

@admin_router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): return
    await cb.message.answer("Send promo-code format:\n<code>CODE DAYS REQUESTS COUNT</code>\n\nExample: <code>NEW2024 30 100 50</code>")
    await state.set_state(AdminStates.waiting_for_promo_code)
    await cb.answer()

@admin_router.message(AdminStates.waiting_for_promo_code)
async def process_create_promo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        code = parts[0].upper()
        days = int(parts[1])
        reqs = int(parts[2])
        uses = int(parts[3])
        await db.create_promo(code, days, reqs, uses)
        await message.answer(f"✅ Promo created: {code}\n💎 Days: {days}\n➕ Requests: {reqs}\n🔢 Count: {uses}")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
    await state.clear()

@admin_router.callback_query(F.data == "admin_reset_limits")
async def admin_reset_limits(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await db.reset_all_daily_limits(10)
    await cb.message.answer("✅ Daily limits reset to 10 for all free users.")
    await cb.answer()
