import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openai import AsyncOpenAI, OpenAIError
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# OpenRouter settings
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# OpenRouter client — OpenAI SDK bilan mos ishlaydi
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

SYSTEM_PROMPT = (
    "Sen SmartAI — kuchli va aqlli AI assistantsan. "
    "Foydalanuvchiga har qanday savol bo'yicha batafsil, aniq va foydali javob ber. "
    "Har doim foydalanuvchi tilida javob ber. "
    "Agar foydalanuvchi ruscha yozsa — ruscha javob ber. "
    "Agar inglizcha yozsa — inglizcha javob ber. "
    "Agar o'zbekcha yozsa — o'zbekcha javob ber. "
    "Javoblar professional, tushunarli va to'liq bo'lsin."
)


async def get_chat_response(messages: list) -> str:
    """OpenRouter orqali AI chat javobini olish."""
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
        return f"⚠️ AI xatosi: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"⚠️ Kutilmagan xato: {e}"


async def generate_image(prompt: str) -> str:
    """Rasm yaratish — hozircha mavjud emas."""
    return (
        "Error: Rasm yaratish funksiyasi hozircha mavjud emas. "
        "OpenRouter faqat matnli modellarni qo'llab-quvvatlaydi."
    )
