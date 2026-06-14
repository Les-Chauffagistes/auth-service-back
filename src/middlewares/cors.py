from aiohttp.web import middleware, StreamResponse, Response
from aiohttp.web_request import Request
from typing import Awaitable, Callable


@middleware
async def cors_middleware(request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]) -> StreamResponse:
    if request.method == "OPTIONS":
        response = Response(status=200)
    else:
        response = await handler(request)

    origin = request.headers.get("Origin")

    if origin in [
        "https://auth.staging.chauffagistes-btc.fr",
        "https://auth.chauffagistes-btc.fr",
        "https://contenders.staging.chauffagistes-btc.fr",
        "https://contenders.chauffagistes-btc.fr"
    ]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, DELETE"

    return response