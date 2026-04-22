import logging
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from openai import AsyncOpenAI, OpenAIError
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Bepul modellar orasida eng barqarorini tanlaymiz
CHAT_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

SYSTEM_PROMPT = (
    "Sen SmartAI — kuchli va aqlli AI assistantsan. "
    "Foydalanuvchiga har qanday savol bo'yicha batafsil, aniq va foydali javob ber. "
    "Har doim foydalanuvchi tilida javob ber. "
    "Javoblar professional, tushunarli va to'liq bo'lsin."
)

async def get_chat_response(messages: list) -> str:
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=full_messages,
            max_tokens=2048,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenRouter API error: {e}")
        if "429" in str(e):
            return "⚠️ Bepul so'rovlar limiti tugadi. Iltimos, birozdan keyin urinib ko'ring yoki Premium sotib oling. ✨"
        return f"⚠️ AI xatosi: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"⚠️ Kutilmagan xato yuz berdi."

async def generate_image(prompt: str) -> str:
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
