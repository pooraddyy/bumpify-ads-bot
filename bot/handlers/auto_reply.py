from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit
from bot.config import AUTO_REPLY_TEXT


async def auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    enabled = await db.is_auto_reply_enabled(user_id)
    text = await db.get_auto_reply_text(user_id) or AUTO_REPLY_TEXT
    preview = text[:120] + "..." if len(text) > 120 else text
    status = "ON" if enabled else "OFF"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'Disable' if enabled else 'Enable'} Auto Reply",
            callback_data="toggle_auto_reply",
            api_kwargs={"style": "primary"},
        )],
        [InlineKeyboardButton("Set Custom Text", callback_data="set_auto_reply_text", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Back to Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})],
    ])
    await safe_edit(
        query,
        f"<b>Auto Reply — {status}</b>\n\n"
        f"Current text:\n<i>{preview}</i>\n\n"
        "When enabled, any private message to your added accounts will receive this auto-reply.",
        reply_markup=keyboard,
        parse_mode="HTML",
        context=context,
    )


async def toggle_auto_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    current = await db.is_auto_reply_enabled(user_id)
    new_state = not current
    await db.set_auto_reply_enabled(user_id, new_state)

    from bot.utils.auto_reply_manager import start_auto_reply, stop_auto_reply
    if new_state:
        await start_auto_reply(user_id)
    else:
        await stop_auto_reply(user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Auto Reply Settings", callback_data="auto_reply", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Back to Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})],
    ])
    await safe_edit(
        query,
        f"<b>Auto Reply {'enabled' if new_state else 'disabled'}.</b>\n\n"
        + ("Your added accounts will now auto-reply to private messages." if new_state
           else "Auto-reply has been turned off."),
        reply_markup=keyboard,
        parse_mode="HTML",
        context=context,
    )


async def set_auto_reply_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.set_waiting_for_auto_reply(user_id, True)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="auto_reply", api_kwargs={"style": "danger"})]])
    await safe_edit(
        query,
        "<b>Set Auto Reply Text</b>\n\n"
        "Send me the text you want your accounts to auto-reply with when someone messages them.\n\n"
        "Plain text only — no formatting.",
        reply_markup=keyboard,
        parse_mode="HTML",
        context=context,
    )


async def handle_auto_reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not await db.is_waiting_for_auto_reply(user_id):
        return False
    await db.set_waiting_for_auto_reply(user_id, False)
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Please send a valid text message.")
        return True
    await db.set_auto_reply_text(user_id, text)
    try:
        await update.message.delete()
    except Exception:
        pass
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Auto Reply Settings", callback_data="auto_reply", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})],
    ])
    await update.message.reply_text(
        "<b>Auto reply text updated.</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return True
