from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils.helpers import safe_edit

FAQ_TEXT = (
    "<b>FAQ</b>\n\n"
    "<blockquote><b>Q: How many accounts can I add?</b>\n"
    "Unlimited. The bot handles any number of accounts concurrently in parallel chunks.</blockquote>\n\n"
    "<blockquote><b>Q: Will my sessions expire?</b>\n"
    "Sessions are permanent unless you log out from Telegram settings or get banned. Expired sessions are automatically removed.</blockquote>\n\n"
    "<blockquote><b>Q: What message types are supported for ads?</b>\n"
    "Text, photo, video, document, audio, animation, sticker, voice, video note — all Telegram media types.</blockquote>\n\n"
    "<blockquote><b>Q: Is formatting preserved in broadcast?</b>\n"
    "Yes. Bold, italic, code, blockquote, strikethrough, underline — all preserved. The ad is forwarded directly from each account's Saved Messages so no re-encoding occurs.</blockquote>\n\n"
    "<blockquote><b>Q: How does the broadcast work?</b>\n"
    "Your ad message is saved to each account's Saved Messages. During broadcast, each account forwards that message to every group it is a member of.</blockquote>\n\n"
    "<blockquote><b>Q: What are /broadcast and /pbroadcast?</b>\n"
    "Owner-only commands to send any message to all bot users. Reply to a message with /broadcast to send it. /pbroadcast sends and pins the message in every user's chat.</blockquote>"
)

HOWTO_TEXT = (
    "<b>How To Use</b>\n\n"
    "<blockquote>1. Add your Telegram accounts via the web panel\n"
    "2. Set your ad message (any media type)\n"
    "3. Set an interval (how often to re-broadcast)\n"
    "4. Press Start Ads</blockquote>\n\n"
    "<blockquote>Your logger bot will receive detailed logs after each cycle showing:\n"
    "- Every group name, username, link and ID\n"
    "- Success / failed counts per account\n"
    "- Next cycle countdown</blockquote>\n\n"
    "<blockquote><b>Leave Groups:</b> Go to Dashboard → Leave Groups to bulk-leave groups from one or all accounts. Logs are sent after each account.</blockquote>"
)


async def faq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("How To Use", callback_data="howto", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("Back", callback_data="home", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, FAQ_TEXT, reply_markup=keyboard, parse_mode="HTML", context=context)


async def howto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Home", callback_data="home", api_kwargs={"style": "danger"})],
    ])
    await safe_edit(query, HOWTO_TEXT, reply_markup=keyboard, parse_mode="HTML", context=context)
