import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.handlers import MessageHandler
from bot.utils import db
from bot.utils.session_manager import get_pyrogram_client
from bot.config import AUTO_REPLY_TEXT

logger = logging.getLogger(__name__)

auto_reply_tasks: dict[int, asyncio.Task] = {}
auto_reply_clients: dict[str, Client] = {}

async def start_auto_reply(owner_id: int):
    await stop_auto_reply(owner_id)

    async def run():
        accounts = await db.get_accounts(owner_id)
        clients = []
        for acc in accounts:
            try:
                client = await get_pyrogram_client(acc["session"], name=f"ar_{acc['phone']}")

                def make_handler(phone):
                    async def on_message(c, message):
                        if not message.from_user:
                            return
                        if message.chat.type != ChatType.PRIVATE:
                            return
                        if message.from_user.is_self:
                            return
                        if not await db.is_auto_reply_enabled(owner_id):
                            return
                        text = await db.get_auto_reply_text(owner_id) or AUTO_REPLY_TEXT
                        try:
                            await message.reply(text)
                        except Exception as e:
                            logger.warning("auto_reply send failed [%s]: %s", phone, e)
                    return on_message

                handler_fn = make_handler(acc["phone"])
                client.add_handler(MessageHandler(handler_fn, filters.private & ~filters.me))
                await client.start()
                clients.append(client)
                auto_reply_clients[acc["phone"]] = client
                logger.info("auto_reply started for %s", acc["phone"])
            except Exception as e:
                logger.warning("auto_reply client failed [%s]: %s", acc.get("phone"), e)

        if clients:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
            finally:
                for c in clients:
                    try:
                        await c.stop()
                    except Exception:
                        pass
                for acc in accounts:
                    auto_reply_clients.pop(acc.get("phone", ""), None)

    task = asyncio.create_task(run())
    auto_reply_tasks[owner_id] = task

async def stop_auto_reply(owner_id: int):
    task = auto_reply_tasks.pop(owner_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def stop_all_auto_replies():
    for owner_id in list(auto_reply_tasks.keys()):
        await stop_auto_reply(owner_id)
