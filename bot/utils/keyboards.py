from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

MENU_LABELS = {
    "ru": {
        "balance": "📊 Баланс", "premium": "💎 Премиум", "ref": "👥 Друзья",
        "help": "🆘 Помощь", "clear": "🗑 Очистить", "image": "🎨 Картинка",
        "lang": "🌐 Язык", "bonus": "🎁 Бонус",
    },
    "en": {
        "balance": "📊 Balance", "premium": "💎 Premium", "ref": "👥 Friends",
        "help": "🆘 Help", "clear": "🗑 Clear", "image": "🎨 Image",
        "lang": "🌐 Lang", "bonus": "🎁 Bonus",
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

def main_menu(lang: str = "en") -> ReplyKeyboardMarkup:
    if lang not in MENU_LABELS:
        lang = "en"
    L = MENU_LABELS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=L["balance"]), KeyboardButton(text=L["premium"])],
            [KeyboardButton(text=L["image"]), KeyboardButton(text=L["ref"])],
            [KeyboardButton(text=L["bonus"]), KeyboardButton(text=L["clear"])],
            [KeyboardButton(text=L["lang"]), KeyboardButton(text=L["help"])],
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
            [InlineKeyboardButton(text=L["sbp"], url="https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79990402614&bankCode=100000000111&comment=Premium_1_Month")],
            [InlineKeyboardButton(text=L["stars"], callback_data="pay_stars_1month")]
        ]
    )
