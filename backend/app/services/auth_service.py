"""
Silent Frequency — Auth Service

Minimal register/login/logout logic for internal testing.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import UserAccount


_PBKDF2_ALGORITHM = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 200_000


class AuthServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != _PBKDF2_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest.hex(), digest_hex)


def _new_auth_token() -> str:
    return secrets.token_urlsafe(48)


def _normalize_username(username: str) -> str:
    return username.strip()


async def register_user(
    db: AsyncSession,
    username: str,
    password: str,
    real_name: str | None = None,
) -> dict[str, str | uuid.UUID | None]:
    normalized_username = _normalize_username(username)
    existing_result = await db.execute(
        select(UserAccount).where(UserAccount.username == normalized_username)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        raise AuthServiceError(
            code="USERNAME_TAKEN",
            message="Username already exists",
            status_code=409,
        )

    user = UserAccount(
        username=normalized_username,
        password_hash=_hash_password(password),
        real_name=real_name.strip() if real_name else None,
        auth_token=_new_auth_token(),
        last_login_at=_utcnow(),
    )
    db.add(user)
    await db.commit()

    return {
        "user_id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "auth_token": user.auth_token,
    }


async def login_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> dict[str, str | uuid.UUID | None]:
    normalized_username = _normalize_username(username)
    result = await db.execute(
        select(UserAccount).where(UserAccount.username == normalized_username)
    )
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(password, user.password_hash):
        raise AuthServiceError(
            code="INVALID_CREDENTIALS",
            message="Invalid username or password",
            status_code=401,
        )

    user.auth_token = _new_auth_token()
    user.last_login_at = _utcnow()
    await db.commit()

    return {
        "user_id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "auth_token": user.auth_token,
    }


async def logout_user(db: AsyncSession, auth_token: str) -> None:
    result = await db.execute(
        select(UserAccount).where(UserAccount.auth_token == auth_token)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthServiceError(
            code="INVALID_TOKEN",
            message="Invalid auth token",
            status_code=401,
        )

    user.auth_token = None
    await db.commit()
