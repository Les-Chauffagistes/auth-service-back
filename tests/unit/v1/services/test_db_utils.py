from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from prisma.errors import UniqueViolationError
from src.v1.services.db_utils import create_with_sequence_repair


def _unique_violation(target: list[str]) -> UniqueViolationError:
    return UniqueViolationError({"user_facing_error": {"message": "boom", "meta": {"target": target}}})


@pytest.mark.asyncio
async def test_create_with_sequence_repair_returns_result_on_first_success():
    db = SimpleNamespace(execute_raw=AsyncMock())
    create = AsyncMock(return_value="created")

    result = await create_with_sequence_repair(db, "users", create)

    assert result == "created"
    create.assert_awaited_once()
    db.execute_raw.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_with_sequence_repair_resyncs_sequence_and_retries_on_id_collision():
    db = SimpleNamespace(execute_raw=AsyncMock())
    create = AsyncMock(side_effect=[_unique_violation(["id"]), "created"])

    result = await create_with_sequence_repair(db, "users", create)

    assert result == "created"
    assert create.await_count == 2
    db.execute_raw.assert_awaited_once()
    (query,), _ = db.execute_raw.call_args
    assert "users" in query
    assert "setval" in query


@pytest.mark.asyncio
async def test_create_with_sequence_repair_reraises_when_collision_is_not_on_id():
    db = SimpleNamespace(execute_raw=AsyncMock())
    error = _unique_violation(["username"])
    create = AsyncMock(side_effect=error)

    with pytest.raises(UniqueViolationError):
        await create_with_sequence_repair(db, "password_users", create)

    create.assert_awaited_once()
    db.execute_raw.assert_not_awaited()
