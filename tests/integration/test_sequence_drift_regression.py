"""Regression coverage for the staging incident where linking a provider crashed with
`UniqueViolationError: Unique constraint failed on the fields: (id)`.

Root cause: the `users`/`ln_users`/`password_users` autoincrement sequences had fallen
behind the tables' actual data (rows landed with explicit ids without advancing the
sequence), so the next Prisma-issued insert collided with an existing row.

The rest of the integration suite builds its database with `prisma db push`, which always
creates fresh, in-sync sequences — it structurally cannot reproduce this class of drift.
This module instead applies the real, committed migration history with
`prisma migrate deploy`, then manually desyncs a sequence the same way the staging
incident did, to prove the fix holds against the actual deploy path.
"""

import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
from prisma import Prisma
from testcontainers.postgres import PostgresContainer

from tests.integration.conftest import POSTGRES_IMAGE, _resolve_prisma_cli
from src.v1.services.username_password.register import (
    create_username_password_account,
    link_username_password_account,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _migrate_deploy(database_url: str) -> None:
    result = subprocess.run(
        [_resolve_prisma_cli(), "migrate", "deploy", "--schema", str(PROJECT_ROOT / "prisma" / "schema.prisma")],
        cwd=PROJECT_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"prisma migrate deploy failed:\n{details}")


@pytest_asyncio.fixture
async def migrated_prisma():
    postgres = PostgresContainer(
        POSTGRES_IMAGE,
        username="postgres",
        password="postgres",
        dbname="auth_migration_test",
        driver=None,
    )
    postgres.start()
    try:
        database_url = postgres.get_connection_url()
        _migrate_deploy(database_url)

        prisma = Prisma(datasource={"url": database_url})
        await prisma.connect()
        try:
            yield prisma
        finally:
            await prisma.disconnect()
    finally:
        postgres.stop()


async def _desync_sequence_like_a_bulk_load(prisma: Prisma, table: str, explicit_id: int) -> None:
    """Insert a row with an explicit id, exactly as a bulk data load into staging did,
    then pin the table's id sequence one step behind it — so the very next
    Prisma-issued, default-id insert is guaranteed to collide with this row, exactly
    like the staging incident."""
    if table == "users":
        await prisma.execute_raw(
            f'INSERT INTO "{table}" (id, pseudo) VALUES ({explicit_id}, \'bulk-loaded\')'
        )
    else:
        raise NotImplementedError(table)

    await prisma.execute_raw(
        f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), {explicit_id - 1})"
    )


@pytest.mark.asyncio
async def test_migrations_apply_cleanly_from_scratch(migrated_prisma: Prisma):
    # If this fails, `prisma/schema.prisma` has drifted from the committed migration
    # history (e.g. a field was hand-edited without generating a migration for it).
    ln_user = await migrated_prisma.ln_users.create(data={"ln_key": "same-key"})
    with pytest.raises(Exception):
        await migrated_prisma.ln_users.create(data={"ln_key": "same-key"})
    assert ln_user.ln_key == "same-key"


@pytest.mark.asyncio
async def test_registering_a_new_account_survives_a_desynced_users_sequence(migrated_prisma: Prisma):
    await _desync_sequence_like_a_bulk_load(migrated_prisma, "users", explicit_id=9999)

    user = await create_username_password_account(migrated_prisma, "post-bulk-load-user", "secret")

    assert user.pseudo == "post-bulk-load-user"


@pytest.mark.asyncio
async def test_linking_credentials_survives_a_desynced_password_users_sequence(migrated_prisma: Prisma):
    user = await migrated_prisma.users.create(data={"pseudo": "existing-user"})

    # Simulate the exact staging failure: a password_users row lands with an explicit id
    # ahead of the sequence (e.g. copied in alongside a bulk load of other accounts), and
    # the sequence is pinned one step behind it so the next insert is guaranteed to collide.
    await migrated_prisma.execute_raw(
        'INSERT INTO "password_users" (id, username, password, user_id) '
        "VALUES (9999, 'bulk-loaded-account', 'hash', $1)",
        user.id,
    )
    await migrated_prisma.execute_raw(
        "SELECT setval(pg_get_serial_sequence('\"password_users\"', 'id'), 9998)"
    )

    other_user = await migrated_prisma.users.create(data={"pseudo": "linker"})

    linked = await link_username_password_account(migrated_prisma, other_user.id, "fresh-username", "secret")

    assert linked.id == other_user.id
