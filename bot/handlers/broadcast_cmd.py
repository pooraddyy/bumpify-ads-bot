import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Forbidden, BadRequest
from bot.utils import db
from bot.config import OWNER_IDS

logger = logging.getLogger(__name__)

STATUS_EVERY = 25
SEND_DELAY = 0.05


def status_text(mode: str, total: int, done: int, success: int, blocked: int, deleted: int, failed: int, complete: bool = False) -> str:
    state = "complete" if complete else "in progress"
    body = (
        f"Total     : {total}\n"
        f"Sent      : {success}\n"
        f"Blocked   : {blocked}\n"
        f"Deleted   : {deleted}\n"
        f"Failed    : {failed}"
    )
    if not complete:
        body += f"\nRemaining : {total - done}"
    return f"<b>{mode} {state}</b>\n\n<blockquote>{body}</blockquote>"


async def run_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, pin: bool):
    user_id = update.effective_user.id

    if not OWNER_IDS or user_id not in OWNER_IDS:
        return

    msg = update.message
    if not msg or not msg.reply_to_message:
        notice = await msg.reply_text(
            "<b>Usage:</b> Reply to any message with this command to broadcast it.",
            parse_mode="HTML",
        )
        try:
            await msg.delete()
        except Exception:
            pass
        await asyncio.sleep(5)
        try:
            await notice.delete()
        except Exception:
            pass
        return

    src = msg.reply_to_message

    try:
        await msg.delete()
    except Exception:
        pass

    users = await db.get_all_users()
    total = len(users)
    mode = "Pinned Broadcast" if pin else "Broadcast"

    if not total:
        await context.bot.send_message(
            chat_id=user_id,
            text="<b>No users found in the database.</b>",
            parse_mode="HTML",
        )
        return

    status_msg = await context.bot.send_message(
        chat_id=user_id,
        text=status_text(mode, total, 0, 0, 0, 0, 0),
        parse_mode="HTML",
    )

    success = 0
    blocked = 0
    deleted = 0
    failed = 0

    for idx, user in enumerate(users):
        uid = user.get("user_id")
        if not uid:
            continue

        try:
            sent = await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=src.chat_id,
                message_id=src.message_id,
            )
            if pin:
                try:
                    await context.bot.pin_chat_message(
                        chat_id=uid,
                        message_id=sent.message_id,
                        disable_notification=True,
                    )
                except Exception:
                    pass
            success += 1

        except Forbidden as e:
            err = str(e).lower()
            if "deactivated" in err or "deleted" in err:
                deleted += 1
            else:
                blocked += 1

        except BadRequest as e:
            err = str(e).lower()
            if "chat not found" in err or "not found" in err:
                deleted += 1
            else:
                failed += 1

        except Exception as e:
            logger.warning("broadcast send failed [uid=%d]: %s", uid, e)
            failed += 1

        await asyncio.sleep(SEND_DELAY)

        done = idx + 1
        if done % STATUS_EVERY == 0:
            try:
                await status_msg.edit_text(
                    status_text(mode, total, done, success, blocked, deleted, failed),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    try:
        await status_msg.edit_text(
            status_text(mode, total, total, success, blocked, deleted, failed, complete=True),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_broadcast(update, context, pin=False)


async def pbroadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_broadcast(update, context, pin=True)
