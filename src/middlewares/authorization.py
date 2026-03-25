from aiohttp import web
from aiohttp.web import StreamResponse
from aiohttp.web_request import Request
from typing import Awaitable, Callable

from src.settings import settings


def require_auth(handler: Callable[[Request], Awaitable[StreamResponse]]):
    async def wrapper(request: Request):
        token = request.headers.get("X-Api-Key")

        if token != settings.api_token:
            raise web.HTTPUnauthorized()

        return await handler(request)

    return wrapper