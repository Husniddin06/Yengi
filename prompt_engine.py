# =================================
# NANO BANANA PROMPT ENGINE (MAX VERSION)
# Put this into your Telegram bot project
# ==========================================

from openai import OpenAI

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")


def build_prompt(user_text):
    text = user_text.lower()

    # ------------------------------
    # BILLIONAIRE / RICH
    # ------------------------------
    if any(word in text for word in ["boy", "rich", "millioner", "billionaire", "dubai"]):
        return """
Use the uploaded face. Keep identity recognizable.
Ultra realistic portrait of the person as a billionaire in Dubai.
Luxury black suit, expensive watch, Rolls Royce nearby,
sunset skyline, cinematic lighting, sharp facial details,
premium lifestyle, powerful confident pose, 8k masterpiece.
"""

    # ------------------------------
    # CEO / BUSINESS
    # ------------------------------
    elif any(word in text for word in ["ceo", "boss", "business"]):
        return """
Use the uploaded face. Keep identity recognizable.
Professional CEO portrait inside a modern skyscraper office.
Luxury suit, clean hairstyle, serious confident expression,
city skyline background, cinematic business lighting,
hyper realistic, LinkedIn premium style, 8k quality.
"""

    # ------------------------------
    # GYM
    # ------------------------------
    elif any(word in text for word in ["gym", "body", "muscle", "fitness"]):
        return """
Use the uploaded face. Keep identity recognizable.
Athletic muscular body inside a premium gym.
Strong confident pose, sharp jawline,
realistic skin texture, dramatic lighting,
fitness magazine quality, ultra realistic.
"""

    # ------------------------------
    # ANIME
    # ------------------------------
    elif any(word in text for word in ["anime", "naruto", "hero"]):
        return """
Use the uploaded face. Keep facial resemblance.
Epic anime hero portrait.
Detailed eyes, dramatic hair, glowing background,
dynamic pose, ultra detailed anime art,
vibrant colors, masterpiece quality.
"""

    # ------------------------------
    # KING / ROYAL
    # ------------------------------
    elif any(word in text for word in ["king", "prince", "royal"]):
        return """
Use the uploaded face. Keep identity recognizable.
Royal king portrait sitting on golden throne.
Luxury crown, expensive royal clothes,
dramatic palace background, cinematic light,
powerful legendary aura, ultra realistic.
"""

    # ------------------------------
    # DEFAULT SMART PROMPT
    # ------------------------------
    else:
        return f"""
Use the uploaded face. Keep identity recognizable.
Create a high quality ultra realistic image of the person:
{user_text}

Sharp facial details, cinematic lighting,
professional composition, premium quality, 8k.
"""


# ==========================================
# Example usage in your /img command:
# prompt = build_prompt(user_text)
#
