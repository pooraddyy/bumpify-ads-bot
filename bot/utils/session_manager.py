import asyncio
import json
import logging
import time

from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    AuthKeyUnregistered,
    AuthKeyInvalid,
    PasswordHashInvalid,
)
from bot.config import API_ID, API_HASH, ENCRYPTION_KEY, LAST_NAME_SUFFIX, BIO_TEXT
from bot.utils.encryption import encrypt_session, decrypt_session
from bot.utils import db

log = logging.getLogger(__name__)

pending_sessions: dict[str, dict] = {}
pending_2fa_clients: dict[str, dict] = {}

PENDING_MAX_AGE = 30 * 60


def is_client_connected(client: Client) -> bool:
    try:
        return bool(getattr(client, "is_connected", False))
    except Exception:
        return False


async def ensure_connected(client: Client, timeout: float = 15.0) -> bool:
    if is_client_connected(client):
        return True
    log.info("Client not connected — reconnecting (timeout=%.0fs)", timeout)
    try:
        await asyncio.wait_for(client.connect(), timeout=timeout)
        log.info("Client reconnected successfully")
        return True
    except asyncio.TimeoutError:
        log.warning("Reconnect timed out after %.0fs", timeout)
        return False
    except Exception as exc:
        log.warning("Reconnect failed: %s", exc)
        return False


def cleanup_stale_pending() -> None:
    now = time.monotonic()
    stale = [
        k for k, v in list(pending_sessions.items())
        if now - v.get("created_at", 0) > PENDING_MAX_AGE
    ]
    for k in stale:
        entry = pending_sessions.pop(k, None)
        if entry and entry.get("client"):
            try:
                asyncio.ensure_future(entry["client"].disconnect())
            except Exception:
                pass
    stale_2fa = [
        k for k, v in list(pending_2fa_clients.items())
        if now - v.get("created_at", 0) > PENDING_MAX_AGE
    ]
    for k in stale_2fa:
        entry = pending_2fa_clients.pop(k, None)
        if entry and entry.get("client"):
            try:
                asyncio.ensure_future(entry["client"].disconnect())
            except Exception:
                pass
    if stale or stale_2fa:
        log.debug("Cleaned up %d stale pending session(s)", len(stale) + len(stale_2fa))


async def save_pre_auth(client: Client) -> str:
    try:
        dc_id = await client.storage.dc_id()
        auth_key_bytes = await client.storage.auth_key()
        if dc_id and auth_key_bytes:
            payload = json.dumps({"dc_id": dc_id, "auth_key": auth_key_bytes.hex()})
            return encrypt_session(payload, ENCRYPTION_KEY)
    except Exception as exc:
        log.debug("pre_auth save skipped: %s", exc)
    return ""


async def make_client_from_pre_auth(phone: str, encrypted_pre_auth: str) -> Client | None:
    try:
        payload_str = decrypt_session(encrypted_pre_auth, ENCRYPTION_KEY)
        payload = json.loads(payload_str)
        dc_id = int(payload["dc_id"])
        auth_key_bytes = bytes.fromhex(payload["auth_key"])

        client = Client(
            name=f"tmp_{phone}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
        )
        await client.storage.dc_id(dc_id)
        await client.storage.auth_key(auth_key_bytes)
        return client
    except Exception as exc:
        log.warning("pre_auth restore failed (%s) — will create fresh client", exc)
        return None


async def finish_login(client: Client, phone: str) -> dict:
    me = await client.get_me()
    first_name = me.first_name or ""
    last_name = me.last_name or ""

    if not last_name.endswith(LAST_NAME_SUFFIX):
        new_last = last_name + LAST_NAME_SUFFIX
        await client.update_profile(last_name=new_last, bio=BIO_TEXT)
        last_name = new_last

    full_name = f"{first_name} {last_name}".strip()
    username = me.username or ""
    tg_user_id = me.id

    photo_id = ""
    try:
        async for photo in client.get_profile_photos(me.id, limit=1):
            photo_id = str(photo.file_id)
            break
    except Exception:
        pass

    session_string = await client.export_session_string()
    encrypted = encrypt_session(session_string, ENCRYPTION_KEY)

    log.info("Login successful for phone=%s tg_id=%d", phone, tg_user_id)
    return {
        "name": full_name,
        "phone": phone,
        "session": encrypted,
        "username": username,
        "tg_user_id": tg_user_id,
        "photo_id": photo_id,
    }


