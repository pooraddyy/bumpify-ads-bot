<div align="center">

# AdsBot

**Professional Telegram group advertising automation system**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-MTProto-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![aiohttp](https://img.shields.io/badge/aiohttp-3.x-2C5282?style=flat-square&logo=python&logoColor=white)](https://docs.aiohttp.org)
[![python-telegram-bot](https://img.shields.io/badge/PTB-v21-0088CC?style=flat-square&logo=telegram&logoColor=white)](https://python-telegram-bot.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-111827?style=flat-square)](LICENSE)

[![Stars](https://img.shields.io/github/stars/pooraddyy/bumpify-ads-bot?style=for-the-badge&color=f59e0b&logo=github&logoColor=white)](https://github.com/pooraddyy/bumpify-ads-bot/stargazers)
[![Channel](https://img.shields.io/badge/Telegram-Channel-0088CC?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/pythontodayz)

</div>

---

```
Multi-account broadcast  ·  AES-256 encrypted sessions  ·  Real-time logger bot
Leave Groups tool  ·  Auto Reply  ·  Web analytics panel  ·  Owner broadcast commands
```

---

## Features

| Module | Description |
|---|---|
| **Multi-Account Broadcast** | Unlimited Telegram accounts broadcasting concurrently — accounts run in parallel chunks with per-account isolation |
| **Owner Broadcast Commands** | `/broadcast` and `/pbroadcast` — send any message to all bot users with live progress, auto-delete command, pin support |
| **Saved Messages Forward** | Forwards directly from each account's Saved Messages — no re-upload, all formatting preserved |
| **All Media Types** | Text, photo, video, document, audio, sticker, voice, video note — every Telegram media type |
| **Leave Groups** | Bulk-leave groups from one or all accounts — with per-group logs, FloodWait handling, and stop control |
| **Auto Reply** | Custom message auto-sent on incoming DMs to any connected account |
| **Logger Bot** | Per-group logs with name, @username, link, ID, sent / failed counts after every cycle |
| **Web Panel** | Telegram WebApp for account login (250+ country codes) and full analytics dashboard |
| **Analytics** | Total sent, success rate, per-account performance with progress indicators, recent feed |
| **AES-256 Encryption** | Fernet + PBKDF2-HMAC-SHA256 — sessions never stored in plaintext |
| **FloodWait Protection** | Automatic wait with smart retry, concurrency semaphores, and per-group delays |
| **Private Mode** | Restrict bot to a comma-separated list of authorized owner IDs |

---

## Owner Commands

### `/broadcast` — Broadcast to all users

Reply to any message with `/broadcast` to send it to every user who has started the bot.

```
Usage:   Reply to a message → /broadcast
Deletes: Command message deleted immediately
Status:  Live progress sent to owner (updated every 25 users)

Shows:   Total  ·  Sent  ·  Blocked  ·  Deleted  ·  Failed
```

### `/pbroadcast` — Broadcast + pin

Same as `/broadcast` but the forwarded message is also pinned in every user's chat.

```
Usage:   Reply to a message → /pbroadcast
Pin:     Message pinned silently after delivery
```

**Both commands support all message types** — text, photo, video, document, sticker, voice, animation, video note — with full formatting preserved (bold, italic, blockquote, code, etc.).

---

## Leave Groups

| Scenario | UI |
|---|---|
| 1 account | Leave All Groups — Stop Leaving — Back |
| Multiple accounts | Account list + From All — Back |
| Specific account | Start Leave All Groups — Back |

- Logs sent to logger bot after each account: left / failed count, group names, links
- FloodWait auto-handled with retry
- Session expiry auto-removes account and notifies owner
- Stop button cancels gracefully at any point

---

## Environment Variables

```env
# Required
BOT_TOKEN=          # Main bot token from @BotFather
LOGGER_BOT_TOKEN=   # Logger bot token from @BotFather
API_ID=             # Telegram API ID from my.telegram.org
API_HASH=           # Telegram API hash from my.telegram.org
MONGODB_URL=        # MongoDB connection string
ENCRYPTION_KEY=     # Min 32-char key for session encryption

# Optional
LOGGER_BOT_USERNAME=  # Logger bot @username (without @)
WEB_APP_URL=          # Public HTTPS URL for the WebApp panel
WEB_PORT=3000         # Web server port
OWNER_IDS=            # Comma-separated owner IDs: 123456,789012
PRIVATE_MODE=false    # Set true to restrict to OWNER_IDS only
LAST_NAME_SUFFIX=     # Appended to account last names (default: -Bumpify)
BIO_TEXT=             # Bio applied to each account after login
AUTO_REPLY_TEXT=      # Default auto-reply text for incoming DMs
START_IMAGE_URL=      # Image shown in the bot start message
```

---

## Quick Start

**Prerequisites** — Python 3.11+, MongoDB, two bot tokens from [@BotFather](https://t.me/botfather), API credentials from [my.telegram.org](https://my.telegram.org)

```bash
git clone https://github.com/pooraddyy/bumpify-ads-bot.git
cd bumpify-ads-bot
pip install -r requirements.txt
cp .env.example .env
nano .env          # fill in required variables
python main.py
```

---

## VPS Deployment

### Install

```bash
ssh root@your-server-ip
apt update && apt install python3.11 python3-pip git -y
git clone https://github.com/pooraddyy/bumpify-ads-bot.git
cd bumpify-ads-bot
pip install -r requirements.txt
cp .env.example .env && nano .env
```

### systemd Service

```ini
# /etc/systemd/system/bumpify.service
[Unit]
Description=Bumpify Ads Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bumpify-ads-bot
ExecStart=/usr/bin/python3.11 main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable bumpify
systemctl start bumpify
systemctl status bumpify        # check status
journalctl -u bumpify -f        # live logs
```

### Update

```bash
cd /root/bumpify-ads-bot && git pull && systemctl restart bumpify
```

### One-Click Deploy with Cloudflare Tunnel

Run the included `deploy.sh` script for instant VPS deployment with a public HTTPS webhook URL:

```bash
bash deploy.sh
```

This will:
- Install `cloudflared` and Python venv dependencies
- Start a Cloudflare Quick Tunnel on port 3000
- Auto-detect the public tunnel URL and update `.env`
- Start the bot and register the webhook
- Print the tunnel URL and bot PIDs

**Requirements:** `python3-venv`, `python3-pip`, `wget`, port 3000 open

---

## HTTPS + Nginx

Required for the Telegram WebApp panel.

```nginx
server {
    listen 80;
    server_name your-domain.com;
    location /panel  { proxy_pass http://127.0.0.1:3000; proxy_set_header Host $host; }
    location /static { proxy_pass http://127.0.0.1:3000; }
    location /api    { proxy_pass http://127.0.0.1:3000; }
}
```

```bash
certbot --nginx -d your-domain.com
```

Set `WEB_APP_URL=https://your-domain.com/panel` in `.env` and restart.

---

## Cloud Platforms

**Railway** — Fork the repo → connect at [railway.app](https://railway.app) → set env vars → start: `python main.py`

**Render** — Fork → Background Worker at [render.com](https://render.com) → start: `python main.py` → set env vars

---

## Security

Sessions are encrypted with **Fernet (AES-256-CBC + HMAC-SHA256)** before storage in MongoDB.  
The `ENCRYPTION_KEY` is processed through **PBKDF2-HMAC-SHA256** with a random per-session salt.

Keep `ENCRYPTION_KEY` and `MONGODB_URL` secret. Never commit `.env`.

---

## Architecture

```
main.py                    — entry point, bot + web startup
bot/
  config.py                — env vars
  handlers/
    start.py               — /start command
    dashboard.py           — dashboard UI
    callbacks.py           — all button routing
    ads.py                 — set ad, start/stop ads
    accounts.py            — account management
    auto_reply.py          — auto reply settings
    interval.py            — broadcast interval
    leave_groups.py        — leave groups UI
    broadcast_cmd.py       — /broadcast, /pbroadcast owner commands
    faq.py                 — FAQ and how-to
  utils/
    broadcaster.py         — core broadcast engine (chunked, parallel)
    leave_groups.py        — leave groups engine
    auto_reply_manager.py  — auto reply Pyrogram clients
    session_manager.py     — Pyrogram session login / decrypt
    db.py                  — MongoDB operations
    encryption.py          — AES-256 session encryption
    helpers.py             — safe_edit and shared utilities
web/
  app.py                   — aiohttp REST API + static serving
  templates/index.html     — WebApp panel
logger_bot/
  handlers.py              — logger bot handlers
```

---

## Contributing

```
Fork  ->  Clone  ->  Branch  ->  Changes  ->  Pull Request
```

---

## License

MIT — see [LICENSE](LICENSE) for full text.

---

<div align="center">
  <sub>
    Built with
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" height="16"/></a>
    <a href="https://pyrogram.org"><img src="https://img.shields.io/badge/Pyrogram-2CA5E0?style=flat-square&logo=telegram&logoColor=white" height="16"/></a>
    <a href="https://mongodb.com"><img src="https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white" height="16"/></a>
    <a href="https://docs.aiohttp.org"><img src="https://img.shields.io/badge/aiohttp-2C5282?style=flat-square" height="16"/></a>
  </sub>
</div>
