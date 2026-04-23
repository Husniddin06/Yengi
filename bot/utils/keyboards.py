from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

MENU_LABELS = {
    "ru": {
        "balance": "📊 Баланс", "premium": "💎 Премиум", "ref": "👥 Друзья",
        "help": "🆘 Помощь", "clear": "🗑 Очистить", "image": "🎨 Nano Image",
        "lang": "🌐 Язык", "bonus": "🎁 Бонус", "banana": "🍌 Nano Banana",
    },
    "en": {
        "balance": "📊 Balance", "premium": "💎 Premium", "ref": "👥 Friends",
        "help": "🆘 Help", "clear": "🗑 Clear", "image": "🎨 Nano Image",
        "lang": "🌐 Lang", "bonus": "🎁 Bonus", "banana": "🍌 Nano Banana",
    },
}

def _all_labels(key: str) -> set:
    return {MENU_LABELS[lang][key] for lang in MENU_LABELS}

BTN_BALANCE = _all_labels("balance")
BTN_PREMIUM = _all_labels("premium")
BTN_REF = _all_labels("ref")
BTN_HELP = _all_labels("help")
BTN_CLEAR = _all_labels("clear")
BTN_IMAGE = _all_labels("image")
BTN_LANG = _all_labels("lang")
BTN_BONUS = _all_labels("bonus")
BTN_BANANA = _all_labels("banana")

def main_menu(lang: str = "en") -> ReplyKeyboardMarkup:
    if lang not in MENU_LABELS:
        lang = "en"
    L = MENU_LABELS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=L["balance"]), KeyboardButton(text=L["premium"])],
            [KeyboardButton(text=L["image"]), KeyboardButton(text=L["banana"])],
            [KeyboardButton(text=L["ref"]), KeyboardButton(text=L["bonus"])],
            [KeyboardButton(text=L["clear"]), KeyboardButton(text=L["lang"]), KeyboardButton(text=L["help"])],
        ],
        resize_keyboard=True,
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
