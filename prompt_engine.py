# =================================
# NANO BANANA PROMPT ENGINE (GEMINI VERSION)
# This version uses Google Gemini to enhance user prompts
# ==========================================

import os
import google.generativeai as genai

# Gemini API sozlamalari
# Railway'da GEMINI_API_KEY nomli o'zgaruvchi qo'shishni unutmang
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def build_prompt_with_gemini(user_text):
    """
    Foydalanuvchi matnini Gemini orqali tahlil qilib, 
    professional rasm promptiga aylantiradi.
    """
    
    # Gemini modelini tanlash
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Tizim ko'rsatmasi (System Instruction)
    system_prompt = """
    You are an expert AI Image Prompt Engineer. 
    Your task is to take a user's short description and turn it into a high-quality, 
    detailed, and professional prompt for image generation (like DALL-E 3 or Midjourney).
    
    Rules:
    1. Always start with: "Use the uploaded face. Keep identity recognizable."
    2. Expand the user's idea into a cinematic scene.
    3. Include details about lighting, camera angle, clothing, and environment.
    4. Use keywords like: "8k masterpiece", "ultra realistic", "cinematic lighting", "sharp facial details".
    5. Keep the final output concise but descriptive (max 100 words).
    6. Output ONLY the final prompt text.
    """
    
    try:
        # Gemini'dan javob olish
        response = model.generate_content(f"{system_prompt}\n\nUser text: {user_text}")
        return response.text.strip()
    except Exception as e:
        # Xatolik yuz bersa, oddiy formatga qaytish
        return f"Use the uploaded face. Keep identity recognizable. Ultra realistic portrait of {user_text}, 8k, cinematic lighting."

# ==========================================
# Example usage in your /img command:
# prompt = build_prompt_with_gemini(user_text)
# print(prompt)
# ==========================================
