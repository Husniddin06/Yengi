import os
from dotenv import load_dotenv

# Load .env for local testing
load_dotenv()

# Railway Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_ID_RAW = os.getenv('ADMIN_ID', '1999635628')

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except (ValueError, TypeError):
    ADMIN_ID = 1999635628

SPB_PAYMENT_LINK = os.getenv('SPB_PAYMENT_LINK', 'https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111&comment=Premium_150_Coins')
DAILY_BONUS = 1 # Kunlik 1 tanga
