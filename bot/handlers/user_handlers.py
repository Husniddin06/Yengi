import os
import io
import fitz  # PyMuPDF
from aiogram import Router, F, types
from aiogram.types import (
    Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent, LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction
from datetime import datetime, timedelta

from config import ADMIN_ID, SPB_PAYMENT_LINK, DAILY_BONUS
from database import db
from utils.openai_utils import (
    get_chat_response, generate_image, analyze_image_and_chat, 
    transcribe_audio, analyze_document, edit_image
)
from utils.text_utils import split_message, markdown_to_html
from utils.keyboards import (
    main_menu, lang_keyboard,
    BTN_BALANCE, BTN_PREMIUM, BTN_REF, BTN_HELP, BTN_CLEAR,
    BTN_IMAGE, BTN_LANG, BTN_BONUS,
)

user_router = Router()

class UserStates(StatesGroup):
    chatting = State()
    waiting_for_image_prompt = State()

# ---------------- Localization ----------------
UZ_MESSAGES = {
    "welcome": lambda name, daily_limit: f"Assalomu alaykum, {name}! 👋 SmartAI botga xush kelibsiz.\n\nMen sizning shaxsiy AI yordamchingizman. Savol bering, rasm yuboring yoki internetdan qidiruvni ishlating.\n\nKunlik {daily_limit} ta bepul so'rov bor. Cheksiz uchun /premium ✨",
    "welcome_premium": lambda name: f"Assalomu alaykum, {name}! 👋 Siz premium foydalanuvchisiz — cheksiz imkoniyatlar! 🚀",
    "help": (
        "<b>SmartAI — yordam</b>\n\n"
        "💬 Matn yozing — AI javob beradi\n"
        "🌐 /search matn — Internetdan qidirish\n"
        "🎙 Ovozli xabar — AI javob beradi\n"
        "🖼️ Rasm yuboring — AI tahlil qiladi\n"
        "📄 PDF/Text — AI hujjatni o'qiydi\n"
        "🎨 /image — rasm yaratish\n"
        "💎 /premium — Stars orqali sotib olish"
    ),
    "premium_only_feature": "Bu funksiya faqat premium uchun. /premium 🚫",
    "daily_limit_exceeded": "Kunlik limit tugadi. /premium yoki /bonus 😔",
    "image_generating": "Rasm yaratilmoqda... 🎨",
    "image_ready": "Rasm tayyor! ✨",
    "image_prompt_request": "Rasm uchun tavsif bering: 🖼️",
    "cleared": "Suhbat tarixi tozalandi. ✅",
}

RU_MESSAGES = UZ_MESSAGES 
EN_MESSAGES = UZ_MESSAGES 

MESSAGE_MAP = {"uz": UZ_MESSAGES, "ru": RU_MESSAGES, "en": EN_MESSAGES}

def get_message(lang_code, key, *args, **kwargs):
    lang_dict = MESSAGE_MAP.get(lang_code, UZ_MESSAGES)
    value = lang_dict.get(key, UZ_MESSAGES.get(key, key))
    if callable(value):
        # Argumentlar sonini tekshirish
        import inspect
        sig = inspect.signature(value)
        if len(sig.parameters) == len(args):
            return value(*args)
        elif len(sig.parameters) == 0:
            return value()
        return value(args[0]) # Faqat birinchi argumentni yuborish
    return value

async def _user_lang(user_id: int) -> str:
    user = await db.get_user(user_id)
    return user["language_code"] if user else "uz"

async def _send_long(message: Message, text: str):
    html = markdown_to_html(text)
    for chunk in split_message(html):
        try: await message.answer(chunk)
        except: await message.answer(chunk, parse_mode=None)

# ---------------- Handlers ----------------
@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    lang = message.from_user.language_code if message.from_user.language_code in MESSAGE_MAP else "uz"
    await db.add_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name, lang)
    user = await db.get_user(user_id)
    if user["is_premium"]:
        welcome = get_message(lang, "welcome_premium", message.from_user.first_name)
    else:
        welcome = get_message(lang, "welcome", message.from_user.first_name, user["daily_limit"])
    await message.answer(welcome, reply_markup=main_menu(lang))
    await state.set_state(UserStates.chatting)

@user_router.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Foydalanish: /search qidiriladigan matn")
        return
    await message.bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    response = await get_chat_response([{"role": "user", "content": command.args}], use_web=True)
    await _send_long(message, response)

