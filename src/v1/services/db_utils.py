from typing import Awaitable, Callable, TypeVar

from prisma import Prisma
from prisma.errors import UniqueViolationError

T = TypeVar("T")


async def create_with_sequence_repair(db: Prisma, table: str, create: Callable[[], Awaitable[T]]) -> T:
    """Run a Prisma `.create()` on an autoincrement `id` table, self-healing once if the
    underlying sequence has fallen behind the table's data.

    This happened in staging: bulk-loaded rows landed with explicit ids without advancing
    the sequence, so every subsequent insert collided with an existing id until the
    sequence caught up on its own. Resyncing on the first collision fixes it immediately
    instead of failing requests until enough attempts happen to skip past the gap.
    """
    try:
        return await create()
    except UniqueViolationError as exc:
        target = (exc.meta or {}).get("target") or []
        if "id" not in target:
            raise

        await db.execute_raw(
            f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), "
            f'COALESCE((SELECT MAX(id) FROM "{table}"), 1))'
        )
        return await create()
