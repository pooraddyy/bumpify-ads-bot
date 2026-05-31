import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit
from bot.utils.broadcaster import start_broadcast, stop_broadcast, send_ad_via_pyrogram
from bot.utils.session_manager import get_pyrogram_client
from bot.config import WEB_APP_URL, LOGGER_BOT_TOKEN, LOGGER_BOT_USERNAME

logger = logging.getLogger(__name__)


async def save_ad_to_saved_messages(owner_id: int, ad_data: dict):
    accounts = await db.get_accounts(owner_id)
    if not accounts:
        return

    sem = asyncio.Semaphore(10)

    async def save_one(acc: dict):
        async with sem:
            try:
                client = await get_pyrogram_client(acc["session"])
                async with client:
                    await send_ad_via_pyrogram(client, "me", ad_data)
            except Exception as e:
                logger.warning("save_to_saved_messages failed [%s]: %s", acc["phone"], e)

    await asyncio.gather(*[save_one(acc) for acc in accounts], return_exceptions=True)


async def set_ad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.set_waiting_for_ad(user_id, True)
    await db.set_prompt_message(user_id, query.message.chat_id, query.message.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="dashboard", api_kwargs={"style": "danger"})]])
    await safe_edit(
        query,
        "<b>Set Ad Message</b>\n\n"
        "<blockquote>Send any message — text, photo, video, document, audio, sticker.\n"
        "Full formatting is preserved: bold, italic, code, blockquote, strikethrough.\n\n"
        "Your message will be automatically saved to each account's Saved Messages and broadcast from there.</blockquote>\n\n"
        "Send your message now. It will be deleted after saving.",
        reply_markup=keyboard,
        parse_mode="HTML",
        context=context,
    )


async def handle_ad_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not await db.is_waiting_for_ad(user_id):
        return False

    await db.set_waiting_for_ad(user_id, False)
    msg = update.message

    ad_data = None
    if msg.photo:
        ad_data = {"type": "photo", "file_id": msg.photo[-1].file_id, "file_unique_id": msg.photo[-1].file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.video:
        ad_data = {"type": "video", "file_id": msg.video.file_id, "file_unique_id": msg.video.file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.document:
        ad_data = {"type": "document", "file_id": msg.document.file_id, "file_unique_id": msg.document.file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.audio:
        ad_data = {"type": "audio", "file_id": msg.audio.file_id, "file_unique_id": msg.audio.file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.animation:
        ad_data = {"type": "animation", "file_id": msg.animation.file_id, "file_unique_id": msg.animation.file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.sticker:
        ad_data = {"type": "sticker", "file_id": msg.sticker.file_id, "file_unique_id": msg.sticker.file_unique_id}
    elif msg.voice:
        ad_data = {"type": "voice", "file_id": msg.voice.file_id, "file_unique_id": msg.voice.file_unique_id, "caption": msg.caption_html or msg.caption or ""}
    elif msg.video_note:
        ad_data = {"type": "video_note", "file_id": msg.video_note.file_id, "file_unique_id": msg.video_note.file_unique_id}
    elif msg.text:
        ad_data = {"type": "text", "text": msg.text_html or msg.text or ""}
    else:
        await db.set_waiting_for_ad(user_id, True)
        await update.message.reply_text("Unsupported message type. Please try again.")
        return True

    await db.set_ad_message_data(user_id, {"set": True})
    asyncio.create_task(save_ad_to_saved_messages(user_id, ad_data))

    try:
        await msg.delete()
    except Exception:
        pass

    prompt = await db.get_prompt_message(user_id)
    if prompt:
        chat_id, msg_id = prompt
        text, keyboard = await build_dashboard_content_local(user_id)
        for method in ("edit_message_caption", "edit_message_text"):
            try:
                fn = getattr(context.bot, method)
                kwargs = {"chat_id": chat_id, "message_id": msg_id, "reply_markup": keyboard, "parse_mode": "HTML"}
                if method == "edit_message_caption":
                    kwargs["caption"] = text
                else:
                    kwargs["text"] = text
                await fn(**kwargs)
                return True
            except Exception:
                continue

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await context.bot.send_message(
        chat_id=msg.chat_id,
        text="<b>✅ Ad message saved.</b>\n\n<blockquote>Copying to all account Saved Messages in background...</blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return True


async def build_dashboard_content_local(user_id: int):
    from bot.handlers.dashboard import build_dashboard_content
    return await build_dashboard_content(user_id)


async def remove_ad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await db.clear_ad_message_data(user_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await safe_edit(
        query,
        "<b>Ad message removed.</b>\n\n"
        "<blockquote>Your ad has been cleared. Set a new one from the dashboard.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def start_ads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    ad_data = await db.get_ad_message_data(user_id)
    if not ad_data:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Set Ad Message", callback_data="set_ad", api_kwargs={"style": "primary"})]])
        await safe_edit(
            query,
            "<b>No ad message set.</b>\n\n"
            "<blockquote>Set your ad message first. It will be saved to each account's Saved Messages and broadcast from there.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    accounts = await db.get_accounts(user_id)
    if not accounts:
        add_btn = (
            InlineKeyboardButton("Add Account", web_app=WebAppInfo(url=WEB_APP_URL), api_kwargs={"style": "primary"})
            if WEB_APP_URL
            else InlineKeyboardButton("Add Account", callback_data="add_account", api_kwargs={"style": "primary"})
        )
        await safe_edit(
            query,
            "<b>No accounts connected.</b>\n\n"
            "<blockquote>Add at least one Telegram account before starting ads.</blockquote>",
            reply_markup=InlineKeyboardMarkup([[add_btn]]), parse_mode="HTML", context=context,
        )
        return

    if LOGGER_BOT_TOKEN and not await db.is_logger_started(user_id):
        note = f" @{LOGGER_BOT_USERNAME}" if LOGGER_BOT_USERNAME else ""
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
        await safe_edit(
            query,
            f"<b>Start your Logger Bot first!</b>\n\n"
            f"<blockquote>Open your logger bot{note} and send /start before starting ads.\n\n"
            "This ensures you receive broadcast logs and reports after each cycle.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    if await db.is_ads_running(user_id):
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
        await safe_edit(
            query,
            "<b>Ads are already running.</b>\n\nUse Stop Ads to stop the current broadcast.",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    await start_broadcast(user_id)
    interval = await db.get_interval(user_id)
    mins, secs = divmod(interval, 60)
    interval_label = f"{mins}m {secs}s" if mins else f"{secs}s"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])
    await safe_edit(
        query,
        f"<b>🚀 Ads Started</b>\n\n"
        f"<blockquote>Broadcasting from Saved Messages via <b>{len(accounts)}</b> account(s).\n"
        f"Interval: <b>{interval_label}</b>\n\n"
        "Logs will arrive in your logger bot after each cycle.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )


async def stop_ads_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="dashboard", api_kwargs={"style": "success"})]])

    if not await db.is_ads_running(user_id):
        await safe_edit(
            query,
            "<b>No ads are currently running.</b>\n\n<blockquote>Start a broadcast first from the dashboard.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    await stop_broadcast(user_id)
    await safe_edit(
        query,
        "<b>Ads Stopped.</b>\n\n<blockquote>Broadcasting has been paused. Start again from the dashboard.</blockquote>",
        reply_markup=keyboard, parse_mode="HTML", context=context,
    )
