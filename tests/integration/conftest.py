import os
import subprocess
import sys
from pathlib import Path
from shutil import which

import pytest
import pytest_asyncio
from prisma import Prisma
from testcontainers.postgres import PostgresContainer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "postgres:18.1-alpine3.23"


def _resolve_prisma_cli() -> str:
    prisma = which("prisma")
    if prisma:
        return prisma

    candidates = [
        Path(sys.executable).resolve().parent / "prisma",
        PROJECT_ROOT / "venv" / "bin" / "prisma",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "Unable to locate the Prisma CLI. Expected it in PATH or venv/bin/prisma."
    )


def _apply_prisma_schema(database_url: str) -> None:
    result = subprocess.run(
        [
            _resolve_prisma_cli(),
            "db",
            "push",
            "--skip-generate",
            "--schema",
            str(PROJECT_ROOT / "prisma" / "schema.prisma"),
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to apply the Prisma test schema:\n{details}")


@pytest.fixture(scope="session")
def postgres_database_url():
    previous_database_url = os.environ.get("DATABASE_URL")
    try:
        with PostgresContainer(
            POSTGRES_IMAGE,
            username="postgres",
            password="postgres",
            dbname="auth_test",
            driver=None,
        ) as postgres:
            database_url = postgres.get_connection_url()
            os.environ["DATABASE_URL"] = database_url
            _apply_prisma_schema(database_url)
            yield database_url
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def prisma_client(postgres_database_url: str):
    prisma = Prisma(datasource={"url": postgres_database_url})
    await prisma.connect()
    try:
        yield prisma
    finally:
        await prisma.disconnect()


@pytest_asyncio.fixture
async def prisma_tx(prisma_client: Prisma):
    transaction_manager = prisma_client.tx()
    transaction = await transaction_manager.start()
    try:
        yield transaction
    finally:
        await transaction_manager.rollback()
