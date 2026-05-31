from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeExpired, PhoneCodeInvalid
from bot.config import API_ID, API_HASH, ENCRYPTION_KEY, LAST_NAME_SUFFIX, BIO_TEXT
from bot.utils.encryption import encrypt_session, decrypt_session
from bot.utils import db

pending_sessions: dict[str, dict] = {}


async def start_login(phone: str, owner_id: int) -> str:
    client = Client(
        name=f"tmp_{phone}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    await client.connect()
    sent = await client.send_code(phone)
    phone_code_hash = sent.phone_code_hash

    key = f"{owner_id}_{phone}"
    pending_sessions[key] = {
        "client": client,
        "phone_code_hash": phone_code_hash,
    }

    await db.save_pending_session(owner_id, phone, phone_code_hash)

    return phone_code_hash


async def complete_login(phone: str, owner_id: int, code: str, password: str | None = None) -> dict:
    key = f"{owner_id}_{phone}"
    pending = pending_sessions.get(key)

    if pending:
        client: Client = pending["client"]
        phone_code_hash = pending["phone_code_hash"]
    else:
        db_pending = await db.get_pending_session(owner_id, phone)
        if not db_pending:
            raise ValueError("Session expired. Please request a new OTP.")

        phone_code_hash = db_pending["phone_code_hash"]
        client = Client(
            name=f"tmp_{phone}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
        )
        await client.connect()

    try:
        try:
            await client.sign_in(phone, phone_code_hash, code)
        except SessionPasswordNeeded:
            if not password:
                raise ValueError("2FA_REQUIRED")
            await client.check_password(password)
        except PhoneCodeExpired:
            raise ValueError("Code expired. Please request a new OTP.")
        except PhoneCodeInvalid:
            raise ValueError("Invalid code. Please try again.")

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
            photos = await client.get_profile_photos(me.id, limit=1)
            if photos:
                photo_id = str(photos[0].file_id)
        except Exception:
            pass

        session_string = await client.export_session_string()
        encrypted = encrypt_session(session_string, ENCRYPTION_KEY)

        return {
            "name": full_name,
            "phone": phone,
            "session": encrypted,
            "username": username,
            "tg_user_id": tg_user_id,
            "photo_id": photo_id,
        }

    finally:
        pending_sessions.pop(key, None)
        await db.delete_pending_session(owner_id, phone)
        try:
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
