import jwt
from aiohttp.web_request import Request

from .cookie import ACCESS_TOKEN_COOKIE_NAME
from .jwt import decode_access_token


def resolve_authenticated_user_id(request: Request) -> int | None:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not access_token:
        return None

    try:
        payload = decode_access_token(access_token)
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None

    try:
        return int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None
