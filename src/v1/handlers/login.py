import jwt
from aiohttp.web_request import Request
from aiohttp.web import json_response
from src.settings import settings
from ..cookie import delete_cookies

from ..jwt import create_access_token, decode_access_token, rotate_refresh_token
from ..app import routes
from init import app


@routes.get("/auth/me")
async def me(request: Request):
    token = request.cookies.get("access_token")
    
    if not token:
        return json_response({"error": "Missing token"}, status=401)
    
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid token"}, status=401)

    return json_response({"user_id": payload["sub"], "pseudo": payload["pseudo"]})

@routes.post("/auth/refresh")
async def refresh_token(request: Request):
    provided_refresh_token = request.cookies.get("refresh_token")

    if not provided_refresh_token:
        try:
            raw_payload = await request.json()
        except ValueError:
            raw_payload = {}
        provided_refresh_token = raw_payload.get("refresh_token")

    if not provided_refresh_token:
        return json_response({"error": "Missing refresh token"}, status=401)

    prisma = request.app["prisma"]

    try:
        user, new_refresh_token = await rotate_refresh_token(prisma, provided_refresh_token)
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Refresh token expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid refresh token"}, status=401)

    access_token = create_access_token(user.id, user.pseudo)
    response = json_response(
        {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }
    )

    if request.cookies.get("refresh_token"):
        response.set_cookie(
            "refresh_token",
            new_refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            domain=settings.domain_name,
            path="/",
        )
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            domain=settings.domain_name,
            path="/",
        )

    return response

@routes.delete("/auth/logout")
async def logout(_: Request):
    response = delete_cookies()
    return response