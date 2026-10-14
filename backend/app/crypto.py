"""Encryption for sensitive public lead fields."""

import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.getenv("MIZAN_DATA_ENCRYPTION_KEY")
    if not key:
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise RuntimeError("MIZAN_DATA_ENCRYPTION_KEY must be set in production.")
        key = "R0s6ugUwPavxEu4qgDM6j5d85q9Cv3Ce1G1ll7l6ZEA="
    return Fernet(key.encode())


def encrypt(value: str | None) -> str | None:
    return _fernet().encrypt(value.encode()).decode() if value else None


def decrypt(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt protected data") from exc
