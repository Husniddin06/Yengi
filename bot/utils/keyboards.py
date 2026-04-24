from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

MENU_LABELS = {
    "ru": {
        "vision": "📸 Get prompt from photo 📸",
        "profile": "👤 My Profile",
        "friends": "👥 Friends / Referral",
        "vip": "🌟 NANO BANANA VIP 🌟",
        "hype": "🔥 Hype Prompts 🔥",
        "lang": "🌐 Language / Язык",
        "help": "🆘 Help"
    },
    "en": {
        "vision": "📸 Get prompt from photo 📸",
        "profile": "👤 My Profile",
        "friends": "👥 Friends / Referral",
        "vip": "🌟 NANO BANANA VIP 🌟",
        "hype": "🔥 Hype Prompts 🔥",
        "lang": "🌐 Language / Язык",
        "help": "🆘 Help"
    },
}

def main_reply_menu(lang: str = "en") -> ReplyKeyboardMarkup:
    if lang not in MENU_LABELS:
        lang = "en"
    L = MENU_LABELS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=L["vision"])],
            [KeyboardButton(text=L["profile"]), KeyboardButton(text=L["friends"])],
            [KeyboardButton(text=L["vip"])],
            [KeyboardButton(text=L["hype"])],
            [KeyboardButton(text=L["lang"]), KeyboardButton(text=L["help"])]
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an option..."
    )

def characters_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    chars = {
        "ru": [
            ("🍌 Банан-Шутник", "char_funny_banana"),
            ("🧠 Мудрый Советник", "char_wise_advisor"),
            ("🎨 Арт-Дизайнер", "char_art_designer"),
            ("🤖 Стандартный ИИ", "char_default")
        ],
        "en": [
            ("🍌 Funny Banana", "char_funny_banana"),
            ("🧠 Wise Advisor", "char_wise_advisor"),
            ("🎨 Art Designer", "char_art_designer"),
            ("🤖 Default AI", "char_default")
        ]
    }
    L = chars.get(lang, chars["en"])
    keyboard = [[InlineKeyboardButton(text=name, callback_data=data)] for name, data in L]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")],
        ]
    )

def payment_options_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    texts = {
        "ru": {"sbp": "💳 СБП (75₽)", "stars": "⭐️ Telegram Stars (50 ⭐️)"},
        "en": {"sbp": "💳 SBP (75₽)", "stars": "⭐️ Telegram Stars (50 ⭐️)"}
    }
    L = texts.get(lang, texts["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=L["sbp"], callback_data="pay_sbp_request")],
            [InlineKeyboardButton(text=L["stars"], callback_data="pay_stars_1month")]
        ]
    )

def admin_payment_confirm_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm", callback_data=f"admin_confirm_pay_{payment_id}")],
            [InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_pay_{payment_id}")]
        ]
    )

def tasks_keyboard(tasks_list, lang="en") -> InlineKeyboardMarkup:
    keyboard = []
    for t in tasks_list:
        keyboard.append([InlineKeyboardButton(text=f"🔗 {t['title']} (+{t['reward']} 🪙)", url=t['url'])])
        keyboard.append([InlineKeyboardButton(text="✅ Проверить / Check", callback_data=f"check_task_{t['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
