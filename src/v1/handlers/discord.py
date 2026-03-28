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


@routes.get("/auth/discord")
async def discord_login(request: Request):
    return HTTPFound("")

@routes.get("/auth/discord/callback")
async def discord_callback(request: Request):
    raise NotImplemented

