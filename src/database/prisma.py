from prisma import Prisma
from aiohttp import web

async def init_prisma(app: web.Application):
    from init import log
    log.info("Prisma ready")
    prisma = Prisma()
    await prisma.connect()
    app["prisma"] = prisma

async def close_prisma(app: web.Application):
    await app["prisma"].disconnect()