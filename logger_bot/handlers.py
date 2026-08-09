import logging
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bot.config import LOGGER_BOT_TOKEN, BOT_TOKEN

logger = logging.getLogger(__name__)

async def logger_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.utils import db
    await db.save_logger_started(update.effective_user.id)

    main_username = ""
    try:
        async with telegram.Bot(token=BOT_TOKEN) as main_bot:
            info = await main_bot.get_me()
            if info.username:
                main_username = f"@{info.username}"
    except Exception as e:
        logger.warning("Could not fetch main bot info: %s", e)

    bot_ref = f" from {main_username}" if main_username else ""

    await update.message.reply_text(
        f"<b>📊 Logger Bot</b>\n\n"
        f"Subscribed to broadcast reports{bot_ref}.\n\n"
        "<b>You will receive:</b>\n"
        "• Success / failure per group\n"
        "• Per-account breakdown\n"
        "• Next cycle countdown\n\n"
        f"Start broadcasting{bot_ref} to see reports here.",
        parse_mode="HTML",
    )

def build_logger_app() -> Application:
    app = Application.builder().token(LOGGER_BOT_TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", logger_start))
    return app
