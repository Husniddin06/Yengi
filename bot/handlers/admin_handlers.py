from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_ID
from database import db
from handlers.user_handlers import get_message # Import get_message from user_handlers

admin_router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_user_id_to_manage = State()
    waiting_for_user_id_to_set_premium = State()
    waiting_for_user_id_to_block = State()
    waiting_for_user_id_to_unblock = State()

@admin_router.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: Message):
    # Admin panel messages will be in English for consistency, as per previous implementation
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message("en", "stats_button"), callback_data="admin_stats")],
        [types.InlineKeyboardButton(text=get_message("en", "broadcast_button"), callback_data="admin_broadcast")],
        [types.InlineKeyboardButton(text=get_message("en", "payments_button"), callback_data="admin_payments")],
        [types.InlineKeyboardButton(text=get_message("en", "user_management_button"), callback_data="admin_user_management")]
    ])
    await message.answer(get_message("en", "admin_welcome"), reply_markup=keyboard)

@admin_router.callback_query(F.data == "admin_stats", F.from_user.id == ADMIN_ID)
async def admin_stats(callback: CallbackQuery):
    total_users = await db.get_total_users()
    premium_users = await db.get_premium_users_count()

    stats_text = get_message("en", "admin_stats", total_users, premium_users)
    await callback.message.answer(stats_text)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_broadcast", F.from_user.id == ADMIN_ID)
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(get_message("en", "broadcast_prompt"))
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_broadcast_message, F.from_user.id == ADMIN_ID)
async def admin_broadcast_message(message: Message, state: FSMContext):
    all_users = await db.get_all_users()
    for user in all_users:
        try:
            await message.bot.send_message(user["id"], message.text)
        except Exception as e:
            print(f"Could not send message to user {user['id']}: {e}")
    await message.answer(get_message("en", "broadcast_sent"))
    await state.clear()

@admin_router.callback_query(F.data == "admin_payments", F.from_user.id == ADMIN_ID)
async def admin_payments(callback: CallbackQuery):
    pending_payments = await db.get_pending_payments()
    if not pending_payments:
        await callback.message.answer(get_message("en", "no_pending_payments"))
        await callback.answer()
        return

    for payment in pending_payments:
        user = await db.get_user(payment["user_id"])
        admin_message = get_message("en", "new_payment_admin",
            payment["user_id"],
            user["username"] if user and user["username"] else "N/A",
            payment["amount"],
            payment["period"],
            payment["id"]
        )
        approve_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=get_message("en", "approve_button"), callback_data=f"approve_payment_{payment['id']}_{payment['user_id']}_{payment['period'].split()[0]}_{payment['period'].split()[1]}")],
            [types.InlineKeyboardButton(text=get_message("en", "reject_button"), callback_data=f"reject_payment_{payment['id']}")]
        ])
        await callback.message.answer(admin_message, reply_markup=approve_keyboard)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("approve_payment_"), F.from_user.id == ADMIN_ID)
async def approve_payment(callback: CallbackQuery):
    data = callback.data.split("_")
    payment_id = int(data[2])
    user_id = int(data[3])
    period_value = data[4]
    period_unit = data[5]

    premium_until = datetime.now()
    if period_unit == "days":
        premium_until += timedelta(days=int(period_value))
    elif period_unit == "month":
        premium_until += timedelta(days=30 * int(period_value)) # Approximation
    elif period_unit == "months":
        premium_until += timedelta(days=30 * int(period_value)) # Approximation

    await db.update_payment_status(payment_id, "approved", callback.from_user.id)
    await db.update_user_premium(user_id, True, premium_until)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(get_message("en", "payment_approved_admin", payment_id, user_id))
    
    user_lang = (await db.get_user(user_id))["language_code"]
    await callback.bot.send_message(user_id, get_message(user_lang, "payment_approved_user", premium_until.strftime("%Y-%m-%d %H:%M")))
    await callback.answer()

@admin_router.callback_query(F.data.startswith("reject_payment_"), F.from_user.id == ADMIN_ID)
async def reject_payment(callback: CallbackQuery):
    payment_id = int(callback.data.split("_")[2])
    await db.update_payment_status(payment_id, "rejected", callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(get_message("en", "payment_rejected_admin", payment_id))
    await callback.answer()

@admin_router.callback_query(F.data == "admin_user_management", F.from_user.id == ADMIN_ID)
async def admin_user_management(callback: CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=get_message("en", "give_premium_button"), callback_data="admin_give_premium")],
        [types.InlineKeyboardButton(text=get_message("en", "block_user_button"), callback_data="admin_block_user")],
        [types.InlineKeyboardButton(text=get_message("en", "unblock_user_button"), callback_data="admin_unblock_user")]
    ])
    await callback.message.answer(get_message("en", "user_management_welcome"), reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_give_premium", F.from_user.id == ADMIN_ID)
async def admin_give_premium_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(get_message("en", "give_premium_prompt"))
    await state.set_state(AdminStates.waiting_for_user_id_to_set_premium)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_to_set_premium, F.from_user.id == ADMIN_ID)
async def admin_give_premium_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await db.get_user(user_id)
        if user:
            premium_until = datetime.now() + timedelta(days=30) # Default 30 days premium
            await db.update_user_premium(user_id, True, premium_until)
            await message.answer(get_message("en", "premium_given_admin", user_id))
            user_lang = (await db.get_user(user_id))["language_code"]
            await message.bot.send_message(user_id, get_message(user_lang, "payment_approved_user", premium_until.strftime("%Y-%m-%d %H:%M")))
        else:
            await message.answer(get_message("en", "user_not_found"))
    except ValueError:
        await message.answer(get_message("en", "invalid_user_id"))
    await state.clear()

@admin_router.callback_query(F.data == "admin_block_user", F.from_user.id == ADMIN_ID)
async def admin_block_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(get_message("en", "block_user_prompt"))
    await state.set_state(AdminStates.waiting_for_user_id_to_block)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_to_block, F.from_user.id == ADMIN_ID)
async def admin_block_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await db.get_user(user_id)
        if user:
            await db.block_user(user_id)
            await message.answer(get_message("en", "user_blocked_admin", user_id))
            user_lang = (await db.get_user(user_id))["language_code"]
            await message.bot.send_message(user_id, get_message(user_lang, "user_blocked_user"))
        else:
            await message.answer(get_message("en", "user_not_found"))
    except ValueError:
        await message.answer(get_message("en", "invalid_user_id"))
    await state.clear()

@admin_router.callback_query(F.data == "admin_unblock_user", F.from_user.id == ADMIN_ID)
async def admin_unblock_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(get_message("en", "unblock_user_prompt"))
    await state.set_state(AdminStates.waiting_for_user_id_to_unblock)
    await callback.answer()

@admin_router.message(AdminStates.waiting_for_user_id_to_unblock, F.from_user.id == ADMIN_ID)
async def admin_unblock_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await db.get_user(user_id)
        if user:
            await db.unblock_user(user_id)
            await message.answer(get_message("en", "user_unblocked_admin", user_id))
            user_lang = (await db.get_user(user_id))["language_code"]
            await message.bot.send_message(user_id, get_message(user_lang, "user_unblocked_user"))
        else:
            await message.answer(get_message("en", "user_not_found"))
    except ValueError:
        await message.answer(get_message("en", "invalid_user_id"))
    await state.clear()
