from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit


async def my_accounts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    accounts = await db.get_accounts(user_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})]])

    if not accounts:
        await safe_edit(
            query,
            "<b>My Accounts</b>\n\n"
            "<blockquote>No accounts connected yet.\nUse Add Account to get started.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    lines = ["<b>My Accounts</b>\n"]
    for i, acc in enumerate(accounts, 1):
        uname = f"@{acc['username']}" if acc.get("username") else ""
        uid = f" · ID: <code>{acc['tg_user_id']}</code>" if acc.get("tg_user_id") else ""
        status = "🟢" if acc.get("active", True) else "⚫"
        lines.append(f"{status} <code>{i}.</code> <b>{acc['name']}</b> {uname}{uid}")
        lines.append(f"   <code>{acc['phone']}</code>")
    lines.append(f"\n<blockquote>Total active: <b>{len(accounts)}</b> account(s)</blockquote>")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Remove Account", callback_data="delete_account", api_kwargs={"style": "danger"})],
        [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, "\n".join(lines), reply_markup=keyboard, parse_mode="HTML", context=context)


async def delete_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    accounts = await db.get_all_accounts(user_id)

    if not accounts:
        await safe_edit(
            query,
            "<b>No accounts to remove.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})]]),
            parse_mode="HTML", context=context,
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"{acc['name']} ({acc['phone']})",
            callback_data=f"del_acc_{acc['phone']}",
            api_kwargs={"style": "danger"},
        )]
        for acc in accounts
    ]
    buttons.append([InlineKeyboardButton("Cancel", callback_data="dashboard", api_kwargs={"style": "danger"})])
    await safe_edit(
        query,
        "<b>Remove Account</b>\n\nSelect an account to remove:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML", context=context,
    )


async def confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.remove_account(user_id, phone)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await safe_edit(
        query,
        f"<b>Account removed.</b>\n\n<blockquote><code>{phone}</code> has been disconnected.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    stats = await db.get_broadcast_stats(user_id)
    per_account = await db.get_per_account_stats(user_id)
    accounts = await db.get_accounts(user_id)

    total = stats["total"]
    success = stats["success"]
    failed = stats["failed"]
    rate = round(success / total * 100, 1) if total > 0 else 0

    lines = [
        "<b>📊 Analytics Overview</b>\n",
        "<blockquote>"
        f"Total Broadcasts: <b>{total}</b>\n"
        f"Successful: <b>{success}</b>\n"
        f"Failed: <b>{failed}</b>\n"
        f"Success Rate: <b>{rate}%</b>\n"
        f"Active Accounts: <b>{len(accounts)}</b>"
        "</blockquote>",
    ]

    if per_account:
        lines.append("\n<b>Per Account</b>")
        for p in per_account[:10]:
            acc_rate = round(p["success"] / p["total"] * 100, 1) if p["total"] > 0 else 0
            phone = p["_id"]
            lines.append(
                f"\n<code>{phone}</code>\n"
                f"  Sent: {p['success']} · Failed: {p['failed']} · Rate: {acc_rate}%"
            )

    lines.append(
        "\n\n<i>Full real-time logs are sent to your logger bot after each broadcast cycle.</i>"
    )

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})]])
    await safe_edit(query, "\n".join(lines), reply_markup=keyboard, parse_mode="HTML", context=context)
