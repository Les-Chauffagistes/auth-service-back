from aiohttp.web import Application, RouteTableDef


subapp = Application()
routes = RouteTableDef()

# Import route modules here so decorators register routes without making the
# package import itself trigger handler/service imports.
from .handlers import *
