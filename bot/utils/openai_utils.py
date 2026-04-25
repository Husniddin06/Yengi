import os
import logging
import aiohttp
import replicate
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
    """Generate image using DALL-E 3"""
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is missing for DALL-E 3")
        return None
        
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"Viral, funny, ultra-realistic banana style, Gemini trend: {prompt}",
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"DALL-E Error: {e}")
        return None

async def edit_image_with_face(image_path, prompt):
    """Face Identity using Replicate InstantID"""
    if not REPLICATE_API_TOKEN:
        logger.error("REPLICATE_API_TOKEN is missing")
        return await generate_image(prompt)
        
    replicate_client = replicate.Client(auth=REPLICATE_API_TOKEN)
    
    try:
        output = replicate_client.run(
            "fofr/instant-id:6af8543fbf38519100e338e5219b118f07f051ae9997ca21ff6d9d9ec9dae9ad",
            input={
                "image": open(image_path, "rb"),
                "prompt": f"High-quality cinematic portrait, {prompt}",
                "negative_prompt": "ugly, deformed, noisy, blurry, low quality",
                "ip_adapter_scale": 0.8,
                "controlnet_conditioning_scale": 0.8,
                "guidance_scale": 7.5,
                "num_inference_steps": 30,
                "enhance_face_region": True
            }
        )
        if isinstance(output, list) and len(output) > 0:
            return output[0]
        return output
    except Exception as e:
        logger.error(f"Replicate Error: {e}")
        return await generate_image(prompt)

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
