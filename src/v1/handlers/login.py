import jwt
from aiohttp.web_request import Request
from aiohttp.web import json_response
from prisma import Prisma

from ..services.username_password.login import login_with_username_password
from ..services.username_password.register import create_username_password_account
from ..excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from ..models.register import RegisterPayload
from ..jwt import create_access_token, decode_access_token
from ..app import routes
from init import app


@routes.get("/auth/me")
async def me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return json_response({"error": "Missing token"}, status=401)

    token = auth_header.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid token"}, status=401)

    return json_response({"user_id": payload["sub"], "pseudo": payload["pseudo"]})


@routes.post("/auth/register")
async def register(request: Request):
    prisma: Prisma = app["prisma"]
    raw_payload = await request.json()
    payload = RegisterPayload(**raw_payload)

    try:
        user = await create_username_password_account(prisma, payload.username, payload.password)
    except UsernameAlreadyInUseException:
        return json_response({"error": "Username already in use"}, status=409)

    token = create_access_token(user.id, user.pseudo)
    return json_response({"access_token": token})


@routes.post("/auth/login")
async def login(request: Request):
    prisma: Prisma = app["prisma"]
    raw_payload = await request.json()
    payload = RegisterPayload(**raw_payload)

    try:
        user = await login_with_username_password(prisma, payload.username, payload.password)
    except (UnkownUserExpcetion, WrongCredentialsException):
        return json_response({"error": "Unknown user or wrong password"}, status=401)

    token = create_access_token(user.id, user.pseudo)
    return json_response({"access_token": token})