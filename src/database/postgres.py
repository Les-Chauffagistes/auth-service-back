import json, os
from asyncpg import Connection, Pool, create_pool
from aiohttp.web import Application


class PoolProvider:
    def __init__(self, pool: Pool | None):
        self.pool = pool

    def get(self):
        if not self.pool:
            raise RuntimeError("Pool not initialized")
        return self.pool

    def set(self, pool: Pool):
        self.pool = pool


POOL = PoolProvider(None)


async def create_db_pool(_app: Application):
    """Créer le pool de connexions au démarrage"""
    # importer paresseusement le logger central pour éviter les importations circulaires

    pool = await create_pool(
        user=os.getenv("POSTGRE_USER"),
        password=os.getenv("POSTGRE_PASSWORD"),
        database="chauffagistes",
        host=os.getenv("POSTGRE_HOST"),
        port=os.getenv("POSTGRE_PORT"),
        min_size=1,
        max_size=20,
        command_timeout=60,
        max_queries=50000,
        max_inactive_connection_lifetime=300,
        setup=setup_connection,
    )
    POOL.set(pool)


async def setup_connection(conn: Connection):
    """Configurer chaque connexion du pool"""
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def close_db_pool(_app: Application):
    """Fermer le pool à l'arrêt"""
    await POOL.get().close()
