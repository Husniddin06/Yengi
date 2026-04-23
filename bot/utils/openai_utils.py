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
# Foydalanuvchi so'raganidek GPT-4o modelini asosiy qilamiz
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Foydalanuvchi yuborgan System Prompt
SYSTEM_PROMPT = """
You are a premium AI assistant like ChatGPT.

Rules (English):
- Speak naturally and intelligently.
- Give detailed, smart, useful answers.
- Understand user intent deeply.
- Be friendly and professional.
- If needed, ask follow-up questions.
- If user writes in English, reply in English.
- If user writes in Russian, reply in Russian.
- If user writes in Uzbek, reply in Uzbek.
- Always give high-quality responses.

Правила (Русский):
- Отвечай естественно и умно.
- Давай подробные, полезные ответы.
- Понимай смысл запроса глубоко.
- Будь дружелюбным и профессиональным.
- Если нужно, задавай уточняющие вопросы.
- Если пользователь пишет по-русски — отвечай по-русски.
- Если пишет по-английски — отвечай по-английски.
- Если пишет по-узбекски — отвечай по-узбекски.
- Всегда отвечай качественно.
"""

CHARACTERS = {
    "funny_banana": "You are a Funny Banana. You love jokes, puns about bananas, and you are very energetic and silly. Use emojis like 🍌, 😂, 🤪.",
    "wise_advisor": "You are a Wise Advisor. You give deep, thoughtful advice and speak in a calm, professional manner. Use emojis like 🧠, 📚, ✨.",
    "art_designer": "You are an Art Designer. You are creative, visual, and love talking about colors, styles, and aesthetics. Use emojis like 🎨, 🖌️, 🌈.",
    "default": SYSTEM_PROMPT
}

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

async def get_free_ai_response(prompt: str, system_prompt: str = None) -> str:
    """Free model (Pollinations) - used when OpenAI fails or key is missing"""
    try:
        if not system_prompt:
            system_prompt = SYSTEM_PROMPT
        
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=openai&system={urllib.parse.quote(system_prompt)}&search=true"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=25) as resp:
                if resp.status == 200:
                    raw_text = await resp.text()
                    return _strip_ads(raw_text)
        return "⚠️ System is busy. Please try again later."
    except Exception as e:
        logger.error(f"Free AI Error: {e}")
        return "⚠️ An error occurred. Please try again."

async def get_chat_response(user_message: str, history: list = None, character: str = "default") -> str:
    # Character bo'yicha system promptni tanlash
    base_system = CHARACTERS.get(character, SYSTEM_PROMPT)
    
    # If no client, use free model immediately
    if not client:
        return await get_free_ai_response(user_message, base_system)

    messages = [{"role": "system", "content": base_system}]
    
    # Foydalanuvchi yuborgan kod kabi oxirgi 10 ta xabarni olamiz
    if history:
        # Oxirgi 10 ta xabarni filtrlash
        recent_history = history[-10:]
        for h in recent_history:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append(h)
    
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.8, # Foydalanuvchi yuborgan temperature
            max_tokens=1000, # Foydalanuvchi yuborgan max_tokens
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        # Fallback to free model on any OpenAI error
        return await get_free_ai_response(user_message, base_system)

async def generate_image(prompt: str, style: str = "standard") -> str:
    final_prompt = prompt
    if style == "banana":
        final_prompt = (
            f"Ultra-realistic, cinematic, high-detail 3D render of {prompt} in a viral 'Nano Banana' style. "
            "The subject should be creatively integrated with a banana theme, funny, cute, or surreal. "
            "Vibrant colors, studio lighting, 8k resolution, trending on social media, Gemini AI style."
        )
    
    try:
        if client:
            response = await client.images.generate(
                model="dall-e-3", 
                prompt=final_prompt, 
                n=1,
                size="1024x1024",
                quality="hd" if style == "banana" else "standard"
            )
            return response.data[0].url
    except Exception as e:
        logger.error(f"DALL-E Error: {e}")
    
    # Fallback to free image generator (Pollinations)
    encoded = urllib.parse.quote(final_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&seed={os.urandom(4).hex()}"

async def analyze_image_and_chat(prompt: str, image_bytes: bytes) -> str:
    try:
        if not client: 
            return "📸 Image received! (Vision requires OpenAI API Key)."
            
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt or "Analyze this image and provide a detailed generation prompt for it."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return f"⚠️ Vision Error: {str(e)}."

async def transcribe_audio(file_path: str) -> str:
    try:
        if not client: return "🎙 Audio received! (Transcription requires OpenAI API Key)."
        with open(file_path, "rb") as f:
            ts = await client.audio.transcriptions.create(model="whisper-1", file=f)
            return ts.text
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return "⚠️ Audio Error. Please try again."
