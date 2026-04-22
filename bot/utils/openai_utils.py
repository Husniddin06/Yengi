import logging
import os
import urllib.parse
import base64
import aiohttp
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
    "Har doim foydalanuvchi tilida javob ber."
)

async def get_free_ai_response(prompt: str) -> str:
    """Bepul modeldan foydalanish (Pollinations)"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        # Tizim promptini ham qo'shamiz
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&system={urllib.parse.quote(SYSTEM_PROMPT)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.text()
        return "⚠️ Bepul AI xizmati vaqtincha ishlamayapti. Birozdan so'ng urinib ko'ring."
    except Exception as e:
        logger.error(f"Free AI error: {e}")
        return "⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."

async def web_search(query: str) -> str:
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
    # Eng oxirgi foydalanuvchi xabari
    user_msg = messages[-1]["content"]

    # Agar API kalit umuman yo'q bo'lsa, srazu bepulga o'tamiz
    if not OPENAI_API_KEY or len(str(OPENAI_API_KEY)) < 10:
        return await get_free_ai_response(user_msg)

    try:
        # Internet qidiruvi mantiqi
        if use_web:
            search_data = await web_search(user_msg)
            messages.append({"role": "system", "content": f"Internetdan qidiruv natijalari:\n{search_data}"})

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        # OpenAI ga so'rov yuboramiz
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=full_messages,
            max_tokens=2000,
            temperature=0.7,
            timeout=45 # Kutish vaqti
        )
        return response.choices[0].message.content
    except Exception as e:
        # HAR QANDAY XATOLIKDA (Kvota, API kalit, va hokazo) BEPUL MODELGA O'TAMIZ
        logger.error(f"OpenAI xatosi yuz berdi: {e}. Bepul modelga o'tilmoqda...")
        return await get_free_ai_response(user_msg)

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
        # Vision uchun bepul muqobil yo'q, lekin xatoni chiroyli ko'rsatamiz
        return "⚠️ Rasmni tahlil qilish uchun OpenAI kvotasi yetarli emas."

async def generate_image(prompt: str) -> str:
    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        # DALL-E ishlamasa, srazu Pollinations rasm generatoriga
        encoded = urllib.parse.quote(prompt)
        return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

async def transcribe_audio(file_path: str) -> str:
    try:
        with open(file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            return transcript.text
    except Exception as e:
        return ""

async def analyze_document(text: str, query: str) -> str:
    try:
        messages = [
            {"role": "system", "content": "Sen hujjatlarni tahlil qiluvchi yordamchisan."},
            {"role": "user", "content": f"Hujjat: {text}\n\nSavol: {query}"}
        ]
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return await get_free_ai_response(f"Hujjat tahlili (Savol: {query}): {text[:2000]}")
