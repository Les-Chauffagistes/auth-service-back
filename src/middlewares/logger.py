from aiohttp.web import middleware, StreamResponse
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_request import Request
from typing import Awaitable, Callable


@middleware
async def error_handler(request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]) -> StreamResponse:
    import init as hs_init
    log = hs_init.log
    method = request.method

    status = None
    try:
        response = await handler(request)
        status = response.status
        return response

    except HTTPException as e:
        status = e.status_code
        log.exception("Request error")
        raise

    finally:
        log.info(f"{method} {request.path} {status if status is not None else 'ERROR'}")