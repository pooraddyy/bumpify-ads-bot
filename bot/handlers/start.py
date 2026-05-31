from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.config import START_IMAGE_URL, START_CAPTION, LOGGER_BOT_USERNAME, WEB_APP_URL
from bot.utils import db


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, {"user_id": user.id, "username": user.username or ""})

    caption = START_CAPTION
    if LOGGER_BOT_USERNAME:
        caption += (
            f"\n\n<blockquote><b>Important:</b> Start @{LOGGER_BOT_USERNAME} first "
            "to receive real-time broadcast logs.</blockquote>"
        )

    second_row = [InlineKeyboardButton("FAQ", callback_data="faq", api_kwargs={"style": "primary"})]
    if WEB_APP_URL:
        second_row.append(InlineKeyboardButton("Web Panel", web_app=WebAppInfo(url=WEB_APP_URL), api_kwargs={"style": "primary"}))

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Open Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})],
        second_row,
        [InlineKeyboardButton("How To Use", callback_data="howto", api_kwargs={"style": "primary"})],
    ])

    if START_IMAGE_URL:
        try:
            await update.message.reply_photo(
                photo=START_IMAGE_URL,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    await update.message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)
