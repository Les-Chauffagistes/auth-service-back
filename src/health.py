from init import routes
from aiohttp.web_request import Request
from aiohttp.web import HTTPOk

@routes.get("/health")
async def health(_: Request):
    return HTTPOk()