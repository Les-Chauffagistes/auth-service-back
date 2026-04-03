from src.database.prisma import close_prisma, init_prisma
from src.middlewares.logger import error_handler
from src.middlewares.cors import cors_middleware
from src.modules import logger
from aiohttp.web import Application, RouteTableDef

log = logger.Logger("output.log")

app = Application(
    middlewares=(error_handler,cors_middleware)
)

app.on_startup.append(init_prisma) # enregistre prisma dans app["prisma"]
app.on_cleanup.append(close_prisma)
routes = RouteTableDef()