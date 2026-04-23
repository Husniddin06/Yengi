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

CHARACTERS = {
    "funny_banana": "You are a Funny Banana. You love jokes, puns about bananas, and you are very energetic and silly. Use emojis like 🍌, 😂, 🤪.",
    "wise_advisor": "You are a Wise Advisor. You give deep, thoughtful advice and speak in a calm, professional manner. Use emojis like 🧠, 📚, ✨.",
    "art_designer": "You are an Art Designer. You are creative, visual, and love talking about colors, styles, and aesthetics. Use emojis like 🎨, 🖌️, 🌈.",
    "default": "You are a helpful AI assistant. You are polite, concise, and accurate. Respond in the language the user is speaking to you in (Russian or English)."
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
            system_prompt = CHARACTERS["default"]
        
        # Add search capability to prompt if it looks like a search query
        search_keywords = ["news", "today", "current", "price", "weather", "latest"]
        if any(word in prompt.lower() for word in search_keywords):
            prompt = f"Search the web for: {prompt}. Provide the latest information."

        encoded_prompt = urllib.parse.quote(prompt)
        # Using search=true for web search capability in Pollinations
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
    system_prompt = CHARACTERS.get(character, CHARACTERS["default"])
    
    # If no client, use free model immediately
    if not client:
        return await get_free_ai_response(user_message, system_prompt)

    messages = [{"role": "system", "content": system_prompt}]
    if history:
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
        # Fallback to free model on any OpenAI error
        return await get_free_ai_response(user_message, system_prompt)

async def generate_image(prompt: str, style: str = "standard") -> str:
    """
    Generates an image using DALL-E 3 or Pollinations.
    If style is 'banana', it applies the Nano Banana trend prompt engineering.
    """
    final_prompt = prompt
    if style == "banana":
        # Nano Banana trend prompt engineering
        final_prompt = (
            f"Ultra-realistic, cinematic, high-detail 3D render of {prompt} in a viral 'Nano Banana' style. "
            "The subject should be creatively integrated with a banana theme, funny, cute, or surreal. "
            "Vibrant colors, studio lighting, 8k resolution, trending on social media, Gemini AI style."
        )
    elif style == "video_prompt":
        final_prompt = (
            f"Cinematic video frame of {prompt}, Sora 2 style, hyper-realistic, 4k, motion blur, "
            "dynamic lighting, professional cinematography."
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
            # If no OpenAI, we can't do vision easily, but we can try a generic response
            return "📸 Image received! (Vision requires OpenAI API Key). To get a prompt, please ensure your API key is active."
            
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": CHARACTERS["default"]},
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
        return f"⚠️ Vision Error: {str(e)}. Please check your API key or try again later."

async def transcribe_audio(file_path: str) -> str:
    try:
        if not client: return "🎙 Audio received! (Transcription requires OpenAI API Key)."
        with open(file_path, "rb") as f:
            ts = await client.audio.transcriptions.create(model="whisper-1", file=f)
            return ts.text
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return "⚠️ Audio Error. Please try again."
