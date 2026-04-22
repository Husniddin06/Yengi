# SmartAI Bot - Replit Deployment Guide

Loyiha SmartAI Telegram botini Replit muhitida ishga tushirish uchun mo'ljallangan.

## Ishga tushirish
Botni ishga tushirish uchun quyidagi buyruqni ishlating:
```bash
python bot/main.py
```

## Kerakli Secrets (Environment Variables)
Replit Secrets bo'limida quyidagi o'zgaruvchilarni o'rnating:
- `BOT_TOKEN`: Telegram bot tokeni
- `ADMIN_ID`: Adminning Telegram ID raqami
- `OPENAI_API_KEY`: OpenRouter API kaliti
- `SPB_PAYMENT_LINK`: To'lov uchun Sberbank yoki boshqa havola
- `OPENROUTER_MODEL`: (Ixtiyoriy) Ishlatiladigan AI modeli (standart: `openai/gpt-oss-120b:free`)

## Muhim eslatmalar
- Bot **polling** rejimida ishlaydi, shuning uchun tashqi domen yoki HTTPS sertifikati talab qilinmaydi.
- Ma'lumotlar bazasi sifatida `aiosqlite` ishlatiladi (`database.db` fayli).
- Barcha xabarlar va mantiqiy xatolar `user_handlers.py` va `admin_handlers.py` fayllarida tuzatilgan.
