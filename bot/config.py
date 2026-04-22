import os

BOT_TOKEN = os.getenv('BOT_TOKEN', '8737740623:AAF3MGfbkGhh9yLj4_bD38YszGex0F3UB74')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')
ADMIN_ID = int(os.getenv('ADMIN_ID', '1999635628'))
SPB_PAYMENT_LINK = os.getenv('SPB_PAYMENT_LINK', 'https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111&comment=PRO_50')

DEFAULT_DAILY_LIMIT = int(os.getenv('DEFAULT_DAILY_LIMIT', '10'))
DAILY_BONUS = int(os.getenv('DAILY_BONUS', '5'))
HISTORY_KEEP = int(os.getenv('HISTORY_KEEP', '100'))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required (set it in Replit Secrets).")
