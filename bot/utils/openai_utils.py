import logging
import os
import urllib.parse
import base64
import aiohttp
from openai import AsyncOpenAI

# Loglarni sozlash
logger = logging.getLogger(__name__)

# O'zgaruvchilarni olish
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SYSTEM_PROMPT = "Sen SmartAI — kuchli va aqlli AI assistantsan. Foydalanuvchiga har doim foydalanuvchi tilida javob ber."

async def get_free_ai_response(prompt: str) -> str:
    """Bepul model (Pollinations) - OpenAI xato berganda ishlatiladi"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&system={urllib.parse.quote(SYSTEM_PROMPT)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                if resp.status == 200:
                    return await resp.text()
        return "⚠️ Hozirda tizim band. Iltimos, birozdan so'ng urinib ko'ring."
    except Exception as e:
        logger.error(f"Free AI Error: {e}")
        return "⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring."

async def get_chat_response(messages: list, use_web=False) -> str:
    user_msg = messages[-1]["content"]
    
    # Agar OpenAI kalit bo'lmasa, srazu bepulga
    if not client:
        return await get_free_ai_response(user_msg)

    try:
        # OpenAI ga so'rov
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=2000,
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        # HAR QANDAY XATOLIKDA BEPUL MODELGA O'TAMIZ
        logger.error(f"OpenAI xatosi: {e}")
        return await get_free_ai_response(user_msg)

async def generate_image(prompt: str) -> str:
    try:
        if client:
            response = await client.images.generate(model="dall-e-3", prompt=prompt, n=1)
            return response.data[0].url
    except:
        pass
    # Xato bo'lsa bepul rasm generatori
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

# Boshqa funksiyalar (Soddalashtirilgan)
async def analyze_image_and_chat(prompt: str, image_bytes: bytes) -> str:
    try:
        if not client: return "⚠️ OpenAI kalit yo'q."
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt or "Tahlil qil"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Xato: {str(e)}"

async def transcribe_audio(file_path: str) -> str:
    try:
        if not client: return ""
        with open(file_path, "rb") as f:
            ts = await client.audio.transcriptions.create(model="whisper-1", file=f)
            return ts.text
    except: return ""

async def analyze_document(text: str, query: str) -> str:
    return await get_chat_response([{"role": "user", "content": f"Hujjat: {text[:2000]}\nSavol: {query}"}])
    import re

def _strip_ads(text: str) -> str:
    """Pollinations javobidagi reklama bloklarini olib tashlash."""
    if not text:
        return text
    markers = [
        "**Support Pollinations",
        "🌸 **Ad**",
        "🌸 Ad 🌸",
        "Powered by Pollinations",
        "pollinations.ai/redirect",
    ]
    lowest = len(text)
    for m in markers:
        idx = text.find(m)
        if idx != -1 and idx < lowest:
            lowest = idx
    text = text[:lowest]
    text = re.sub(r"\n-{3,}\s*$", "", text)
    return text.strip()
