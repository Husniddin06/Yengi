import os
import logging
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
from datetime import datetime, timedelta

from bot.database import db
from bot.utils.openai_utils import get_chat_response, generate_image, analyze_image_and_chat, transcribe_audio
from bot.utils.keyboards import main_menu, BTN_BALANCE, BTN_CLEAR, BTN_IMAGE

logger = logging.getLogger(__name__)
user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name, "uz")
    await message.answer(f"Assalomu alaykum, {message.from_user.first_name}! 👋 SmartAI botga xush kelibsiz.\nSavol bering yoki rasm yuboring.", reply_markup=main_menu("uz"))

@user_router.message(Command("premium"))
async def cmd_premium(message: Message):
    prices = [LabeledPrice(label="Premium 1 oy", amount=50)] 
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="SmartAI Premium",
        description="1 oylik cheksiz imkoniyatlar!",
        payload="premium_1_month",
        provider_token="", 
        currency="XTR", 
        prices=prices
    )

@user_router.pre_checkout_query()
async def process_pre_checkout(pq: PreCheckoutQuery):
    await pq.answer(ok=True)

@user_router.message(F.successful_payment)
async def process_pay(message: Message):
    await db.update_user_premium(message.from_user.id, True, datetime.now() + timedelta(days=30))
    await message.answer("🎉 Premium faollashtirildi!")

@user_router.message(F.text.in_(BTN_IMAGE))
@user_router.message(Command("image"))
async def ask_image(message: Message):
    await message.answer("Rasm uchun tavsif yozing (masalan: 'Astro-mushuk'):")

@user_router.message(F.photo)
async def handle_photo(message: Message):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_bytes = await message.bot.download_file(file.file_path)
    await message.bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    resp = await analyze_image_and_chat(message.caption, photo_bytes.read())
    await message.answer(resp)

@user_router.message(F.text)
async def handle_msg(message: Message):
    user_id = message.from_user.id
    text = message.text
    
    if text in BTN_BALANCE:
        user = await db.get_user(user_id)
        status = "Premium 🚀" if user and user["is_premium"] else "Free 🆓"
        await message.answer(f"📊 Balans:\nStatus: {status}")
        return
    elif text in BTN_CLEAR:
        await db.clear_conversation_history(user_id)
        await message.answer("Tarix tozalandi. ✅")
        return

    if text.lower().startswith(("rasm", "image", "yasa", "chiz")):
        await message.answer("Rasm tayyorlanmoqda... 🎨")
        url = await generate_image(text)
        await message.answer_photo(url)
        return

    await message.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    history = await db.get_chat_history(user_id)
    msgs = [{"role": h["role"], "content": h["content"]} for h in history]
    msgs.append({"role": "user", "content": text})
    
    resp = await get_chat_response(msgs)
    await message.answer(resp)
    await db.add_chat_history(user_id, text, resp)
