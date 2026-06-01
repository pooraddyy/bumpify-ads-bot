from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGODB_URL, DATABASE_NAME
import datetime

mongo_client = None
mongo_db = None

def get_db():
    return mongo_db

async def connect():
    global mongo_client, mongo_db
    mongo_client = AsyncIOMotorClient(
        MONGODB_URL,
        maxPoolSize=50,
        minPoolSize=5,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        socketTimeoutMS=30_000,
    )
    mongo_db = mongo_client[DATABASE_NAME]
    await mongo_db.users.create_index("user_id", unique=True)
    await mongo_db.accounts.create_index([("owner_id", 1), ("phone", 1)])
    await mongo_db.accounts.create_index([("owner_id", 1), ("active", 1)])
    await mongo_db.broadcast_logs.create_index([("owner_id", 1), ("created_at", -1)])
    await mongo_db.broadcast_logs.create_index([("owner_id", 1), ("success", 1)])
    await mongo_db.broadcast_logs.create_index([("owner_id", 1), ("account_phone", 1)])
    await mongo_db.logger_started.create_index("user_id", unique=True)
    await mongo_db.pending_sessions.create_index(
        [("owner_id", 1), ("phone", 1)], unique=True
    )
    PENDING_TTL = 1800
    try:
        await mongo_db.command({
            "collMod": "pending_sessions",
            "index": {"keyPattern": {"created_at": 1}, "expireAfterSeconds": PENDING_TTL},
        })
    except Exception:
        try:
            await mongo_db.pending_sessions.drop_index("created_at_1")
        except Exception:
            pass
        await mongo_db.pending_sessions.create_index(
            "created_at", expireAfterSeconds=PENDING_TTL
        )

async def close():
    if mongo_client:
        mongo_client.close()

async def get_user(user_id: int) -> dict | None:
    return await get_db().users.find_one({"user_id": user_id})

async def upsert_user(user_id: int, data: dict):
    await get_db().users.update_one(
        {"user_id": user_id}, {"$set": data}, upsert=True
    )

async def get_all_users() -> list:
    cursor = get_db().users.find({}, {"user_id": 1, "_id": 0})
    return await cursor.to_list(length=None)

async def set_ad_message_data(user_id: int, data: dict):
    await upsert_user(user_id, {"ad_msg": data})

async def clear_ad_message_data(user_id: int):
    await get_db().users.update_one(
        {"user_id": user_id}, {"$unset": {"ad_msg": ""}}
    )

async def get_ad_message_data(user_id: int) -> dict | None:
    user = await get_user(user_id)
    return user.get("ad_msg") if user else None

async def set_prompt_message(user_id: int, chat_id: int, msg_id: int):
    await upsert_user(user_id, {"prompt_chat_id": chat_id, "prompt_msg_id": msg_id})

async def get_prompt_message(user_id: int) -> tuple[int, int] | None:
    user = await get_user(user_id)
    if user and user.get("prompt_chat_id"):
        return user["prompt_chat_id"], user["prompt_msg_id"]
    return None

async def set_interval(user_id: int, seconds: int):
    await upsert_user(user_id, {"interval": seconds})

async def get_interval(user_id: int) -> int:
    user = await get_user(user_id)
    return int(user.get("interval", 300)) if user else 300

async def set_ads_running(user_id: int, running: bool):
    await upsert_user(user_id, {"ads_running": running})

