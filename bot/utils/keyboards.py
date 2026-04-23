from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

MENU_LABELS = {
    "ru": {
        "nano": "🎨 NANO BANANA / AI",
        "vision": "📸 Получить промт по фото",
        "characters": "👽 Персонажи",
        "tiktok": "📱 TikTok режим",
        "profile": "👤 Мой профиль",
        "tariffs": "💎 Тарифы",
        "add_coins": "💸 Докинуть токенов",
        "hype": "🔥 Хайп промты 🔥",
        "tasks": "🎁 Задания (Бонус)",
        "lang": "🌐 Язык",
        "help": "🆘 Помощь"
    },
    "en": {
        "nano": "🎨 NANO BANANA / AI",
        "vision": "📸 Get prompt from photo",
        "characters": "👽 Characters",
        "tiktok": "📱 TikTok mode",
        "profile": "👤 My Profile",
        "tariffs": "💎 Tariffs",
        "add_coins": "💸 Add Coins",
        "hype": "🔥 Hype Prompts 🔥",
        "tasks": "🎁 Tasks (Bonus)",
        "lang": "🌐 Lang",
        "help": "🆘 Help"
    },
}

def main_inline_menu(lang: str = "en") -> InlineKeyboardMarkup:
    if lang not in MENU_LABELS:
        lang = "en"
    L = MENU_LABELS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=L["nano"], callback_data="menu_nano")],
            [InlineKeyboardButton(text=L["vision"], callback_data="menu_vision")],
            [InlineKeyboardButton(text=L["characters"], callback_data="menu_chars")],
            [InlineKeyboardButton(text=L["tiktok"], callback_data="menu_tiktok"), InlineKeyboardButton(text=L["profile"], callback_data="menu_profile")],
            [InlineKeyboardButton(text=L["tariffs"], callback_data="menu_tariffs")],
            [InlineKeyboardButton(text=L["add_coins"], callback_data="menu_add_coins")],
            [InlineKeyboardButton(text=L["hype"], callback_data="menu_hype")],
            [InlineKeyboardButton(text=L["tasks"], callback_data="menu_tasks")],
            [InlineKeyboardButton(text=L["lang"], callback_data="menu_lang"), InlineKeyboardButton(text=L["help"], callback_data="menu_help")]
        ]
    )

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
    
    back_text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    keyboard.append([InlineKeyboardButton(text=back_text, callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
