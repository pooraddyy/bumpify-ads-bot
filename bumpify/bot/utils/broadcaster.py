"""
broadcaster.py — concurrent ad broadcaster with 10k-account support.

Key design decisions:
- Global semaphore (MAX_CONCURRENT_ACCOUNTS, default 30) limits simultaneous
  Pyrogram sessions so we never flood-connect to Telegram.
- All accounts start concurrently and are throttled by the semaphore; as one
  finishes the next begins immediately — no sequential chunking.
- Per-account group semaphore (3) limits concurrent sends within one account.
- FloodWait is caught, capped at 60 s, and retried once.
- asyncio.CancelledError propagates cleanly so stop_broadcast() works instantly.
"""

import asyncio
import io
import logging
import os
import httpx
from pyrogram import Client
from pyrogram.enums import ParseMode, ChatType
from pyrogram.errors import (
    FloodWait,
    ChatWriteForbidden,
    UserBannedInChannel,
    SessionRevoked,
    AuthKeyUnregistered,
    ChannelPrivate,
    UserNotParticipant,
)
from bot.utils.session_manager import get_pyrogram_client
from bot.utils import db
import telegram
from bot.config import BOT_TOKEN, LOGGER_BOT_TOKEN

logger = logging.getLogger(__name__)

# ── Concurrency knobs ──────────────────────────────────────────────────────────
# How many Pyrogram sessions may be ACTIVE at the same time across all users.
# Raise this on powerful servers; keep ≤50 to stay within Telegram API limits.
MAX_CONCURRENT_ACCOUNTS: int = int(os.getenv("MAX_CONCURRENT_ACCOUNTS", "30"))

# Per-account: how many groups may be targeted simultaneously.
GROUPS_PER_ACCOUNT_CONCURRENCY: int = int(os.getenv("GROUPS_PER_ACCOUNT_CONCURRENCY", "3"))

# Delay (seconds) between successful sends within one account to avoid flood bans.
SEND_DELAY: float = float(os.getenv("SEND_DELAY", "1.5"))

# Semaphores — created lazily so they live on the running event loop.
_global_client_sem: asyncio.Semaphore | None = None
_dl_semaphore: asyncio.Semaphore | None = None

# In-flight broadcast tasks: {owner_id: Task}
active_tasks: dict[int, asyncio.Task] = {}

# Cached logger bot instance
_logger_bot: telegram.Bot | None = None


def _get_global_client_sem() -> asyncio.Semaphore:
    global _global_client_sem
    if _global_client_sem is None:
        _global_client_sem = asyncio.Semaphore(MAX_CONCURRENT_ACCOUNTS)
    return _global_client_sem


def _get_dl_sem() -> asyncio.Semaphore:
    global _dl_semaphore
    if _dl_semaphore is None:
        _dl_semaphore = asyncio.Semaphore(8)
    return _dl_semaphore


def get_logger_bot() -> telegram.Bot | None:
    global _logger_bot
    if not LOGGER_BOT_TOKEN:
        return None
    if _logger_bot is None:
        _logger_bot = telegram.Bot(token=LOGGER_BOT_TOKEN)
    return _logger_bot


# ── Logging helper ─────────────────────────────────────────────────────────────

async def send_logs(owner_id: int, text: str) -> None:
    bot = get_logger_bot()
    if not bot:
        return
    try:
        await bot.send_message(chat_id=owner_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning("send_logs failed: %s", e)


# ── File download ──────────────────────────────────────────────────────────────

async def download_file(file_id: str) -> bytes | None:
    async with _get_dl_sem():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                    params={"file_id": file_id},
                )
                path = r.json()["result"]["file_path"]
                r2 = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}")
                return r2.content
        except Exception as e:
            logger.warning("download_file failed [%s]: %s", file_id, e)
            return None


# ── Ad sender (Pyrogram) ───────────────────────────────────────────────────────

async def send_ad_via_pyrogram(client: Client, chat_id, ad_data: dict) -> None:
    msg_type = ad_data.get("type")
    caption = ad_data.get("caption", "") or ""

    if msg_type == "text":
        text = ad_data.get("text", "") or ""
        await client.send_message(chat_id, text, parse_mode=ParseMode.HTML)

    elif msg_type == "forward":
        msgs = [m async for m in client.get_chat_history("me", limit=1)]
        if msgs and msgs[0].id:
            await client.forward_messages(chat_id, "me", msgs[0].id)
        else:
            raise ValueError("No message in Saved Messages to forward")

    elif msg_type == "photo":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download photo")
        await client.send_photo(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "video":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download video")
        await client.send_video(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "document":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download document")
        await client.send_document(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "audio":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download audio")
        await client.send_audio(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "animation":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download animation")
        await client.send_animation(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "sticker":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download sticker")
        await client.send_sticker(chat_id, io.BytesIO(data))

    elif msg_type == "voice":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download voice")
        await client.send_voice(chat_id, io.BytesIO(data), caption=caption, parse_mode=ParseMode.HTML)

    elif msg_type == "video_note":
        data = await download_file(ad_data["file_id"])
        if not data:
            raise ValueError("Could not download video note")
        await client.send_video_note(chat_id, io.BytesIO(data))

    else:
        raise ValueError(f"Unsupported ad message type: {msg_type!r}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def group_link(group) -> str:
    username = getattr(group, "username", None)
    gid = str(group.id)
    if username:
        return f"https://t.me/{username}"
    if gid.startswith("-100"):
        return f"https://t.me/c/{gid[4:]}"
    return ""


# ── Single-account broadcaster ─────────────────────────────────────────────────

async def process_account(owner_id: int, acc_num: int, acc: dict) -> dict:
    """
    Runs inside the global client semaphore — at most MAX_CONCURRENT_ACCOUNTS
    of these execute concurrently across ALL users.
    """
    report: dict = {
        "num": acc_num,
        "phone": acc["phone"],
        "name": acc.get("name", acc["phone"]),
        "success": 0,
        "failed": 0,
        "groups": [],
        "error": None,
    }

    async with _get_global_client_sem():
        try:
            client = await get_pyrogram_client(acc["session"])
            async with client:
                # Fetch latest Saved Message ID
                msgs = [m async for m in client.get_chat_history("me", limit=1)]
                if not msgs or not msgs[0].id:
                    report["error"] = "No message in Saved Messages"
                    await send_logs(
                        owner_id,
                        f"<b>Account #{acc_num} — {acc.get('name', acc['phone'])}</b>\n"
                        f"<code>{acc['phone']}</code>\n\n"
                        "No message in Saved Messages. Set your ad first.",
                    )
                    return report

                saved_msg_id = msgs[0].id

                # Collect all group dialogs
                groups = []
                async for dialog in client.get_dialogs(limit=0):
                    if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                        groups.append(dialog.chat)

                logger.info("Account #%d (%s): %d groups", acc_num, acc["phone"], len(groups))

                # Per-account concurrency semaphore
                group_sem = asyncio.Semaphore(GROUPS_PER_ACCOUNT_CONCURRENCY)

                async def send_to_group(group):
                    gid = group.id
                    gtitle = group.title or str(gid)
                    gusername = getattr(group, "username", None) or ""
                    glink = group_link(group)

                    async with group_sem:
                        # Bail early if broadcast was stopped
                        if not await db.is_ads_running(owner_id):
                            return

                        async def _do_send():
                            await client.forward_messages(gid, "me", saved_msg_id)

                        try:
                            await _do_send()
                            await db.log_broadcast(owner_id, acc["phone"], acc_num, gid, gtitle, gusername, True)
                            report["success"] += 1
                            report["groups"].append({
                                "title": gtitle, "username": gusername,
                                "link": glink, "id": gid, "ok": True,
                            })
                            await asyncio.sleep(SEND_DELAY)

                        except FloodWait as e:
                            wait = min(e.value, 60)
                            logger.info("FloodWait %ds — acc #%d group '%s'", wait, acc_num, gtitle)
                            await asyncio.sleep(wait)
                            try:
                                await _do_send()
                                await db.log_broadcast(owner_id, acc["phone"], acc_num, gid, gtitle, gusername, True)
                                report["success"] += 1
                                report["groups"].append({
                                    "title": gtitle, "username": gusername,
                                    "link": glink, "id": gid, "ok": True,
                                })
                            except Exception as ex2:
                                await db.log_broadcast(owner_id, acc["phone"], acc_num, gid, gtitle, gusername, False, str(ex2)[:120])
                                report["failed"] += 1
                                report["groups"].append({
                                    "title": gtitle, "username": gusername,
                                    "link": glink, "id": gid, "ok": False, "err": str(ex2)[:60],
                                })

                        except (ChatWriteForbidden, UserBannedInChannel, ChannelPrivate, UserNotParticipant):
                            err = "No write permission / not a member"
                            await db.log_broadcast(owner_id, acc["phone"], acc_num, gid, gtitle, gusername, False, err)
                            report["failed"] += 1
                            report["groups"].append({
                                "title": gtitle, "username": gusername,
                                "link": glink, "id": gid, "ok": False, "err": err,
                            })

                        except asyncio.CancelledError:
                            raise  # propagate cancellation

                        except Exception as ex:
                            err = str(ex)[:120]
                            await db.log_broadcast(owner_id, acc["phone"], acc_num, gid, gtitle, gusername, False, err)
                            report["failed"] += 1
                            report["groups"].append({
                                "title": gtitle, "username": gusername,
                                "link": glink, "id": gid, "ok": False, "err": str(ex)[:60],
                            })

                # Fan out to all groups; return_exceptions so one bad group
                # never cancels the rest.
                await asyncio.gather(
                    *[send_to_group(g) for g in groups],
                    return_exceptions=True,
                )

        except asyncio.CancelledError:
            raise

        except (SessionRevoked, AuthKeyUnregistered):
            report["error"] = "Session expired — account removed"
            await db.remove_account(owner_id, acc["phone"])
            await send_logs(
                owner_id,
                f"<b>Account #{acc_num} Session Expired</b>\n"
                f"Phone: <code>{acc['phone']}</code>\n"
                "Automatically removed. Please re-add it.",
            )

        except Exception as e:
            report["error"] = str(e)[:200]
            logger.error("process_account error [%s]: %s", acc["phone"], e)
            await send_logs(
                owner_id,
                f"<b>Account #{acc_num} Error</b>\n"
                f"Phone: <code>{acc['phone']}</code>\n"
                f"Error: {str(e)[:200]}",
            )

    return report


# ── Report formatter ───────────────────────────────────────────────────────────

def build_report_text(report: dict, time_str: str) -> str:
    if report.get("error") and not report["groups"]:
        return ""

    lines = [
        f"<b>Account #{report['num']} — {report['name']}</b>",
        f"<code>{report['phone']}</code>",
        "",
        f"Sent: <b>{report['success']}</b>  |  Failed: <b>{report['failed']}</b>  |  Total: <b>{len(report['groups'])}</b>",
        "",
    ]

    shown = 0
    for g in report["groups"]:
        if shown >= 50:
            lines.append(f"<i>... and {len(report['groups']) - shown} more groups</i>")
            break
        mark = "+" if g["ok"] else "-"
        name = g["title"][:35]
        uname = f"@{g['username']}" if g["username"] else ""
        gid_str = str(g["id"])
        if g["link"]:
            lines.append(f"{mark} <a href='{g['link']}'>{name}</a> {uname} <code>{gid_str}</code>")
        else:
            lines.append(f"{mark} {name} {uname} <code>{gid_str}</code>")
        if not g["ok"] and g.get("err"):
            lines.append(f"  <i>{g['err']}</i>")
        shown += 1

    lines.append(f"\nNext cycle: <code>{time_str}</code>")
    msg = "\n".join(lines)
    if len(msg) > 4096:
        msg = msg[:4000] + "\n<i>... truncated</i>"
    return msg


# ── Per-user broadcast loop ────────────────────────────────────────────────────

async def broadcast_for_user(owner_id: int) -> None:
    accounts = await db.get_accounts(owner_id)
    if not accounts:
        return

    interval = await db.get_interval(owner_id)
    mins, secs = divmod(interval, 60)
    time_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    logger.info(
        "broadcast_for_user owner=%d accounts=%d max_concurrent=%d",
        owner_id, len(accounts), MAX_CONCURRENT_ACCOUNTS,
    )

    # Launch ALL accounts at once — the global semaphore throttles actual connections.
    # This is far faster than sequential chunking for large account pools.
    tasks = [
        asyncio.ensure_future(process_account(owner_id, i + 1, acc))
        for i, acc in enumerate(accounts)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, (Exception, BaseException)):
            if not isinstance(result, asyncio.CancelledError):
                logger.error("broadcast_for_user exception: %s", result)
            continue
        text = build_report_text(result, time_str)
        if text:
            await send_logs(owner_id, text)


# ── Public API ─────────────────────────────────────────────────────────────────

async def start_broadcast(owner_id: int) -> None:
    await db.set_ads_running(owner_id, True)

    async def run():
        try:
            while await db.is_ads_running(owner_id):
                interval = await db.get_interval(owner_id)
                await broadcast_for_user(owner_id)
                if await db.is_ads_running(owner_id):
                    await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("start_broadcast loop error [owner=%d]: %s", owner_id, e)
        finally:
            active_tasks.pop(owner_id, None)

    task = asyncio.ensure_future(run())
    active_tasks[owner_id] = task


async def stop_broadcast(owner_id: int) -> None:
    await db.set_ads_running(owner_id, False)
    task = active_tasks.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
