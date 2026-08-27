from os import getenv
from src.database.prisma import close_prisma, init_prisma
from src.middlewares.logger import error_handler
from src.middlewares.cors import cors_middleware
from chauff_cmn.logging import configure, logger as log
from aiohttp.web import Application, RouteTableDef

configure(service="auth-service-back", level=getenv("LOG_LEVEL", "DEBUG"))

app = Application(
    middlewares=(cors_middleware, error_handler)
)

app.on_startup.append(init_prisma) # enregistre prisma dans app["prisma"]
app.on_cleanup.append(close_prisma)
routes = RouteTableDef()