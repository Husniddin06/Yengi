import os
import base64
import logging
import aiohttp
import replicate
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY or OPENROUTER_API_KEY or "dummy_key")

async def get_chat_response(message_text, history, character="default"):
    """Get response from OpenAI GPT-4o (Primary) or OpenRouter (Fallback)"""
    # Prefer direct OpenAI GPT-4o for best quality
    api_key = OPENAI_API_KEY or OPENROUTER_API_KEY
    
    system_prompts = {
        "default": "You are a premium AI assistant like ChatGPT. Speak naturally, give detailed and smart answers. Support English, Russian, and Uzbek.",
        "funny_banana": "You are a funny, viral banana character. Use banana puns and be hilarious!",
        "wise_advisor": "You are a wise and calm advisor. Give deep, philosophical and practical advice.",
        "art_designer": "You are a creative art designer. Help users with prompts and artistic ideas."
    }
    
    system_prompt = system_prompts.get(character, system_prompts["default"])
    
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-20:]:
        role = h.get("role") or "user"
        content = h.get("content") or h.get("user_message") or h.get("bot_message") or ""
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message_text})

    # Try OpenAI Direct first
    if OPENAI_API_KEY:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Direct Error: {e}")

    # Fallback to OpenRouter
    if OPENROUTER_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "openai/gpt-4o",
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
            logger.error(f"OpenRouter Fallback Error: {e}")
    
    return "⚠️ System is busy. Please check API keys."

async def generate_image(prompt):
    """Generate image from text prompt via Replicate (Flux 1.2 Pro).
    Returns image URL on success, or None on failure.
    """
    if not REPLICATE_API_TOKEN:
        logger.error("REPLICATE_API_TOKEN is missing")
        return None
    
    try:
        # Using Flux 1.2 Pro - The latest and most advanced model
        output = await replicate.async_run(
            "black-forest-labs/flux-1.2-pro",
            input={
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "output_format": "jpg",
                "output_quality": 95
            }
        )
        if output:
            return str(output)
        return None
    except Exception as e:
        logger.error(f"Replicate Flux 1.2 Pro exception: {e}")
        return None

async def edit_image_with_face(image_paths, prompt):
    """Image(s) + prompt -> image via Replicate (InstantID).
    Returns image URL on success, or None on failure.
    """
    if not REPLICATE_API_TOKEN:
        logger.error("REPLICATE_API_TOKEN is missing")
        return None
    
    if isinstance(image_paths, (str, bytes)):
        image_paths = [image_paths]
    
    image_paths = [p for p in (image_paths or []) if os.path.exists(p)]
    if not image_paths:
        logger.error("No valid input images provided")
        return None

    try:
        # Using InstantID on Replicate
        with open(image_paths[0], "rb") as f:
            output = await replicate.async_run(
                "lucataco/instantid:15a0e92730055099f0619885890938686d634939230800608c769666b44994d7",
                input={
                    "image": f,
                    "prompt": prompt,
                    "negative_prompt": "(lowres, low quality, worst quality:1.2), (text:1.2), watermark, painting, drawing, illustration, glitch, deformed, mutated, cross-eyed, ugly, disfigured",
                    "scheduler": "EulerDiscreteScheduler",
                    "num_inference_steps": 30,
                    "guidance_scale": 5,
                    "adapter_strength_ratio": 0.8,
                    "identity_net_strength_ratio": 0.8
                }
            )
            if output and len(output) > 0:
                return output[0]
            return None
    except Exception as e:
        logger.error(f"Replicate InstantID exception: {e}")
        return None

async def analyze_image_and_chat(image_path, prompt):
    """Analyze image using GPT-4o Vision"""
    if not OPENAI_API_KEY: return "❌ OpenAI API key missing."
    
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        )
        return response.choices[0].message.content
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
