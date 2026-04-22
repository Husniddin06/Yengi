import os
from dotenv import load_dotenv

# Mahalliy test uchun .env yuklanadi, Railway'da esa platforma o'zgaruvchilari ishlaydi
load_dotenv()

# Railway Variables bo'limidan olinadigan qiymatlar
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_ID_RAW = os.getenv('ADMIN_ID', '1999635628')

# Admin ID ni raqamga o'tkazishda xatolikni oldini olish
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except (ValueError, TypeError):
    ADMIN_ID = 1999635628

SPB_PAYMENT_LINK = os.getenv('SPB_PAYMENT_LINK', 'https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111&comment=PRO_50')
DEFAULT_DAILY_LIMIT = int(os.getenv('DEFAULT_DAILY_LIMIT', '10'))
DAILY_BONUS = int(os.getenv('DAILY_BONUS', '5'))
HISTORY_KEEP = int(os.getenv('HISTORY_KEEP', '100'))

# Bot ishga tushishi uchun eng zarur tekshiruv
if not BOT_TOKEN:
    print("XATOLIK: BOT_TOKEN topilmadi! Railway Variables bo'limini tekshiring.")
if not OPENAI_API_KEY:
    print("OGOHLANTIRISH: OPENAI_API_KEY topilmadi! AI funksiyalari ishlamasligi mumkin.")
