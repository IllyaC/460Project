import hashlib
import os
import secrets


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.sha256(salt + password.encode()).hexdigest()
    return f"{salt.hex()}:{digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, stored_digest = hashed_password.split(":", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    computed = hashlib.sha256(salt + plain_password.encode()).hexdigest()
    return secrets.compare_digest(computed, stored_digest)
