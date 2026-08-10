from dotenv import load_dotenv

load_dotenv(".env")

from init import routes, app, log
from src.settings import settings
from aiohttp import web


def main():
    log.info("Démarrage du serveur...")

    web.run_app(
        app,
        host="0.0.0.0",
        port=settings.server_port,
        print=log.info,
    )


if __name__ == "__main__":
    from src import v1, health

    from src.v1.app import routes as v1_routes
    app.add_routes(routes)
    app.add_routes(v1_routes)
    main()
