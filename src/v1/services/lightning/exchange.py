from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

_EXCHANGE_CODE_TTL_SECONDS = 60

_exchange_codes: dict[str, tuple[dict, datetime]] = {}


def create_exchange_code(user_id: int) -> str:
    code = token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_EXCHANGE_CODE_TTL_SECONDS)
    _exchange_codes[code] = ({"type": "login", "user_id": user_id}, expires_at)
    return code


def create_onboarding_code(ln_key: str) -> str:
    code = token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_EXCHANGE_CODE_TTL_SECONDS)
    _exchange_codes[code] = ({"type": "onboarding", "ln_key": ln_key}, expires_at)
    return code


def consume_exchange_code(code: str) -> dict | None:
    entry = _exchange_codes.pop(code, None)
    if entry is None:
        return None
    payload, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        return None
    return payload
