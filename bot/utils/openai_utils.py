import logging
import os
import sys
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
    """Agar OpenAI kvotasi tugasa, bepul modeldan foydalanish (Pollinations)"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&system={urllib.parse.quote(SYSTEM_PROMPT)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.text()
        return "⚠️ Hozirda barcha tizimlar band. Birozdan so'ng urinib ko'ring."
    except Exception as e:
        return f"⚠️ Xatolik yuz berdi: {str(e)}"

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
    if not OPENAI_API_KEY or OPENAI_API_KEY == "None":
        # Agar kalit bo'lmasa, bepul modelga o'tamiz
        last_msg = messages[-1]["content"]
        return await get_free_ai_response(last_msg)

    try:
        if use_web:
            last_query = messages[-1]["content"]
            search_data = await web_search(last_query)
            messages.append({"role": "system", "content": f"Internetdan qidiruv natijalari:\n{search_data}"})

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
        
        # AGAR KVOTA TUGAGAN BO'LSA, BEPUL MODELGA O'TAMIZ
        if "insufficient_quota" in error_str:
            logger.info("Kvota tugadi, bepul modelga o'tilmoqda...")
            last_msg = messages[-1]["content"]
            return await get_free_ai_response(last_msg)
            
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
        # Vision uchun bepul muqobil hozircha yo'q, shuning uchun xatoni qaytaramiz
        return f"⚠️ Rasmni tahlil qilishda kvota yetmadi: {str(e)}"

async def generate_image(prompt: str) -> str:
    try:
        # Kvota bo'lsa DALL-E 3
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        # Kvota tugasa bepul Pollinations.ai
        logger.info("DALL-E kvotasi tugadi, Pollinations'ga o'tilmoqda...")
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
        # Hujjat tahlili uchun ham bepul modelga o'tish mumkin
        return await get_free_ai_response(f"Hujjat: {text[:2000]}\n\nSavol: {query}")
