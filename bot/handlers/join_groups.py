import asyncio
import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils import db
from bot.utils.helpers import safe_edit
from bot.utils.session_manager import get_pyrogram_client
from bot.utils.broadcaster import send_logs

logger = logging.getLogger(__name__)

join_tasks: dict[int, asyncio.Task] = {}
join_stop_flags: dict[int, bool] = {}

def is_join_running(owner_id: int) -> bool:
    task = join_tasks.get(owner_id)
    return task is not None and not task.done()

async def stop_join_groups(owner_id: int):
    join_stop_flags[owner_id] = True
    task = join_tasks.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    join_stop_flags.pop(owner_id, None)

def extract_group_link(text: str) -> str:
    text = text.strip()
    if text.startswith("https://t.me/") or text.startswith("http://t.me/"):
        return text
    if text.startswith("t.me/"):
        return "https://" + text
    if re.match(r'^\+?[a-zA-Z0-9_]{5,}$', text):
        return f"https://t.me/{text}"
    return ""

def get_join_param(link: str) -> str:
    link = link.strip()
    if link.startswith("https://t.me/"):
        return link[len("https://t.me/"):]
    if link.startswith("http://t.me/"):
        return link[len("http://t.me/"):]
    if link.startswith("t.me/"):
        return link[len("t.me/"):]
    return link

async def join_groups_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    accounts = await db.get_accounts(user_id)

    if not accounts:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(
            query,
            "<b>Join Groups</b>\n\n"
            "<blockquote>No accounts connected. Add an account first.</blockquote>",
            reply_markup=keyboard, parse_mode="HTML", context=context,
        )
        return

    text = (
        "<b>Join Groups</b>\n\n"
        "<blockquote>"
        f"Accounts: <b>{len(accounts)}</b>\n"
        "Load groups from file, edit list, or join all."
        "</blockquote>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Load Groups", callback_data="load_groups", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Edit List", callback_data="edit_groups", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Join All", callback_data="join_all", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Stop", callback_data="stop_join", api_kwargs={"style": "danger"})],
        [InlineKeyboardButton("Back", callback_data="dashboard", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, text, reply_markup=keyboard, parse_mode="HTML", context=context)

async def load_groups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    groups = await db.get_groups()
    text = (
        "<b>Load Groups</b>\n\n"
        f"<blockquote>Total groups loaded: <b>{len(groups)}</b></blockquote>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join All", callback_data="join_all", api_kwargs={"style": "primary"}),
         InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, text, reply_markup=keyboard, parse_mode="HTML", context=context)

async def edit_groups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    groups = await db.get_groups()
    preview = "\n".join(groups[:10])
    more = f"\n... and {len(groups) - 10} more" if len(groups) > 10 else ""
    text = (
        "<b>Edit Group List</b>\n\n"
        "<blockquote>"
        f"Current count: <b>{len(groups)}</b>\n\n"
        f"<pre>{preview}{more}</pre>"
        "</blockquote>"
        "Send the new list of links (one per line) to replace the current list."
    )
    await safe_edit(query, text, parse_mode="HTML", context=context)
    context.user_data["editing_groups"] = True

async def join_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    logger.info("join_all requested by %d", user_id)
    accounts = await db.get_accounts(user_id)

    if not accounts:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(query, "<b>No accounts connected.</b>", reply_markup=keyboard, parse_mode="HTML", context=context)
        return

    if is_join_running(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Stop", callback_data="stop_join", api_kwargs={"style": "danger"})],
            [InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(query, "<b>Join already running...</b>", reply_markup=keyboard, parse_mode="HTML", context=context)
        return

    groups = await db.get_groups()
    if not groups:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Load Groups", callback_data="load_groups", api_kwargs={"style": "primary"}),
             InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(query, "<b>No groups loaded. Load groups first.</b>", reply_markup=keyboard, parse_mode="HTML", context=context)
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Stop", callback_data="stop_join", api_kwargs={"style": "danger"})],
        [InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, "<b>Joining groups...</b> Started.", reply_markup=keyboard, parse_mode="HTML", context=context)

    async def run():
        try:
            logger.info("join_all started user=%d accounts=%d groups=%d", user_id, len(accounts), len(groups))
            for acc in accounts:
                if join_stop_flags.get(user_id, False):
                    break
                try:
                    logger.info("join_all getting client for %s", acc["phone"])
                    client = await get_pyrogram_client(acc["session"])
                    async with client:
                        logger.info("join_all client started for %s", acc["phone"])
                        joined = 0
                        failed = 0
                        for link in groups:
                            if join_stop_flags.get(user_id, False):
                                break
                            clean_link = extract_group_link(link)
                            if not clean_link:
                                continue
                            join_param = get_join_param(clean_link)
                            try:
                                logger.info("join_all trying %s with %s", join_param, acc["phone"])
                                await client.join_chat(join_param)
                                joined += 1
                                await db.add_join_log(user_id, acc["phone"], clean_link, True)
                                await send_logs(
                                    user_id,
                                    f"<b>Joined</b>\nAccount: <code>{acc['phone']}</code>\nGroup: {clean_link}",
                                )
                                await asyncio.sleep(1)
                            except Exception as e:
                                failed += 1
                                err = str(e)[:80]
                                logger.warning("join_all failed %s with %s: %s", join_param, acc["phone"], err)
                                await db.add_join_log(user_id, acc["phone"], clean_link, False, err)
                                await send_logs(
                                    user_id,
                                    f"<b>Join Failed</b>\nAccount: <code>{acc['phone']}</code>\nGroup: {clean_link}\nError: {err}",
                                )
                                await asyncio.sleep(1)
                        await send_logs(
                            user_id,
                            f"<b>Join Groups — {acc['name']}</b>\n"
                            f"<code>{acc['phone']}</code>\n\n"
                            f"Joined: <b>{joined}</b>\n"
                            f"Failed: <b>{failed}</b>",
                        )
                except Exception as e:
                    logger.error("join_all account error [%s]: %s", acc["phone"], e, exc_info=True)
                    await send_logs(user_id, f"<b>Join Error</b>\nAccount: <code>{acc['phone']}</code>\nError: {str(e)[:100]}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("join_all error [%s]: %s", user_id, e, exc_info=True)
        finally:
            join_tasks.pop(user_id, None)
            join_stop_flags.pop(user_id, None)

    task = asyncio.create_task(run())
    join_tasks[user_id] = task

async def stop_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if is_join_running(user_id):
        await stop_join_groups(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(query, "<b>Join stopped.</b>", reply_markup=keyboard, parse_mode="HTML", context=context)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data="join_groups", api_kwargs={"style": "danger"})],
        ])
        await safe_edit(query, "<b>No active join process.</b>", reply_markup=keyboard, parse_mode="HTML", context=context)

async def join_groups_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if context.user_data.get("editing_groups"):
        text = update.message.text or ""
        links = [extract_group_link(line) for line in text.splitlines() if extract_group_link(line)]
        if links:
            with open("groups.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(links) + "\n")
            await update.message.reply_text(f"<b>Updated.</b> {len(links)} groups saved.", parse_mode="HTML")
        else:
            await update.message.reply_text("<b>No valid links found.</b> Send one link per line.", parse_mode="HTML")
        context.user_data["editing_groups"] = False
        return True
    return False
