from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

MENU_LABELS = {
    "uz": {
        "balance": "📊 Balans", "premium": "💎 Premium", "ref": "👥 Do'stlar",
        "help": "🆘 Yordam", "clear": "🗑 Tozalash", "image": "🎨 Rasm",
        "lang": "🌐 Til", "bonus": "🎁 Bonus",
    },
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
    L = MENU_LABELS.get(lang, MENU_LABELS["en"])
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
            [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="setlang_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")],
        ]
    )
