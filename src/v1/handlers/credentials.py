from aiohttp.web_exceptions import HTTPOk
from aiohttp.web_request import Request
from aiohttp.web import json_response
from prisma import Prisma

from ..auth import resolve_authenticated_user_id
from ..cookie import set_cookie_and_redirect
from ..services.username_password.login import login_with_username_password
from ..services.username_password.register import (
    CredentialsProviderAlreadyLinkedError,
    create_username_password_account,
    link_username_password_account,
)
from ..excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from ..models.register import RegisterPayload
from ..jwt import create_access_token, create_refresh_token
from ..app import routes


async def _authenticate(prisma: Prisma, raw_payload: dict):
    payload = RegisterPayload(**raw_payload)
    user = await login_with_username_password(prisma, payload.username, payload.password)
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(HTTPOk(), access_token, refresh_token)
    return response


async def _register(prisma: Prisma, raw_payload: dict):
    payload = RegisterPayload(**raw_payload)
    user = await create_username_password_account(prisma, payload.username, payload.password)
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(HTTPOk(), access_token, refresh_token)
    return response


@routes.post("/login-or-register")
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


@routes.post("/credentials/link")
async def link_credentials(request: Request):
    prisma: Prisma = request.app["prisma"]
    linked_user_id = resolve_authenticated_user_id(request)
    if linked_user_id is None:
        return json_response({"error": "Unauthorized"}, status=401)

    raw_payload = await request.json()
    payload = RegisterPayload(**raw_payload)
    try:
        user = await link_username_password_account(
            prisma, linked_user_id, payload.username, payload.password
        )
    except UsernameAlreadyInUseException:
        return json_response({"error": "Username already in use"}, status=409)
    except CredentialsProviderAlreadyLinkedError as exc:
        return json_response({"error": str(exc)}, status=409)
    except ValueError as exc:
        return json_response({"error": str(exc)}, status=404)

    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    return set_cookie_and_redirect(HTTPOk(), access_token, refresh_token)