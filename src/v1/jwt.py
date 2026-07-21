from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

import jwt
from prisma import Prisma

from src.settings import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
ONBOARDING_TOKEN_EXPIRE_MINUTES = 10


def create_access_token(user_id: int, pseudo: str | None) -> str:
    payload = {
        "sub": str(user_id),
        "pseudo": pseudo,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_onboarding_token(ln_key: str) -> str:
    payload = {
        "ln_key": ln_key,
        "type": "onboarding",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ONBOARDING_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_onboarding_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "onboarding":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def _hash_refresh_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def create_refresh_token(db: Prisma, user_id: int) -> str:
    refresh_token = token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    await db.refresh_tokens.create(
        data={
            "token_hash": _hash_refresh_token(refresh_token),
            "user_id": user_id,
            "expires_at": expires_at,
        }
    )

    return refresh_token


async def rotate_refresh_token(db: Prisma, refresh_token: str):
    token_hash = _hash_refresh_token(refresh_token)
    stored_token = await db.refresh_tokens.find_unique(where={"token_hash": token_hash})

    if stored_token is None or stored_token.revoked_at is not None:
        raise jwt.InvalidTokenError("Invalid refresh token")

    now = datetime.now(timezone.utc)
    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        await db.refresh_tokens.update(
            where={"id": stored_token.id},
            data={"revoked_at": now},
        )
        raise jwt.ExpiredSignatureError("Refresh token expired")

    user = await db.users.find_unique(where={"id": stored_token.user_id})
    if user is None:
        raise jwt.InvalidTokenError("Unknown user")

    new_refresh_token = token_urlsafe(48)
    await db.refresh_tokens.update(
        where={"id": stored_token.id},
        data={
            "token_hash": _hash_refresh_token(new_refresh_token),
            "expires_at": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "revoked_at": None,
        },
    )

    return user, new_refresh_token