async def is_ads_running(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("ads_running", False) if user else False

async def set_waiting_for_ad(user_id: int, value: bool):
    await upsert_user(user_id, {"waiting_for_ad": value})

async def is_waiting_for_ad(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("waiting_for_ad", False) if user else False

async def set_waiting_for_interval(user_id: int, value: bool):
    await upsert_user(user_id, {"waiting_for_interval": value})

async def is_waiting_for_interval(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("waiting_for_interval", False) if user else False

async def set_auto_reply_text(user_id: int, text: str):
    await upsert_user(user_id, {"auto_reply_text": text})

async def get_auto_reply_text(user_id: int) -> str | None:
    user = await get_user(user_id)
    return user.get("auto_reply_text") if user else None

async def set_auto_reply_enabled(user_id: int, enabled: bool):
    await upsert_user(user_id, {"auto_reply_enabled": enabled})

async def is_auto_reply_enabled(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("auto_reply_enabled", False) if user else False

async def set_waiting_for_auto_reply(user_id: int, value: bool):
    await upsert_user(user_id, {"waiting_for_auto_reply": value})

async def is_waiting_for_auto_reply(user_id: int) -> bool:
    user = await get_user(user_id)
    return user.get("waiting_for_auto_reply", False) if user else False

async def save_logger_started(user_id: int):
    await get_db().logger_started.update_one(
        {"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True
    )

async def is_logger_started(user_id: int) -> bool:
    doc = await get_db().logger_started.find_one({"user_id": user_id})
    return doc is not None

async def add_account(owner_id: int, phone: str, session_encrypted: str, name: str,
                      username: str = "", tg_user_id: int = 0, photo_id: str = ""):
    await get_db().accounts.update_one(
        {"owner_id": owner_id, "phone": phone},
        {"$set": {
            "session": session_encrypted,
            "name": name,
            "username": username,
            "tg_user_id": tg_user_id,
            "photo_id": photo_id,
            "active": True,
        }},
        upsert=True,
    )

async def get_accounts(owner_id: int) -> list:
    cursor = get_db().accounts.find({"owner_id": owner_id, "active": True})
    return await cursor.to_list(length=None)

async def get_all_accounts(owner_id: int) -> list:
    cursor = get_db().accounts.find({"owner_id": owner_id})
    return await cursor.to_list(length=None)

async def toggle_account_active(owner_id: int, phone: str) -> bool:
    acc = await get_db().accounts.find_one({"owner_id": owner_id, "phone": phone})
    if not acc:
        return False
    new_state = not acc.get("active", True)
    await get_db().accounts.update_one(
        {"owner_id": owner_id, "phone": phone},
        {"$set": {"active": new_state}},
    )
    return new_state

async def remove_account(owner_id: int, phone: str):
    await get_db().accounts.delete_one({"owner_id": owner_id, "phone": phone})

async def log_broadcast(owner_id: int, account_phone: str, account_num: int,
                        group_id: int, group_title: str, group_username: str,
                        success: bool, error: str = ""):
    await get_db().broadcast_logs.insert_one({
        "owner_id": owner_id,
        "account_phone": account_phone,
        "account_num": account_num,
        "group_id": group_id,
        "group_title": group_title,
        "group_username": group_username,
        "success": success,
        "error": error,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    })

async def get_broadcast_stats(owner_id: int) -> dict:
    total = await get_db().broadcast_logs.count_documents({"owner_id": owner_id})
    success = await get_db().broadcast_logs.count_documents({"owner_id": owner_id, "success": True})
    failed = total - success
    return {"total": total, "success": success, "failed": failed}

async def get_per_account_stats(owner_id: int) -> list:
    pipeline = [
        {"$match": {"owner_id": owner_id}},
        {"$group": {
            "_id": "$account_phone",
            "total": {"$sum": 1},
            "success": {"$sum": {"$cond": ["$success", 1, 0]}},
            "failed": {"$sum": {"$cond": ["$success", 0, 1]}},
        }},
        {"$sort": {"total": -1}},
    ]
    cursor = get_db().broadcast_logs.aggregate(pipeline)
    return await cursor.to_list(length=None)

async def get_recent_broadcast_logs(owner_id: int, limit: int = 30) -> list:
    cursor = get_db().broadcast_logs.find(
        {"owner_id": owner_id},
        {"_id": 0, "owner_id": 0},
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=None)

async def save_pending_session(owner_id: int, phone: str, phone_code_hash: str, pre_auth_session: str = ""):
    await get_db().pending_sessions.update_one(
        {"owner_id": owner_id, "phone": phone},
        {"$set": {
            "owner_id": owner_id,
            "phone": phone,
            "phone_code_hash": phone_code_hash,
            "pre_auth_session": pre_auth_session,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }},
        upsert=True,
    )

async def get_pending_session(owner_id: int, phone: str) -> dict | None:
    return await get_db().pending_sessions.find_one(
        {"owner_id": owner_id, "phone": phone}
    )

async def delete_pending_session(owner_id: int, phone: str):
    await get_db().pending_sessions.delete_one(
        {"owner_id": owner_id, "phone": phone}
    )
