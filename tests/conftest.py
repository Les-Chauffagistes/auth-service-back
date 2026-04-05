from prisma import Prisma
import pytest_asyncio
import pytest
from src.modules.logger.logger import Logger
from dotenv import load_dotenv
import subprocess, os, sys
from shutil import which
from pathlib import Path
import asyncpg


load_dotenv(".env.test", override=True)
def _resolve_prisma_cli() -> str:
    prisma = which("prisma")
    if prisma:
        return prisma

    candidates = [
        Path(sys.executable).resolve().parent / "prisma",
        Path(__file__).resolve().parents[1] / "venv" / "bin" / "prisma",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "Unable to locate the Prisma CLI. Expected it in PATH or venv/bin/prisma."
    )


def _ensure_test_db():
    """Crée la BDD de test et applique le schéma Prisma si nécessaire."""
    db_url = os.environ["DATABASE_URL"]
    db_name = db_url.rsplit("/", 1)[-1].split("?")[0]
    server_url = db_url.rsplit("/", 1)[0] + "/template1"

    import asyncio

    async def _create_db():
        conn = await asyncpg.connect(server_url)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                print("creating", db_name)
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    asyncio.run(_create_db())

    subprocess.run(
        [_resolve_prisma_cli(), "db", "push", "--skip-generate"],
        env={**os.environ, "DATABASE_URL": db_url},
        check=True,
        capture_output=True,
    )


_ensure_test_db()

# NE PAS RÉUTILISER. UTILISER prisma_tx SI BESOIN DE PRISMA
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def prisma_client():
    prisma = Prisma()
    await prisma.connect()
    yield prisma
    await prisma.disconnect()

@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def seed_db(prisma_client: Prisma):
    """Purge et peuple la BDD une seule fois au début de la session de tests."""
    # Purge (ordre respectant les FK)
    await prisma_client.refresh_tokens.delete_many()
    await prisma_client.discord_users.delete_many()
    await prisma_client.password_users.delete_many()
    await prisma_client.lnurl_auth.delete_many()
    await prisma_client.ln_users.delete_many()
    await prisma_client.users.delete_many()

    yield

    # Nettoyage après tous les tests
    await prisma_client.refresh_tokens.delete_many()
    await prisma_client.discord_users.delete_many()
    await prisma_client.password_users.delete_many()
    await prisma_client.lnurl_auth.delete_many()
    await prisma_client.ln_users.delete_many()
    await prisma_client.users.delete_many()

@pytest_asyncio.fixture
async def prisma_tx(prisma_client: Prisma):
    tx =  prisma_client.tx()
    transaction = await tx.start()
    try:
        yield transaction

    finally:
        await tx.rollback()

@pytest.fixture
def log():
    log = Logger()
    yield log
