from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit


async def set_interval_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    current = await db.get_interval(update.effective_user.id)
    mins, secs = divmod(current, 60)
    current_label = f"{mins}m {secs}s" if mins else f"{secs}s"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("5 min", callback_data="interval_300", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("10 min", callback_data="interval_600", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("15 min", callback_data="interval_900", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("30 min", callback_data="interval_1800", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("1 hour", callback_data="interval_3600", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("2 hours", callback_data="interval_7200", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Custom", callback_data="interval_custom", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(
        query,
        f"<b>Set Interval</b>\n\n"
        f"<blockquote>Current interval: <b>{current_label}</b>\n"
        f"Select a preset or enter a custom value in seconds.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def interval_preset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, seconds: int):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.set_interval(user_id, seconds)
    mins, secs = divmod(seconds, 60)
    label = f"{mins}m {secs}s" if mins else f"{secs}s"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await safe_edit(
        query,
        f"<b>Interval set to {label}.</b>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def interval_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.set_waiting_for_interval(user_id, True)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="dashboard", api_kwargs={"style": "danger"})]])
    await safe_edit(
        query,
        "<b>Custom Interval</b>\n\n"
        "<blockquote>Send the interval in seconds.\n"
        "Example: <code>120</code> = 2 minutes, <code>3600</code> = 1 hour.\n"
        "Minimum: 60 seconds.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def handle_interval_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not await db.is_waiting_for_interval(user_id):
        return False
    await db.set_waiting_for_interval(user_id, False)
    text = (update.message.text or "").strip()
    try:
        seconds = int(text)
        if seconds < 60:
            seconds = 60
    except ValueError:
        await update.message.reply_text("Please send a valid number (seconds).")
        await db.set_waiting_for_interval(user_id, True)
        return True

    await db.set_interval(user_id, seconds)
    try:
        await update.message.delete()
    except Exception:
        pass

    mins, secs = divmod(seconds, 60)
    label = f"{mins}m {secs}s" if mins else f"{secs}s"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await update.message.reply_text(
        f"<b>Interval set to {label}.</b>",
        parse_mode="HTML", reply_markup=keyboard,
    )
    return True
