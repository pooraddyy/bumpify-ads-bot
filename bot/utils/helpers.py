import logging
logger = logging.getLogger(__name__)


async def safe_edit(query, text: str, reply_markup=None, parse_mode: str = "HTML", context=None):
    try:
        await query.edit_message_caption(
            caption=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        return
    except Exception:
        pass
    try:
        await query.edit_message_text(
            text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        return
    except Exception:
        pass
    try:
        await query.message.reply_text(
            text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception as e:
        logger.warning("safe_edit fallback failed: %s", e)