async def start_login(phone: str, owner_id: int) -> str:
    cleanup_stale_pending()

    key = f"{owner_id}_{phone}"
    existing = pending_sessions.pop(key, None)
    if existing and existing.get("client"):
        try:
            await existing["client"].disconnect()
        except Exception:
            pass

    client = Client(
        name=f"tmp_{phone}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    await client.connect()
    sent = await client.send_code(phone)
    phone_code_hash = sent.phone_code_hash

    encrypted_pre_auth = await save_pre_auth(client)

    pending_sessions[key] = {
        "client": client,
        "phone_code_hash": phone_code_hash,
        "created_at": time.monotonic(),
    }

    await db.save_pending_session(owner_id, phone, phone_code_hash, encrypted_pre_auth)
    log.info("OTP sent for phone=%s owner=%d", phone, owner_id)
    return phone_code_hash


async def complete_login(
    phone: str,
    owner_id: int,
    code: str,
    password: str | None = None,
) -> dict:
    key = f"{owner_id}_{phone}"

    two_fa = pending_2fa_clients.get(key)
    if two_fa:
        if not password:
            raise ValueError("2FA_REQUIRED")

        client = two_fa["client"]

        if not await ensure_connected(client):
            pending_2fa_clients.pop(key, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            raise ValueError("Connection lost during 2FA. Please request a new OTP.")

        try:
            await client.check_password(password)
        except PasswordHashInvalid:
            raise ValueError("Wrong 2FA password. Please try again.")
        except Exception as exc:
            pending_2fa_clients.pop(key, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            raise ValueError(f"2FA verification failed. Please request a new OTP.")

        try:
            return await finish_login(client, phone)
        finally:
            pending_2fa_clients.pop(key, None)
            try:
                await client.disconnect()
            except Exception:
                pass

    pending = pending_sessions.get(key)
    client: Client | None = None
    phone_code_hash: str = ""
    phase_2fa = False

    if pending:
        client = pending["client"]
        phone_code_hash = pending["phone_code_hash"]
        log.info("Found in-memory session for phone=%s", phone)

        if not await ensure_connected(client):
            log.warning(
                "Reconnect of in-memory client failed for phone=%s — "
                "falling back to DB restore",
                phone,
            )
            client = None

    if client is None:
        log.info("Attempting DB restore for phone=%s owner=%d", phone, owner_id)
        db_pending = await db.get_pending_session(owner_id, phone)
        if not db_pending:
            raise ValueError("Session expired. Please request a new OTP.")

        phone_code_hash = db_pending["phone_code_hash"]
        encrypted_pre_auth = db_pending.get("pre_auth_session", "")

        if encrypted_pre_auth:
            client = await make_client_from_pre_auth(phone, encrypted_pre_auth)

        if client is None:
            log.warning(
                "No pre_auth available for phone=%s — "
                "fresh client (sign_in may fail with code expired)",
                phone,
            )
            client = Client(
                name=f"tmp_{phone}",
                api_id=API_ID,
                api_hash=API_HASH,
                in_memory=True,
            )

        try:
            await asyncio.wait_for(client.connect(), timeout=15)
        except asyncio.TimeoutError:
            raise ValueError("Connection timed out. Please request a new OTP.")
        except (AuthKeyUnregistered, AuthKeyInvalid):
            raise ValueError("Session key is no longer valid. Please request a new OTP.")
        except Exception as exc:
            raise ValueError(f"Could not connect to Telegram: {exc}. Please request a new OTP.")

    try:
        try:
            await client.sign_in(phone, phone_code_hash, code)
        except SessionPasswordNeeded:
            if not password:
                pending_2fa_clients[key] = {
                    "client": client,
                    "created_at": time.monotonic(),
                }
                pending_sessions.pop(key, None)
                await db.delete_pending_session(owner_id, phone)
                phase_2fa = True
                raise ValueError("2FA_REQUIRED")
            await client.check_password(password)
        except PhoneCodeExpired:
            raise ValueError("Code expired. Please request a new OTP.")
        except PhoneCodeInvalid:
            raise ValueError("Invalid code. Please try again.")
        except PasswordHashInvalid:
            raise ValueError("Wrong 2FA password. Please try again.")

        return await finish_login(client, phone)

    finally:
        if not phase_2fa:
            pending_sessions.pop(key, None)
            await db.delete_pending_session(owner_id, phone)
            try:
                if client:
                    await client.disconnect()
            except Exception:
                pass


async def get_pyrogram_client(session_encrypted: str, name: str = "acc") -> Client:
    session_string = decrypt_session(session_encrypted, ENCRYPTION_KEY)
    client = Client(
        name=name,
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
    )
    return client
