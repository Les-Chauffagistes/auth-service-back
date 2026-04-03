from aiohttp.web_exceptions import HTTPFound
from aiohttp.web_request import Request
from aiohttp.web import json_response
from prisma import Prisma

from ..cookie import set_cookie_and_redirect
from ..services.username_password.login import login_with_username_password
from ..services.username_password.register import create_username_password_account
from ..excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from ..models.register import RegisterPayload
from ..jwt import create_access_token, create_refresh_token
from ..app import routes


async def _authenticate(prisma: Prisma, raw_payload: dict):
    payload = RegisterPayload(**raw_payload)
    user = await login_with_username_password(prisma, payload.username, payload.password)
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(None, access_token, refresh_token)
    return response


async def _register(prisma: Prisma, raw_payload: dict):
    payload = RegisterPayload(**raw_payload)
    user = await create_username_password_account(prisma, payload.username, payload.password)
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(None, access_token, refresh_token)
    return response


@routes.post("/auth/login-or-register")
async def login_or_register(request: Request):
    prisma: Prisma = request.app["prisma"]
    raw_payload = await request.json()
    try:
        return await _authenticate(prisma, raw_payload)
    except UnkownUserExpcetion:
        try:
            return await _register(prisma, raw_payload)
        except UsernameAlreadyInUseException:
            return json_response({"error": "Username already in use"}, status=409)
    except WrongCredentialsException:
        return json_response({"error": "Unknown user or wrong password"}, status=401)