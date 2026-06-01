from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit
from bot.utils.leave_groups import start_leave_groups, stop_leave_groups, is_leave_running

async def leave_groups_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Leave Groups</b>\n\n"
            "<blockquote>No accounts connected. Add an account first.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    if len(accounts) == 1:
        acc = accounts[0]
        running = is_leave_running(user_id)
        status = "🟢 Currently leaving groups..." if running else "⏸ Idle"
        text = (
            "<b>Leave Groups</b>\n\n"
            "<blockquote>"
            f"Account: <b>{acc['name']}</b>\n"
            f"<code>{acc['phone']}</code>\n\n"
            f"Status: {status}"
            "</blockquote>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Leave All Groups", callback_data="start_leave_all", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("Stop Leaving", callback_data="stop_leave", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
        ])
    else:
        text = (
            "<b>Leave Groups</b>\n\n"
            "<blockquote>Select an account to leave its groups, or use <b>From All</b> to leave from every account.</blockquote>"
        )
        buttons = []
        for acc in accounts:
            buttons.append([InlineKeyboardButton(
                f"{acc['name']} ({acc['phone']})",
                callback_data=f"leave_account_{acc['phone']}",
                api_kwargs={"style": "primary"},
            )])
        buttons.append([
            InlineKeyboardButton("From All", callback_data="start_leave_all", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"}),
        ])
        keyboard = InlineKeyboardMarkup(buttons)

    await safe_edit(query, text, reply_markup=keyboard, parse_mode="HTML", context=context)

async def leave_account_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    query = update.callback_query
    user_id = update.effective_user.id
    accounts = await db.get_accounts(user_id)
    acc = next((a for a in accounts if a["phone"] == phone), None)

    if not acc:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Account not found.</b>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    text = (
        "<b>Leave Groups</b>\n\n"
        "<blockquote>"
        f"Account: <b>{acc['name']}</b>\n"
        f"<code>{acc['phone']}</code>\n\n"
        "All groups this account is a member of will be left."
        "</blockquote>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Start Leave All Groups", callback_data=f"start_leave_{phone}", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, text, reply_markup=keyboard, parse_mode="HTML", context=context)

async def start_leave_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    if is_leave_running(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Stop Leaving", callback_data="stop_leave", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Already leaving groups.</b>\n\n"
            "<blockquote>A leave operation is already in progress.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    accounts = await db.get_accounts(user_id)
    if not accounts:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>No accounts connected.</b>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    await start_leave_groups(user_id, phone=None)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Stop Leaving", callback_data="stop_leave", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(
        query,
        f"<b>🚪 Leaving Groups Started</b>\n\n"
        f"<blockquote>Leaving all groups from <b>{len(accounts)}</b> account(s).\n\n"
        "Logs will be sent to your logger bot as groups are left.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )

async def start_leave_phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    query = update.callback_query
    user_id = update.effective_user.id

    if is_leave_running(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Stop Leaving", callback_data="stop_leave", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("Back", callback_data=f"leave_account_{phone}", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Already leaving groups.</b>\n\n"
            "<blockquote>A leave operation is already in progress.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    accounts = await db.get_accounts(user_id)
    acc = next((a for a in accounts if a["phone"] == phone), None)

    if not acc:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Account not found.</b>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    await start_leave_groups(user_id, phone=phone)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Stop Leaving", callback_data="stop_leave", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(
        query,
        f"<b>🚪 Leaving Groups Started</b>\n\n"
        f"<blockquote>Account: <b>{acc['name']}</b>  <code>{phone}</code>\n\n"
        "Leaving all groups. Logs will be sent to your logger bot.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )

async def stop_leave_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    if not is_leave_running(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>No leave operation is currently running.</b>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    await stop_leave_groups(user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back", callback_data="leave_groups", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(
        query,
        "<b>⏹ Leave Groups Stopped.</b>\n\n"
        "<blockquote>The leave operation has been stopped.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )
