import asyncio
import logging
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait, SessionRevoked, AuthKeyUnregistered
from bot.utils.session_manager import get_pyrogram_client
from bot.utils import db
from bot.utils.broadcaster import send_logs

logger = logging.getLogger(__name__)

leave_tasks: dict[int, asyncio.Task] = {}
stop_flags: dict[int, bool] = {}


def is_leave_running(owner_id: int) -> bool:
    task = leave_tasks.get(owner_id)
    return task is not None and not task.done()


async def stop_leave_groups(owner_id: int):
    stop_flags[owner_id] = True
    task = leave_tasks.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    stop_flags.pop(owner_id, None)


def build_group_link(group) -> str:
    username = getattr(group, "username", None)
    gid = str(group.id)
    if username:
        return f"https://t.me/{username}"
    if gid.startswith("-100"):
        return f"https://t.me/c/{gid[4:]}"
    return ""


async def leave_for_account(owner_id: int, acc_num: int, acc: dict) -> dict:
    report = {
        "num": acc_num,
        "phone": acc["phone"],
        "name": acc.get("name", acc["phone"]),
        "left": 0,
        "failed": 0,
        "groups": [],
        "error": None,
        "stopped": False,
    }

    try:
        client = await get_pyrogram_client(acc["session"])
        async with client:
            groups = []
            async for dialog in client.get_dialogs(limit=0):
                if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    groups.append(dialog.chat)

            logger.info("Leave: Account #%d (%s): %d groups found", acc_num, acc["phone"], len(groups))

            for group in groups:
                if stop_flags.get(owner_id, False):
                    report["stopped"] = True
                    break

                gid = group.id
                gtitle = group.title or str(gid)
                gusername = getattr(group, "username", None) or ""
                glink = build_group_link(group)

                try:
                    await client.leave_chat(gid)
                    report["left"] += 1
                    report["groups"].append({
                        "title": gtitle,
                        "username": gusername,
                        "link": glink,
                        "id": gid,
                        "ok": True,
                    })
                    await asyncio.sleep(1)

                except FloodWait as e:
                    wait = min(e.value, 30)
                    logger.info("FloodWait %ds leaving group %s", wait, gtitle)
                    await asyncio.sleep(wait)
                    try:
                        await client.leave_chat(gid)
                        report["left"] += 1
                        report["groups"].append({
                            "title": gtitle,
                            "username": gusername,
                            "link": glink,
                            "id": gid,
                            "ok": True,
                        })
                    except Exception as ex2:
                        report["failed"] += 1
                        report["groups"].append({
                            "title": gtitle,
                            "username": gusername,
                            "link": glink,
                            "id": gid,
                            "ok": False,
                            "err": str(ex2)[:60],
                        })

                except Exception as e:
                    report["failed"] += 1
                    report["groups"].append({
                        "title": gtitle,
                        "username": gusername,
                        "link": glink,
                        "id": gid,
                        "ok": False,
                        "err": str(e)[:60],
                    })

    except (SessionRevoked, AuthKeyUnregistered):
        report["error"] = "Session expired — account removed"
        await db.remove_account(owner_id, acc["phone"])
        await send_logs(
            owner_id,
            f"<b>Account #{acc_num} Session Expired</b>\n"
            f"Phone: <code>{acc['phone']}</code>\n"
            "The account has been automatically removed. Please re-add it.",
        )

    except Exception as e:
        report["error"] = str(e)[:200]
        logger.warning("leave_for_account error [%s]: %s", acc["phone"], e)

    return report


async def send_leave_report(owner_id: int, report: dict):
    if report.get("error") and not report["groups"]:
        await send_logs(
            owner_id,
            f"<b>Leave Groups — Account #{report['num']}</b>\n"
            f"<b>{report['name']}</b>  <code>{report['phone']}</code>\n\n"
            f"Error: {report['error']}",
        )
        return

    status = "Stopped" if report.get("stopped") else "Completed"

    lines = [
        f"<b>Leave Groups — Account #{report['num']}</b>",
        f"<b>{report['name']}</b>  <code>{report['phone']}</code>",
        "",
        f"Left: <b>{report['left']}</b>  |  Failed: <b>{report['failed']}</b>  |  Total: <b>{len(report['groups'])}</b>",
        f"Status: <b>{status}</b>",
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
            lines.append(f"   <i>{g['err']}</i>")
        shown += 1

    msg = "\n".join(lines)
    if len(msg) > 4096:
        msg = msg[:4000] + "\n<i>... truncated</i>"

    await send_logs(owner_id, msg)


async def start_leave_groups(owner_id: int, phone: str | None = None):
    await stop_leave_groups(owner_id)
    stop_flags[owner_id] = False

    async def run():
        try:
            if phone:
                all_accounts = await db.get_accounts(owner_id)
                accounts = [a for a in all_accounts if a["phone"] == phone]
            else:
                accounts = await db.get_accounts(owner_id)

            if not accounts:
                return

            for i, acc in enumerate(accounts, 1):
                if stop_flags.get(owner_id, False):
                    break
                report = await leave_for_account(owner_id, i, acc)
                await send_leave_report(owner_id, report)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("start_leave_groups run error [owner=%d]: %s", owner_id, e)
        finally:
            leave_tasks.pop(owner_id, None)

    task = asyncio.create_task(run())
    leave_tasks[owner_id] = task
