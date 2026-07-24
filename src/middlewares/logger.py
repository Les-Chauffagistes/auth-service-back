from aiohttp.web import middleware, StreamResponse
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_request import Request
from typing import Awaitable, Callable


@middleware
async def error_handler(request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]) -> StreamResponse:
    import init as hs_init
    log = hs_init.log
    method = request.method
    match method:
        case "GET":
            log_request = log.get

        case "POST":
            log_request = log.post

        case "DELETE":
            log_request = log.delete

        case _:
            log_request = lambda *content: log.info(method, *content)

    status = None
    try:
        response = await handler(request)
        status = response.status
        return response

    except HTTPException as e:
        status = e.status_code
        log.error("Request error")
        raise

    finally:
        log_request(request.path, status if status is not None else "ERROR")