# SmartAI Telegram Bot

A powerful Telegram bot integrated with OpenAI's GPT-4o and DALL-E 3, supporting Russian and English.

## Features
- 🤖 **AI Chat**: Chat with GPT-4o-mini (or your preferred model).
- 🎨 **Image Generation**: Create stunning images using DALL-E 3.
- 🌐 **Multi-language**: Full support for Russian and English.
- 💎 **Premium System**: Manage user limits and premium subscriptions.
- 🎁 **Daily Bonuses**: Users can claim daily request bonuses.
- 👥 **Referral System**: Invite friends to earn more requests.
- 🎟 **Promo Codes**: Create and redeem promo codes for premium/requests.
- 📊 **Admin Panel**: Comprehensive statistics and broadcast tools.

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/Husniddin06/Yengi.git
cd Yengi
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory based on `.env.example`:
```bash
cp .env.example .env
```
Edit `.env` and add your tokens:
- `BOT_TOKEN`: Your Telegram Bot Token from [@BotFather](https://t.me/BotFather).
- `OPENAI_API_KEY`: Your OpenAI API Key.
- `ADMIN_ID`: Your Telegram User ID (for admin access).

### 4. Run the bot
```bash
python bot/main.py
```

## Deployment
The bot is ready for deployment on platforms like **Railway**, **Heroku**, or **VPS**.
- Ensure all environment variables are set in your deployment platform's settings.
- The bot uses SQLite for data storage (`smartai_bot.db`).

## License
MIT
