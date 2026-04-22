import logging
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from openai import AsyncOpenAI, OpenAIError
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Mistral 7B odatda bepul modellar orasida eng barqarori hisoblanadi
CHAT_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

# API kalitni tekshirish
if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENROUTER_API_KEY":
    logger.error("CRITICAL: OPENAI_API_KEY is missing or not set correctly!")

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    default_headers={
        "HTTP-Referer": "https://github.com/Husniddin06/Yengi",
        "X-Title": "SmartAI Bot",
    }
)

SYSTEM_PROMPT = (
    "Sen SmartAI — kuchli va aqlli AI assistantsan. "
    "Foydalanuvchiga har qanday savol bo'yicha batafsil, aniq va foydali javob ber. "
    "Har doim foydalanuvchi tilida javob ber. "
    "Javoblar professional, tushunarli va to'liq bo'lsin."
)

async def get_chat_response(messages: list) -> str:
    # API kalit tekshiruvi
    if not OPENAI_API_KEY or len(OPENAI_API_KEY) < 10:
        return "⚠️ Xatolik: API kalit o'rnatilmagan. Iltimos, Replit Secrets bo'limida OPENAI_API_KEY ni sozlang."

    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=full_messages,
            max_tokens=1500,
            temperature=0.7,
        )
        
        if not response.choices or not response.choices[0].message.content:
            return "⚠️ AI javob qaytarmadi. Iltimos, birozdan keyin qayta urinib ko'ring."
            
        return response.choices[0].message.content
        
    except OpenAIError as e:
        error_str = str(e)
        logger.error(f"OpenRouter API error: {error_str}")
        
        if "401" in error_str or "User not found" in error_str:
            return "⚠️ API kalit xatosi (401). Sizning API kalitingiz noto'g'ri yoki muddati tugagan. Yangi kalit olib Replit Secrets'ga qo'shing."
        elif "429" in error_str:
            return "⚠️ Limit tugadi. Bepul modellar uchun kunlik limitga yetdingiz. Premium sotib oling yoki ertaga urinib ko'ring."
        elif "403" in error_str:
            return "⚠️ Kirish taqiqlangan (403). OpenRouter hisobingizni tekshiring."
            
        return f"⚠️ AI xizmatida muammo yuz berdi. Keyinroq urinib ko'ring."
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"⚠️ Kutilmagan xato yuz berdi."

async def generate_image(prompt: str) -> str:
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