@user_router.message(Command("premium"))
async def cmd_premium(message: Message):
    prices = [LabeledPrice(label="Premium 1 oy", amount=50)] 
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="SmartAI Premium",
        description="1 oylik cheksiz imkoniyatlar va yangi funksiyalar!",
        payload="premium_1_month",
        provider_token="", 
        currency="XTR", 
        prices=prices
    )

@user_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@user_router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    premium_until = datetime.now() + timedelta(days=30)
    await db.update_user_premium(user_id, True, premium_until)
    await message.answer("🎉 To'lov muvaffaqiyatli! Premium faollashtirildi.")

@user_router.message(Command("image"))
@user_router.message(F.text.in_(BTN_IMAGE))
async def cmd_image(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user["is_premium"]:
        await message.answer("Bu funksiya faqat premium uchun. /premium")
        return
    await message.answer("Rasm uchun tavsif bering: 🖼️")
    await state.set_state(UserStates.waiting_for_image_prompt)

@user_router.message(UserStates.waiting_for_image_prompt)
async def process_image_prompt(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await _user_lang(user_id)
    await message.answer(get_message(lang, "image_generating"))
    image_url = await generate_image(message.text)
    if image_url.startswith("http"):
        await message.answer_photo(image_url, caption=get_message(lang, "image_ready"))
    else:
        await message.answer(f"Xato: {image_url}")
    await state.set_state(UserStates.chatting)

@user_router.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user["is_premium"]:
        await message.answer("Bu funksiya faqat premium uchun. /premium")
        return
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_bytes = await message.bot.download_file(file.file_path)
    await message.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    response = await analyze_image_and_chat(message.caption, photo_bytes.read())
    await _send_long(message, response)

@user_router.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    file = await message.bot.get_file(message.voice.file_id)
    file_path = f"voice_{user_id}.ogg"
    await message.bot.download_file(file.file_path, file_path)
    text = await transcribe_audio(file_path)
    if os.path.exists(file_path): os.remove(file_path)
    if text:
        await message.answer(f"🎤 <i>{text}</i>")
        await handle_chat(message, text_override=text)
    else:
        await message.answer("⚠️ Ovozni tushunib bo'lmadi.")

@user_router.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user["is_premium"]:
        await message.answer("Bu funksiya faqat premium uchun. /premium")
        return
    doc = message.document
    if not doc.file_name.lower().endswith(('.pdf', '.txt')):
        await message.answer("⚠️ Faqat .pdf va .txt fayllarni tahlil qila olaman.")
        return
    file = await message.bot.get_file(doc.file_id)
    file_path = f"doc_{user_id}_{doc.file_name}"
    await message.bot.download_file(file.file_path, file_path)
    content = ""
    try:
        if doc.file_name.lower().endswith('.pdf'):
            with fitz.open(file_path) as pdf:
                for page in pdf: content += page.get_text()
        else:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
    except Exception as e:
        await message.answer(f"Faylni o'qishda xato: {e}")
    if os.path.exists(file_path): os.remove(file_path)
    if content:
        await message.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        response = await analyze_document(content[:10000], message.caption if message.caption else "Ushbu hujjatni tahlil qil.")
        await _send_long(message, response)

@user_router.message(F.text)
async def handle_chat(message: Message, text_override=None):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user: return
    text = text_override or message.text
    if text in BTN_BALANCE:
        status = "Premium 🚀" if user["is_premium"] else "Free 🆓"
        await message.answer(f"📊 Balans:\nStatus: {status}\nLimit: {user['daily_limit']}")
        return
    elif text in BTN_CLEAR:
        await db.clear_conversation_history(user_id)
        await message.answer("Suhbat tozalandi. ✅")
        return
    if not user["is_premium"] and user["daily_limit"] <= 0:
        await message.answer("Limit tugadi. /premium")
        return
    history = await db.get_chat_history(user_id)
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": text})
    await message.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
    response = await get_chat_response(messages)
    await _send_long(message, response)
    await db.add_chat_history(user_id, text, response)
    if not user["is_premium"]: await db.decrement_daily_limit(user_id)

@user_router.inline_query()
async def inline_handler(query: InlineQuery):
    if not query.query: return
    response = await get_chat_response([{"role": "user", "content": query.query}])
    results = [InlineQueryResultArticle(id="1", title="SmartAI", input_message_content=InputTextMessageContent(message_text=response))]
    await query.answer(results, cache_time=5)
