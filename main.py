from init import routes, app, log
from src.settings import settings
from aiohttp import web
from asyncio import new_event_loop, set_event_loop, Future


async def main():
    log.info("Démarrage du serveur...")
    
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", settings.server_port)
    await site.start()
    log.info(f"Serveur interne en ligne sur localhost:{settings.server_port}")

    await Future()


if __name__ == "__main__":
    from src import v1, health

    from src.v1.app import routes as v1_routes
    app.add_routes(routes)
    app.add_routes(v1_routes)
    paths = []
    # for route in app.router.routes():
    #     log.info("added cors on", route.method, route.resource.canonical)
    #     cors.add(route)

    loop = new_event_loop()
    set_event_loop(loop)
    try:
        loop.run_until_complete(main())

    except KeyboardInterrupt:
        log.info("Bye")
        exit(0)
