import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.utils.helpers import safe_edit
from bot.config import START_CAPTION, LOGGER_BOT_USERNAME, WEB_APP_URL

logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    logger.info("CALLBACK: %s from %s", data, update.effective_user.id)

    try:
        await query.answer()
    except Exception as e:
        logger.debug("query.answer: %s", e)

    try:
        if data == "dashboard":
            from bot.handlers.dashboard import dashboard_handler
            await dashboard_handler(update, context)

        elif data == "my_accounts":
            from bot.handlers.accounts import my_accounts_handler
            await my_accounts_handler(update, context)

        elif data == "delete_account":
            from bot.handlers.accounts import delete_account_handler
            await delete_account_handler(update, context)

        elif data.startswith("del_acc_"):
            from bot.handlers.accounts import confirm_delete_handler
            await confirm_delete_handler(update, context, data[len("del_acc_"):])

        elif data == "analytics":
            from bot.handlers.accounts import analytics_handler
            await analytics_handler(update, context)

        elif data == "set_ad":
            from bot.handlers.ads import set_ad_handler
            await set_ad_handler(update, context)

        elif data == "remove_ad":
            from bot.handlers.ads import remove_ad_handler
            await remove_ad_handler(update, context)

        elif data == "start_ads":
            from bot.handlers.ads import start_ads_handler
            await start_ads_handler(update, context)

        elif data == "stop_ads":
            from bot.handlers.ads import stop_ads_handler
            await stop_ads_handler(update, context)

        elif data == "set_interval":
            from bot.handlers.interval import set_interval_handler
            await set_interval_handler(update, context)

        elif data.startswith("interval_"):
            val = data[len("interval_"):]
            if val == "custom":
                from bot.handlers.interval import interval_custom_handler
                await interval_custom_handler(update, context)
            else:
                from bot.handlers.interval import interval_preset_handler
                await interval_preset_handler(update, context, int(val))

        elif data == "faq":
            from bot.handlers.faq import faq_handler
            await faq_handler(update, context)

        elif data == "howto":
            from bot.handlers.faq import howto_handler
            await howto_handler(update, context)

        elif data == "home":
            await home_handler(update, context)

        elif data == "add_account":
            await add_account_fallback(update, context)

        elif data == "auto_reply":
            from bot.handlers.auto_reply import auto_reply_handler
            await auto_reply_handler(update, context)

        elif data == "toggle_auto_reply":
            from bot.handlers.auto_reply import toggle_auto_reply_handler
            await toggle_auto_reply_handler(update, context)

        elif data == "set_auto_reply_text":
            from bot.handlers.auto_reply import set_auto_reply_text_handler
            await set_auto_reply_text_handler(update, context)

        elif data == "leave_groups":
            from bot.handlers.leave_groups import leave_groups_menu_handler
            await leave_groups_menu_handler(update, context)

        elif data.startswith("leave_account_"):
            phone = data[len("leave_account_"):]
            from bot.handlers.leave_groups import leave_account_menu_handler
            await leave_account_menu_handler(update, context, phone)

        elif data == "start_leave_all":
            from bot.handlers.leave_groups import start_leave_all_handler
            await start_leave_all_handler(update, context)

        elif data.startswith("start_leave_"):
            phone = data[len("start_leave_"):]
            from bot.handlers.leave_groups import start_leave_phone_handler
            await start_leave_phone_handler(update, context, phone)

        elif data == "stop_leave":
            from bot.handlers.leave_groups import stop_leave_handler
            await stop_leave_handler(update, context)

        else:
            logger.warning("Unhandled callback: %s", data)

    except Exception as e:
        logger.error("callback_handler error [%s]: %s", data, e, exc_info=True)
        try:
            await safe_edit(
                query,
                "<b>Something went wrong.</b>\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Home", callback_data="home", api_kwargs={"style": "danger"})]]),
                parse_mode="HTML",
                context=context,
            )
        except Exception:
            pass

async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
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
    await safe_edit(query, caption, reply_markup=keyboard, parse_mode="HTML", context=context)

async def add_account_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if WEB_APP_URL:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Web Panel", web_app=WebAppInfo(url=WEB_APP_URL), api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Add Account</b>\n\n"
            "<blockquote>Use the web panel to log in with your phone number and OTP.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})]])
        await safe_edit(
            query,
            "<b>Add Account</b>\n\n"
            "<blockquote>Set <code>WEB_APP_URL</code> in your environment to enable the web panel.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
