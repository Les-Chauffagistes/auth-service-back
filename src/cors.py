import aiohttp_cors
from init import app

cors = aiohttp_cors.setup(
    app,
    defaults={
        "https://premium.chauffagistes-btc.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        ),
        "https://premium.swakraft.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        ),
        "https://heatboard.chauffagistes-btc.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        ),
    }
)