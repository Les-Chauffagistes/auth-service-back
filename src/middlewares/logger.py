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
            line = log.get(request.path)
        
        case "POST":
            line = log.post(request.path)
        
        case "DELETE":
            line = log.delete(request.path)
        
        case _:
            line = log.info(request.method, request.path)
    
    assert line
    try:
        response = await handler(request)
        line.add_text("HTTP", response.status)
        line.edit_print()
        return response

    except HTTPException as e:
        line.add_text("HTTP", e.status_code)
        line.edit_print()
        log.error("Request error")
        raise