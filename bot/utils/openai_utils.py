import logging
import os
import urllib.parse
import base64
import aiohttp
import re
import json
import asyncio
from openai import AsyncOpenAI

# Log configuration
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

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
"""

CHARACTERS = {
    "funny_banana": "You are a Funny Banana. You love jokes, puns about bananas, and you are very energetic and silly. Use emojis like 🍌, 😂, 🤪.",
    "wise_advisor": "You are a Wise Advisor. You give deep, thoughtful advice and speak in a calm, professional manner. Use emojis like 🧠, 📚, ✨.",
    "art_designer": "You are an Art Designer. You are creative, visual, and love talking about colors, styles, and aesthetics. Use emojis like 🎨, 🖌️, 🌈.",
    "default": SYSTEM_PROMPT
}

def _strip_ads(text: str) -> str:
    if not text: return text
    markers = ["**Support Pollinations", "🌸 **Ad**", "🌸 Ad 🌸", "Powered by Pollinations", "pollinations.ai/redirect"]
    lowest = len(text)
    for m in markers:
        idx = text.find(m)
        if idx != -1 and idx < lowest: lowest = idx
    text = text[:lowest]
    text = re.sub(r"\n-{3,}\s*$", "", text)
    return text.strip()

async def get_openrouter_response(user_message: str, history: list = None, system_prompt: str = None) -> str:
    """OpenRouter API orqali javob olish"""
    if not OPENROUTER_API_KEY:
        return None
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})
    
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": messages
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=30) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    return res_json["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenRouter Error: {resp.status} - {await resp.text()}")
    except Exception as e:
        logger.error(f"OpenRouter Exception: {e}")
    return None

async def get_free_ai_response(prompt: str, system_prompt: str = None) -> str:
    try:
        if not system_prompt: system_prompt = SYSTEM_PROMPT
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
    base_system = CHARACTERS.get(character, SYSTEM_PROMPT)
    
    # 1. OpenRouter (GPT-4o-mini)
    response = await get_openrouter_response(user_message, history, base_system)
    if response:
        return response
        
    # 2. OpenAI (GPT-4o) Fallback
    if client:
        messages = [{"role": "system", "content": base_system}]
        if history:
            recent_history = history[-10:]
            for h in recent_history:
                if isinstance(h, dict) and "role" in h and "content" in h:
                    messages.append(h)
        messages.append({"role": "user", "content": user_message})
        try:
            response = await client.chat.completions.create(
                model=CHAT_MODEL, messages=messages, temperature=0.8, max_tokens=1000, timeout=30
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            
    # 3. Free AI Fallback
    return await get_free_ai_response(user_message, base_system)

async def generate_image(prompt: str, style: str = "standard") -> str:
    """Faqat OpenAI (DALL-E 3) orqali rasm yaratish. Bepul generator olib tashlandi."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate image.")
        return None

    final_prompt = prompt
    if style == "banana":
        final_prompt = (
            f"Ultra-realistic, cinematic, high-detail 3D render of {prompt} in a viral 'Nano Banana' style. "
            "The subject should be creatively integrated with a banana theme, funny, cute, or surreal. "
            "Vibrant colors, studio lighting, 8k resolution, trending on social media."
        )
    try:
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
        return None

async def edit_image_with_face(image_path: str, prompt: str) -> str:
    """Replicate InstantID orqali yuzni 100% saqlab qolgan holda rasmga ishlov berish"""
    try:
        if not REPLICATE_API_TOKEN:
            return await _edit_image_openai_fallback(image_path, prompt)
            
        async with aiohttp.ClientSession() as session:
            # InstantID model (fofr/instant-id)
            model_version = "ef70dcee6604870795493069004084394073380f089600984869766440263692"
            url = "https://api.replicate.com/v1/predictions"
            headers = {
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            with open(image_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
                img_data_url = f"data:image/jpeg;base64,{img_base64}"

            payload = {
                "version": model_version,
                "input": {
                    "image": img_data_url,
                    "prompt": f"{prompt}, ultra realistic, cinematic lighting, masterpiece, preserve same identity, 8k, highly detailed",
                    "negative_prompt": "ugly, blurry, deformed face, low quality, duplicate face, nsfw, distorted eyes, bad anatomy",
                    "guidance_scale": 8,
                    "num_inference_steps": 35,
                    "ip_adapter_scale": 0.8,
                    "controlnet_conditioning_scale": 0.8
                }
            }
            
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 201:
                    prediction = await resp.json()
                    prediction_id = prediction['id']
                    
                    for _ in range(45): # Max 90 seconds
                        async with session.get(f"{url}/{prediction_id}", headers=headers) as check_resp:
                            status_data = await check_resp.json()
                            if status_data['status'] == 'succeeded':
                                output = status_data['output']
                                return output[0] if isinstance(output, list) else output
                            elif status_data['status'] == 'failed':
                                logger.error(f"Replicate Prediction Failed: {status_data.get('error')}")
                                break
                        await asyncio.sleep(2)
        
        return await _edit_image_openai_fallback(image_path, prompt)
    except Exception as e:
        logger.error(f"Replicate Error: {e}")
        return await _edit_image_openai_fallback(image_path, prompt)

async def _edit_image_openai_fallback(image_path: str, prompt: str) -> str:
    try:
        if not client:
            return None
        with open(image_path, "rb") as img:
            response = await client.images.edit(
                model="dall-e-2",
                image=img,
                prompt=f"Maintain 100% identical facial structure of the person in the image. {prompt}, cinematic, realistic.",
                n=1,
                size="1024x1024"
            )
            return response.data[0].url
    except Exception as e:
        logger.error(f"OpenAI Edit Fallback Error: {e}")
        return None

async def analyze_image_and_chat(prompt: str, image_bytes: bytes) -> str:
    try:
        if not client: return "📸 Image received!"
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
        if not client: return "🎙 Audio received!"
        with open(file_path, "rb") as f:
            ts = await client.audio.transcriptions.create(model="whisper-1", file=f)
            return ts.text
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return "⚠️ Audio Error. Please try again."
