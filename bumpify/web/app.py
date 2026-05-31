import asyncio
import logging
import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application
from bot.config import WEB_PORT, BOT_TOKEN, LOGGER_BOT_TOKEN
from bot.utils import db
from bot.utils.session_manager import start_login, complete_login

log = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get("/")
async def index(request: web.Request):
    raise web.HTTPFound("/panel")


@routes.get("/panel")
async def panel(request: web.Request):
    with open("web/templates/index.html", "r") as f:
        content = f.read()
    return web.Response(text=content, content_type="text/html")


@routes.get("/static/{filename}")
async def static_files(request: web.Request):
    filename = request.match_info["filename"]
    filepath = f"web/static/{filename}"
    if not os.path.exists(filepath):
        raise web.HTTPNotFound()
    with open(filepath, "rb") as f:
        content = f.read()
    ct = {"css": "text/css", "js": "application/javascript"}.get(
        filename.rsplit(".", 1)[-1], "application/octet-stream"
    )
    return web.Response(body=content, content_type=ct)


@routes.post("/api/send-otp")
async def send_otp(request: web.Request):
    try:
        body = await request.json()
        phone = body.get("phone", "").strip()
        user_id = int(body.get("user_id", 0))
        if not phone or not user_id:
            return web.json_response({"ok": False, "error": "Missing phone or user_id"})
        await start_login(phone, user_id)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


@routes.post("/api/verify-otp")
async def verify_otp(request: web.Request):
    try:
        body = await request.json()
        phone = body.get("phone", "").strip()
        user_id = int(body.get("user_id", 0))
        code = body.get("code", "").strip()
        password = body.get("password", "").strip() or None
        if not phone or not user_id or not code:
            return web.json_response({"ok": False, "error": "Missing required fields"})
        result = await complete_login(phone, user_id, code, password)
        await db.add_account(
            user_id,
            result["phone"],
            result["session"],
            result["name"],
            username=result.get("username", ""),
            tg_user_id=result.get("tg_user_id", 0),
            photo_id=result.get("photo_id", ""),
        )
        return web.json_response({
            "ok": True,
            "name": result["name"],
            "username": result.get("username", ""),
            "tg_user_id": result.get("tg_user_id", 0),
            "phone": result["phone"],
        })
    except ValueError as e:
        msg = str(e)
        if msg == "2FA_REQUIRED":
            return web.json_response({"ok": False, "error": "2FA_REQUIRED"})
        return web.json_response({"ok": False, "error": msg})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


@routes.get("/api/accounts")
async def get_accounts(request: web.Request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"ok": False, "error": "Missing user_id"})
        accounts = await db.get_all_accounts(user_id)
        result = [
            {
                "name": a.get("name", ""),
                "phone": a["phone"],
                "username": a.get("username", ""),
                "tg_user_id": a.get("tg_user_id", 0),
                "photo_id": a.get("photo_id", ""),
                "active": a.get("active", True),
            }
            for a in accounts
        ]
        return web.json_response({"ok": True, "accounts": result})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


@routes.post("/api/toggle-account")
async def toggle_account(request: web.Request):
    try:
        body = await request.json()
        user_id = int(body.get("user_id", 0))
        phone = body.get("phone", "").strip()
        if not user_id or not phone:
            return web.json_response({"ok": False, "error": "Missing fields"})
        new_state = await db.toggle_account_active(user_id, phone)
        return web.json_response({"ok": True, "active": new_state})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


@routes.post("/api/remove-account")
async def remove_account(request: web.Request):
    try:
        body = await request.json()
        user_id = int(body.get("user_id", 0))
        phone = body.get("phone", "").strip()
        if not user_id or not phone:
            return web.json_response({"ok": False, "error": "Missing fields"})
        await db.remove_account(user_id, phone)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


@routes.get("/api/stats")
async def get_stats(request: web.Request):
    try:
        user_id = int(request.query.get("user_id", 0))
        if not user_id:
            return web.json_response({"ok": False, "error": "Missing user_id"})
        stats = await db.get_broadcast_stats(user_id)
        per_account = await db.get_per_account_stats(user_id)
        recent = await db.get_recent_broadcast_logs(user_id, 30)
        rate = round(stats["success"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        return web.json_response({
            "ok": True,
            "total": stats["total"],
            "success": stats["success"],
            "failed": stats["failed"],
            "rate": rate,
            "per_account": [
                {
                    "phone": p["_id"],
                    "total": p["total"],
                    "success": p["success"],
                    "failed": p["failed"],
                    "rate": round(p["success"] / p["total"] * 100, 1) if p["total"] > 0 else 0,
                }
                for p in per_account
            ],
            "recent": recent,
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


def build_web_app(main_bot_app: Application, logger_bot_app: Application | None = None) -> web.Application:
    app = web.Application(client_max_size=10 * 1024 * 1024)
    app.add_routes(routes)

    async def main_webhook(request: web.Request):
        token = request.match_info["token"]
        if token != BOT_TOKEN:
            return web.Response(status=403, text="forbidden")
        try:
            data = await request.json()
            update = Update.de_json(data, main_bot_app.bot)
            asyncio.ensure_future(main_bot_app.process_update(update))
        except Exception as e:
            log.warning("main_webhook dispatch error: %s", e)
        return web.Response(text="ok")

    async def logger_webhook(request: web.Request):
        if not logger_bot_app:
            return web.Response(status=404, text="not found")
        token = request.match_info["token"]
        if token != LOGGER_BOT_TOKEN:
            return web.Response(status=403, text="forbidden")
        try:
            data = await request.json()
            update = Update.de_json(data, logger_bot_app.bot)
            asyncio.ensure_future(logger_bot_app.process_update(update))
        except Exception as e:
            log.warning("logger_webhook dispatch error: %s", e)
        return web.Response(text="ok")

    app.router.add_post("/webhook/{token}", main_webhook)
    app.router.add_post("/webhook/logger/{token}", logger_webhook)

    return app


async def run_web(main_bot_app: Application, logger_bot_app: Application | None = None):
    app = build_web_app(main_bot_app, logger_bot_app)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT, reuse_address=True)
    await site.start()
    log.info("Web server started on port %d", WEB_PORT)
    return runner
