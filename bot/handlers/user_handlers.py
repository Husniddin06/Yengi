import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.enums import ChatAction
from datetime import datetime, timedelta

from bot.database import db
from bot.utils.openai_utils import (
    get_chat_response, generate_image, analyze_image_and_chat, transcribe_audio,
)
from bot.utils.keyboards import (
    main_menu, lang_keyboard,
    BTN_BALANCE, BTN_CLEAR, BTN_IMAGE, BTN_PREMIUM,
    BTN_HELP, BTN_REF, BTN_LANG, BTN_BONUS,
)
from bot.config import DAILY_BONUS

logger = logging.getLogger(__name__)
user_router = Router()
