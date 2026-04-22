import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openai import AsyncOpenAI, OpenAIError
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full_messages,
            max_tokens=2048,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return f"⚠️ AI xatosi: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"⚠️ Kutilmagan xato: {e}"


async def generate_image(prompt: str) -> str:
    try:
        response = await client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            n=1,
            size="1024x1024",
        )
        return response.data[0].url
    except OpenAIError as e:
        logger.error(f"OpenAI Image API error: {e}")
        return f"⚠️ Rasm yaratish xatosi: {e}"
    except Exception as e:
        logger.error(f"Unexpected image error: {e}")
        return f"⚠️ Kutilmagan xato: {e}"
