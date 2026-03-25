from datetime import datetime, timedelta, timezone

import jwt

from src.settings import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 15


def create_access_token(user_id: int, pseudo: str | None) -> str:
    payload = {
        "sub": str(user_id),
        "pseudo": pseudo,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])