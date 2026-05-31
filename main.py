import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.config import BOT_TOKEN, LOGGER_BOT_TOKEN, PRIVATE_MODE, OWNER_IDS, WEB_APP_URL
from bot.handlers.start import start_handler
from bot.handlers.dashboard import dashboard_handler
from bot.handlers.callbacks import callback_handler
from bot.handlers.interval import handle_interval_text
from bot.handlers.auto_reply import handle_auto_reply_text
from bot.handlers.ads import handle_ad_message
from bot.handlers.broadcast_cmd import broadcast_command, pbroadcast_command
from bot.utils import db
from web.app import run_web

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def is_allowed(update) -> bool:
    if not PRIVATE_MODE:
        return True
    user = update.effective_user
    if not user:
        return False
    if not OWNER_IDS:
        logging.warning("PRIVATE_MODE enabled but no OWNER_IDS configured — blocking all users.")
        return False
    return user.id in OWNER_IDS


PRIVATE_MSG = (
    "<b>This bot is private.</b>\n\n"
    "Access is restricted to authorized users only.\n"
    "Contact the bot owner to request access."
)


async def message_handler(update, context):
    if not update.message:
        return
    if not is_allowed(update):
        await update.message.reply_text(PRIVATE_MSG, parse_mode="HTML")
        return
    if await handle_interval_text(update, context):
        return
    if await handle_auto_reply_text(update, context):
        return
    await handle_ad_message(update, context)


async def guarded_start_handler(update, context):
    if not is_allowed(update):
        await update.message.reply_text(PRIVATE_MSG, parse_mode="HTML")
        return
    await start_handler(update, context)


async def guarded_dashboard_handler(update, context):
    if not is_allowed(update):
        await update.message.reply_text(PRIVATE_MSG, parse_mode="HTML")
        return
    await dashboard_handler(update, context)


async def guarded_callback_handler(update, context):
    if not is_allowed(update):
        try:
            await update.callback_query.answer(
                "This bot is private. Unauthorized access.",
                show_alert=True
            )
        except Exception:
            pass
        return
    await callback_handler(update, context)


def build_main_app() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)
        .concurrent_updates(True)
        .build()
    )
    app.add_handler(CommandHandler("start", guarded_start_handler))
    app.add_handler(CommandHandler("dashboard", guarded_dashboard_handler))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("pbroadcast", pbroadcast_command))
    app.add_handler(CallbackQueryHandler(guarded_callback_handler))
    app.add_handler(MessageHandler(
        (
            filters.TEXT
            | filters.PHOTO
            | filters.VIDEO
            | filters.Document.ALL
            | filters.AUDIO
            | filters.ANIMATION
            | filters.Sticker.ALL
            | filters.VOICE
            | filters.VIDEO_NOTE
        ) & ~filters.COMMAND,
        message_handler,
    ))
    return app


async def setup_webhook(app: Application, webhook_url: str):
    await app.initialize()
    await app.start()
    await app.bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "edited_message"],
    )
    logging.info("Webhook set: %s", webhook_url)


async def main():
    await db.connect()
    logging.info("MongoDB connected")

    main_app = build_main_app()

    logger_app = None
    if LOGGER_BOT_TOKEN:
        from logger_bot.handlers import build_logger_app
        logger_app = build_logger_app()

    web_runner = await run_web(main_app, logger_app)

    base_url = WEB_APP_URL.rstrip("/")
    if not base_url:
        logging.warning("WEB_APP_URL is not set — webhook cannot be registered with Telegram.")

    await setup_webhook(main_app, f"{base_url}/webhook/{BOT_TOKEN}")
    logging.info("Main bot started (webhook mode)")

    if logger_app:
        await setup_webhook(logger_app, f"{base_url}/webhook/logger/{LOGGER_BOT_TOKEN}")
        logging.info("Logger bot started (webhook mode)")

    logging.info("All services running. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await main_app.stop()
        await main_app.shutdown()
        if logger_app is not None:
            await logger_app.stop()
            await logger_app.shutdown()
        await web_runner.cleanup()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
