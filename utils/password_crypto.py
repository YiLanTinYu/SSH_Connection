"""Password encryption helpers for portable AOMT Excel files."""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


PREFIX = "AOMT_ENC_V1$"
AAD = b"AOMT Excel Password v1"
PBKDF2_ITERATIONS = 600_000


class PasswordDecryptionError(ValueError):
    pass


def is_encrypted_password(value: str) -> bool:
    return str(value or "").startswith(PREFIX)


def _derive_key(master_password: str, salt: bytes) -> bytes:
    if not master_password:
        raise ValueError("master password is required")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(master_password.encode("utf-8"))


def encrypt_password(password: str, master_password: str) -> str:
    if password is None or str(password) == "":
        return ""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(master_password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, str(password).encode("utf-8"), AAD)
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return PREFIX + "$".join((encode(salt), encode(nonce), encode(ciphertext)))


def decrypt_password(value: str, master_password: str) -> str:
    if not is_encrypted_password(value):
        return str(value or "")
    try:
        parts = str(value).split("$")
        if len(parts) != 4 or parts[0] != PREFIX.rstrip("$"):
            raise ValueError
        decode = lambda item: base64.urlsafe_b64decode(item.encode("ascii"))
        salt, nonce, ciphertext = map(decode, parts[1:])
        key = _derive_key(master_password, salt)
        return AESGCM(key).decrypt(nonce, ciphertext, AAD).decode("utf-8")
    except (InvalidTag, ValueError, UnicodeError) as exc:
        raise PasswordDecryptionError("主密码错误或密文已损坏") from exc
