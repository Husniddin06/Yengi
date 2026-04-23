import logging
import os
import urllib.parse
import base64
import aiohttp
import re
from openai import AsyncOpenAI

# Log configuration
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. You can answer questions, generate text, and help with various tasks. "
    "Respond in the language the user is speaking to you in (Russian or English)."
)

def _strip_ads(text: str) -> str:
    """Remove ad blocks from Pollinations response."""
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

async def get_free_ai_response(prompt: str) -> str:
    """Free model (Pollinations) - used when OpenAI fails or key is missing"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&system={urllib.parse.quote(SYSTEM_PROMPT)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                if resp.status == 200:
                    raw_text = await resp.text()
                    return _strip_ads(raw_text)
        return "⚠️ System is busy. Please try again later."
    except Exception as e:
        logger.error(f"Free AI Error: {e}")
        return "⚠️ An error occurred. Please try again."

async def get_chat_response(user_message: str, history: list = None) -> str:
    # If no OpenAI key, use free model
    if not client:
        return await get_free_ai_response(user_message)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        # Filter history to ensure it's in the correct format for OpenAI
        for h in history:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append(h)
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=2000,
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        return await get_free_ai_response(user_message)

async def generate_image(prompt: str) -> str:
    try:
        if client:
            response = await client.images.generate(
                model="dall-e-3", 
                prompt=prompt, 
                n=1,
                size="1024x1024"
            )
            return response.data[0].url
    except Exception as e:
        logger.error(f"DALL-E Error: {e}")
    
    # Fallback to free image generator
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"

async def analyze_image_and_chat(prompt: str, image_bytes: bytes) -> str:
    try:
        if not client: return "⚠️ OpenAI key is missing."
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt or "Analyze this image"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return f"⚠️ Error: {str(e)}"

async def transcribe_audio(file_path: str) -> str:
    try:
        if not client: return ""
        with open(file_path, "rb") as f:
            ts = await client.audio.transcriptions.create(model="whisper-1", file=f)
            return ts.text
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return ""
