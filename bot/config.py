import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
LOGGER_BOT_TOKEN = os.getenv("LOGGER_BOT_TOKEN", "")
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
MONGODB_URL = os.environ["MONGODB_URL"]
ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]

LAST_NAME_SUFFIX = os.getenv("LAST_NAME_SUFFIX", "-Bumpify")
BIO_TEXT = os.getenv("BIO_TEXT", "Managed by Bumpify | Telegram Ad Automation")
START_IMAGE_URL = os.getenv("START_IMAGE_URL", "")

START_CAPTION = (
    "<b>\U0001f680 Welcome to Bumpify Ads Bot</b>\n\n"
    "The most powerful Telegram group advertising automation.\n\n"
    "\u2022 <b>Premium Ad Broadcasting</b>\n"
    "\u2022 <b>Smart Delays &amp; Flood Protection</b>\n"
    "\u2022 <b>Multi-Account Support</b>\n"
    "\u2022 <b>Real-Time Analytics</b>"
)

AUTO_REPLY_TEXT = os.getenv(
    "AUTO_REPLY_TEXT",
    "I'm currently offline. Please drop your message and I'll get back to you soon."
)

LOGGER_BOT_USERNAME = os.getenv("LOGGER_BOT_USERNAME", "")
WEB_APP_URL = os.getenv("WEB_APP_URL", "")
WEB_PORT = int(os.getenv("WEB_PORT", os.getenv("PORT", "3000")))

DATABASE_NAME = "bumpify"

PRIVATE_MODE = os.getenv("PRIVATE_MODE", "false").lower() in ("1", "true", "yes")

raw_owners = os.getenv("OWNER_IDS", os.getenv("OWNER_ID", ""))
OWNER_IDS: list[int] = [int(x.strip()) for x in raw_owners.split(",") if x.strip().lstrip("-").isdigit()]
OWNER_ID = OWNER_IDS[0] if OWNER_IDS else 0
