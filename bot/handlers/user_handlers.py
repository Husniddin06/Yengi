# Premium tugmasi endi to'lov oynasini ochadi:
@user_router.message(Command("premium"))
@user_router.message(F.text.in_(BTN_PREMIUM))
async def cmd_premium(message: Message):
    await _send_premium_invoice(message)

# Yordam tugmasi:
@user_router.message(Command("help"))
@user_router.message(F.text.in_(BTN_HELP))
async def cmd_help(message: Message): ...

# Til tugmasi + callback:
@user_router.message(F.text.in_(BTN_LANG))
async def cmd_lang(message: Message):
    await message.answer("Tilni tanlang...", reply_markup=lang_keyboard())

@user_router.callback_query(F.data.startswith("setlang_"))
async def set_lang(cb: CallbackQuery): ...

# Do'stlar (referal):
@user_router.message(F.text.in_(BTN_REF))
async def cmd_ref(message: Message):
    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref{message.from_user.id}"
    await message.answer(f"👥 ...\n{link}")

# Bonus:
@user_router.message(F.text.in_(BTN_BONUS))
async def cmd_bonus(message: Message):
    ok = await db.claim_daily_bonus(message.from_user.id, DAILY_BONUS)
    ...

# Balans, Tozalash, Rasm — alohida handlerlar
