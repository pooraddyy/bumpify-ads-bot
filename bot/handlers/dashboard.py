from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit
from bot.config import WEB_APP_URL

async def build_dashboard_content(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    accounts = await db.get_accounts(user_id)
    ad_data = await db.get_ad_message_data(user_id)
    running = await db.is_ads_running(user_id)
    interval = await db.get_interval(user_id)
    auto_reply = await db.is_auto_reply_enabled(user_id)

    ad_status = "Set ✓" if ad_data else "Not Set"
    running_status = "🟢 Running" if running else "⏸ Paused"
    ar_label = "ON" if auto_reply else "OFF"
    mins, secs = divmod(interval, 60)
    interval_label = f"{mins}m {secs}s" if mins else f"{secs}s"

    text = (
        "<b>Bumpify Dashboard</b>\n\n"
        "<blockquote>"
        f"Accounts: <b>{len(accounts)}</b>\n"
        f"Ad Message: <b>{ad_status}</b>\n"
        f"Broadcast: <b>From Saved Messages</b>\n"
        f"Interval: <b>{interval_label}</b>\n"
        f"Status: <b>{running_status}</b>\n"
        f"Auto Reply: <b>{ar_label}</b>"
        "</blockquote>"
    )

    add_acc_btn = (
        InlineKeyboardButton("Add Account", web_app=WebAppInfo(url=WEB_APP_URL), api_kwargs={"style": "primary"})
        if WEB_APP_URL
        else InlineKeyboardButton("Add Account", callback_data="add_account", api_kwargs={"style": "primary"})
    )

    ad_row = [InlineKeyboardButton("Set Ad Message", callback_data="set_ad", api_kwargs={"style": "primary"})]
    if ad_data:
        ad_row.append(InlineKeyboardButton("Remove Ad", callback_data="remove_ad", api_kwargs={"style": "primary"}))

    keyboard = InlineKeyboardMarkup([
        [add_acc_btn, InlineKeyboardButton("My Accounts", callback_data="my_accounts", api_kwargs={"style": "primary"})],
        ad_row,
        [InlineKeyboardButton("Set Interval", callback_data="set_interval", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Analytics", callback_data="analytics", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Start Ads", callback_data="start_ads", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Stop Ads", callback_data="stop_ads", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Auto Reply", callback_data="auto_reply", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Leave Groups", callback_data="leave_groups", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Home", callback_data="home", api_kwargs={"style": "danger"})],
    ])
    return text, keyboard

async def dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    text, keyboard = await build_dashboard_content(user_id)
    if query:
        await safe_edit(query, text, reply_markup=keyboard, parse_mode="HTML", context=context)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
