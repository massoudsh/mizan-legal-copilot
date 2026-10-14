"""Tenant-scoped bearer-token authentication and RBAC."""

import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum

from fastapi import Header, HTTPException, status



class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


@dataclass(frozen=True)
class Principal:
    user_id: int
    organization_id: str
    role: Role


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_role(*roles: Role):
    async def dependency(authorization: str | None = Header(default=None)) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن دسترسی ارسال نشده است.")
        from app import storage

        principal = storage.get_principal(token_digest(authorization.removeprefix("Bearer ")))
        if principal is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن دسترسی نامعتبر است.")
        if roles and principal.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی لازم برای این عملیات را ندارید.")
        return principal

    return dependency
