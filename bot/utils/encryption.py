import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_fernet(key: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"bumpify_salt_v1",
        iterations=480000,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return Fernet(derived)

def encrypt_session(session_string: str, key: str) -> str:
    f = get_fernet(key)
    return f.encrypt(session_string.encode()).decode()

def decrypt_session(encrypted: str, key: str) -> str:
    f = get_fernet(key)
    return f.decrypt(encrypted.encode()).decode()
