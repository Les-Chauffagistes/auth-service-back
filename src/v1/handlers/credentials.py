import jwt
from aiohttp.web_request import Request
from aiohttp.web import json_response, HTTPFound
from prisma import Prisma

from ..services.username_password.login import login_with_username_password
from ..services.username_password.register import create_username_password_account
from ..excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from ..models.register import RegisterPayload
from ..jwt import create_access_token, decode_access_token
from ..app import routes
from init import app


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
