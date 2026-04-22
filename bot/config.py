import os
from dotenv import load_dotenv

load_dotenv()

# Railway Variables bo'limidan olinadi
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID', '1999635628'))
SPB_PAYMENT_LINK = os.getenv('SPB_PAYMENT_LINK', 'https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111&comment=PRO_50')

DEFAULT_DAILY_LIMIT = int(os.getenv('DEFAULT_DAILY_LIMIT', '10'))
DAILY_BONUS = int(os.getenv('DAILY_BONUS', '5'))
HISTORY_KEEP = int(os.getenv('HISTORY_KEEP', '100'))

if not BOT_TOKEN:
    # Faqat Railway'da xato bermasligi uchun
    pass
