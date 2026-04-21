import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def get_chat_response(prompt):
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

async def generate_image(prompt):
    try:
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        return f"Error: {e}"
