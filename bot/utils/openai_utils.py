import logging
import os
import sys
import urllib.parse
import base64
from openai import AsyncOpenAI
from config import OPENAI_API_KEY
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# OpenAI modelini tanlaymiz
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "Sen SmartAI — kuchli va aqlli AI assistantsan. "
    "Foydalanuvchiga har qanday savol bo'yicha batafsil, aniq va foydali javob ber. "
    "Har doim foydalanuvchi tilida javob ber. "
    "Javoblar professional, tushunarli va to'liq bo'lsin."
)

async def web_search(query: str) -> str:
    """DuckDuckGo orqali internetdan qidirish"""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"Sarlavha: {r['title']}\nMa'lumot: {r['body']}\nLink: {r['href']}")
        return "\n\n".join(results) if results else "Ma'lumot topilmadi."
    except Exception as e:
        logger.error(f"Search error: {e}")
        return "Qidiruvda xatolik yuz berdi."

async def get_chat_response(messages: list, use_web=False) -> str:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "None":
        return "⚠️ Xatolik: OPENAI_API_KEY Railway Variables bo'limida o'rnatilmagan yoki noto'g'ri!"

    try:
        # Agar internetdan qidirish yoqilgan bo'lsa
        if use_web:
            last_query = messages[-1]["content"]
            search_data = await web_search(last_query)
            messages.append({"role": "system", "content": f"Internetdan qidiruv natijalari:\n{search_data}\n\nUshbu ma'lumotlardan foydalanib javob ber."})

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=full_messages,
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        error_str = str(e)
        if "insufficient_quota" in error_str:
            return "⚠️ OpenAI xatosi: Hisobingizda mablag' tugagan (Insufficient Quota)."
        elif "invalid_api_key" in error_str:
            return "⚠️ OpenAI xatosi: API kalit noto'g'ri kiritilgan (Invalid API Key)."
        return f"⚠️ OpenAI xatosi: {error_str}"

async def analyze_image_and_chat(prompt: str, image_bytes: bytes) -> str:
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt if prompt else "Ushbu rasmda nima tasvirlangan?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision error: {e}")
        return f"⚠️ Rasmni tahlil qilishda xatolik: {str(e)}"

async def generate_image(prompt: str) -> str:
    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"DALL-E error: {e}")
        encoded = urllib.parse.quote(prompt)
        return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

async def edit_image(image_path: str, prompt: str) -> str:
    """Rasmga o'zgartirish kiritish (DALL-E Edit)"""
    try:
        response = await client.images.edit(
            image=open(image_path, "rb"),
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"Image Edit error: {e}")
        return f"⚠️ Rasmni tahrirlashda xatolik: {str(e)}"

async def transcribe_audio(file_path: str) -> str:
    try:
        with open(file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            return transcript.text
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return ""

async def analyze_document(text: str, query: str) -> str:
    try:
        messages = [
            {"role": "system", "content": "Sen hujjatlarni tahlil qiluvchi yordamchisan. Quyidagi matn asosida savolga javob ber."},
            {"role": "user", "content": f"Hujjat matni:\n{text}\n\nSavol: {query}"}
        ]
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return f"⚠️ Hujjatni tahlil qilishda xatolik: {str(e)}"
