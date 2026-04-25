import os
import base64
import logging
import aiohttp
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load keys from environment variables (Railway)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY or OPENROUTER_API_KEY or "dummy_key")

async def get_chat_response(message_text, history, character="default"):
    """Get response from OpenRouter (Primary) or OpenAI (Fallback)"""
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    
    system_prompts = {
        "default": "You are a premium AI assistant like ChatGPT. Speak naturally, give detailed and smart answers. Support English, Russian, and Uzbek.",
        "funny_banana": "You are a funny, viral banana character. Use banana puns and be hilarious!",
        "wise_advisor": "You are a wise and calm advisor. Give deep, philosophical and practical advice.",
        "art_designer": "You are a creative art designer. Help users with prompts and artistic ideas."
    }
    
    system_prompt = system_prompts.get(character, system_prompts["default"])
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:
        messages.append({"role": "user", "content": h['user_message']})
        messages.append({"role": "assistant", "content": h['bot_message']})
    messages.append({"role": "user", "content": message_text})

    if api_key:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "openai/gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 1000
                }
                async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result['choices'][0]['message']['content']
                    else:
                        logger.error(f"OpenRouter Error: {await resp.text()}")
        except Exception as e:
            logger.error(f"Chat Error: {e}")

    # Fallback to OpenAI
    if OPENAI_API_KEY:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Fallback Error: {e}")
    
    return "⚠️ System is busy. Please check API keys in Railway."

async def generate_image(prompt):
    """Generate image from text prompt via OpenRouter (Gemini 2.5 Flash Image / Nano Banana).
    Returns raw image bytes on success, or None on failure.
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is missing for image generation")
        return None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "google/gemini-2.5-flash-image",
        "modalities": ["image", "text"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Generate a high-quality, viral, ultra-realistic image. "
                            "Subject: " + (prompt or "")
                        ),
                    }
                ],
            }
        ],
    }
    try:
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
            ) as resp:
                if resp.status != 200:
                    logger.error(
                        f"OpenRouter image gen error {resp.status}: {await resp.text()}"
                    )
                    return None
                result = await resp.json()
                msg = result.get("choices", [{}])[0].get("message", {}) or {}
                images = msg.get("images") or []
                if images:
                    url = images[0].get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        try:
                            return base64.b64decode(url.split(",", 1)[1])
                        except Exception as e:
                            logger.error(f"Failed to decode image data URL: {e}")
                            return None
                    if url:
                        return url
                logger.error(f"OpenRouter returned no images: {result}")
                return None
    except Exception as e:
        logger.error(f"OpenRouter image gen exception: {e}")
        return None

async def edit_image_with_face(image_paths, prompt):
    """Image(s) + prompt -> image via OpenRouter (Gemini 2.5 Flash Image / Nano Banana).
    `image_paths` may be a single path string or a list of paths (up to 6). Multiple
    reference photos help the model lock in the person's identity / face.
    Returns raw image bytes on success, or None on failure.
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is missing for image editing")
        return None
    if isinstance(image_paths, (str, bytes)):
        image_paths = [image_paths]
    image_paths = [p for p in (image_paths or []) if p]
    if not image_paths:
        logger.error("No input images provided")
        return None
    image_paths = image_paths[:6]
    image_parts = []
    for p in image_paths:
        try:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        except Exception as e:
            logger.error(f"Failed to read input image {p}: {e}")
    if not image_parts:
        return None
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    intro = (
        f"You are given {len(image_parts)} reference photo(s) of the same person. "
        "Use ALL of them together to lock in the person's identity, face shape, "
        "and features as accurately as possible. Generate a NEW image where the "
        "person's face stays clearly recognizable. Apply this transformation: "
        + (prompt or "")
    )
    data = {
        "model": "google/gemini-2.5-flash-image",
        "modalities": ["image", "text"],
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": intro}] + image_parts,
            }
        ],
    }
    try:
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
            ) as resp:
                if resp.status != 200:
                    logger.error(
                        f"OpenRouter image edit error {resp.status}: {await resp.text()}"
                    )
                    return None
                result = await resp.json()
                msg = result.get("choices", [{}])[0].get("message", {}) or {}
                images = msg.get("images") or []
                if images:
                    url = images[0].get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        try:
                            return base64.b64decode(url.split(",", 1)[1])
                        except Exception as e:
                            logger.error(f"Failed to decode image data URL: {e}")
                            return None
                    if url:
                        return url
                logger.error(f"OpenRouter returned no images: {result}")
                return None
    except Exception as e:
        logger.error(f"OpenRouter image edit exception: {e}")
        return None

async def analyze_image_and_chat(image_path, prompt):
    """Analyze image using GPT-4o Vision via OpenRouter"""
    api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not api_key: return "❌ API key missing."
    import base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            }
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        return "❌ Error analyzing image."

async def transcribe_audio(audio_path):
    """Transcribe audio using OpenAI Whisper"""
    if not OPENAI_API_KEY: return None
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return transcript.text
    except Exception as e:
        logger.error(f"Whisper Error: {e}")
        return None
