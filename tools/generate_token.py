from datetime import datetime, timedelta, timezone
from os import getenv

from dotenv import load_dotenv
import jwt
load_dotenv(".env")

ACCESS_TOKEN_EXPIRE_MINUTES = 52
REFRESH_TOKEN_EXPIRE_DAYS = 30
ONBOARDING_TOKEN_EXPIRE_MINUTES = 10


def create_access_token(user_id: int, pseudo: str | None) -> str:
    payload = {
        "sub": str(user_id),
        "pseudo": pseudo,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(weeks=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, getenv("JWT_SECRET"), algorithm="HS256")

print(create_access_token(1, "swakraft@id"))