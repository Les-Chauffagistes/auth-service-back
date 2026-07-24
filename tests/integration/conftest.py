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


def _run_docker_command(*args: str) -> str:
    try:
        result = subprocess.run(
            ["docker", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return f"$ docker {' '.join(args)}\nexit=n/a\ndocker executable was not found.\n"

    output = "\n".join(
        part for part in [result.stdout.strip(), result.stderr.strip()] if part
    )
    return f"$ docker {' '.join(args)}\nexit={result.returncode}\n{output}\n"


def _extract_testcontainer_id(postgres: PostgresContainer) -> str | None:
    container = getattr(postgres, "_container", None)
    if container is None:
        return None

    container_id = getattr(container, "id", None)
    if container_id is None:
        return None

    return str(container_id)


def _collect_startup_diagnostics(postgres: PostgresContainer) -> str:
    container_id = _extract_testcontainer_id(postgres)
    diagnostics = [
        "Postgres Testcontainers startup diagnostics:",
        f"image={POSTGRES_IMAGE}",
        _run_docker_command("ps", "-a", "--no-trunc"),
    ]

    if container_id is not None:
        diagnostics.extend(
            [
                f"container_id={container_id}",
                _run_docker_command("inspect", container_id),
                _run_docker_command("logs", container_id),
            ]
        )
    else:
        diagnostics.append("container_id=<unavailable>")

    return "\n".join(diagnostics)


@pytest.fixture(scope="session")
def postgres_database_url():
    previous_database_url = os.environ.get("DATABASE_URL")
    postgres = PostgresContainer(
        POSTGRES_IMAGE,
        username="postgres",
        password="postgres",
        dbname="auth_test",
        driver=None,
    )
    started = False

    try:
        try:
            postgres.start()
            started = True
        except Exception as exc:
            diagnostics = _collect_startup_diagnostics(postgres)
            raise RuntimeError(
                "Unable to start the Postgres test container.\n"
                f"{diagnostics}"
            ) from exc

        database_url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = database_url
        _apply_prisma_schema(database_url)
        yield database_url
    finally:
        if started:
            postgres.stop()

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
