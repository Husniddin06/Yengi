import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

SYSTEM_PROMPT = "Sen SmartAI, kuchli AI assistantsan. Foydalanuvchiga har qanday savol bo'yicha batafsil, aniq va foydali javob ber. Har doim foydalanuvchi tilida javob ber."

async def get_chat_response(messages):
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=full_messages
        )
        return response.choices[0].message.content
    except openai.error.RateLimitError:
        return "Error: Too many requests. Please try again later." # Or a localized message
    except openai.error.AuthenticationError:
        return "Error: OpenAI API key is invalid." # Or a localized message
    except openai.error.APIError as e:
        return f"Error: OpenAI API error: {e}" # Or a localized message
    except Exception as e:
        return f"Error: An unexpected error occurred: {e}"

async def generate_image(prompt):
    try:
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except openai.error.RateLimitError:
        return "Error: Too many image generation requests. Please try again later." # Or a localized message
    except openai.error.AuthenticationError:
        return "Error: OpenAI API key is invalid for image generation." # Or a localized message
    except openai.error.APIError as e:
        return f"Error: OpenAI API image error: {e}" # Or a localized message
    except Exception as e:
        return f"Error: An unexpected error occurred during image generation: {e}"
