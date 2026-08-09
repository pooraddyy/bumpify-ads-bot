#!/bin/bash
set -e

apt-get update -qq
apt-get install -y -qq python3-venv python3-pip wget

if ! command -v cloudflared &> /dev/null; then
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
fi

cd /root/bumpify-ads-bot

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --quiet -r requirements.txt

pkill -f cloudflared || true
pkill -f "python main.py" || true

TUNNEL_LOG=$(mktemp)
nohup cloudflared tunnel --url http://localhost:3000 > "$TUNNEL_LOG" 2>&1 &
CLOUDFLARED_PID=$!

sleep 8

TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo "Failed to get tunnel URL"
    cat "$TUNNEL_LOG"
    exit 1
fi

sed -i "s|^WEB_APP_URL=.*|WEB_APP_URL=${TUNNEL_URL}|" .env

nohup ./venv/bin/python main.py > bot.log 2>&1 &
BOT_PID=$!

sleep 5

echo "========================================"
echo "Bot deployed successfully!"
echo "Webhook URL: ${TUNNEL_URL}"
echo "Bot PID: ${BOT_PID}"
echo "Tunnel PID: ${CLOUDFLARED_PID}"
echo "========================================"
echo "Logs: tail -f /root/bumpify-ads-bot/bot.log"
