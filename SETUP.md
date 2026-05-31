# Bumpify — Setup Guide

## Step 1: Get Telegram Bot Tokens

1. Open [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` — create your **main bot**. Copy the token.
3. Send `/newbot` again — create your **logger bot**. Copy the token.

## Step 2: Get API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone
3. Click "API development tools"
4. Create a new app — copy **API ID** and **API Hash**

## Step 3: MongoDB

1. Go to [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a free cluster
3. Create a database user (username + password)
4. Get the connection string: `mongodb+srv://USER:PASS@cluster.xxx.mongodb.net/`

## Step 4: Fill .env

```
BOT_TOKEN=          <- main bot token from BotFather
LOGGER_BOT_TOKEN=   <- logger bot token from BotFather
LOGGER_BOT_USERNAME= <- logger bot @username (without @)
API_ID=             <- from my.telegram.org
API_HASH=           <- from my.telegram.org
MONGODB_URL=        <- your MongoDB connection string
ENCRYPTION_KEY=     <- any random string, min 32 characters
WEB_APP_URL=        <- public HTTPS URL to /panel (optional)
```

## Step 5: Run

```bash
python main.py
```

All three services start together:
- Main bot
- Logger bot
- Web panel on port 3000

## Step 6: Use the Bot

1. Open your main bot — send `/start`
2. Open your logger bot — send `/start` (required to receive broadcast logs)
3. Dashboard → Add Account → enter phone + OTP via web panel
4. Set Ad Message (send any Telegram message — all media types supported)
5. Set Interval
6. Press Start Ads

## Web Panel

Runs on port 3000. For the Telegram WebApp button:
- Deploy to a server with a public HTTPS domain
- Set `WEB_APP_URL=https://your-domain.com/panel` in `.env`
- Without it, use the fallback Add Account flow

## Deployment (Railway/Render)

1. Push code to GitHub
2. Connect repo to Railway or Render
3. Set all env vars in the platform dashboard
4. Start command: `python main.py`
