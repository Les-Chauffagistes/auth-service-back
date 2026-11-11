import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.v1.handlers import lightning
from src.v1.handlers.login import complete_lightning_onboarding


@pytest.mark.asyncio
async def test_complete_onboarding_is_rejected():
    response = await complete_lightning_onboarding(SimpleNamespace())

    assert response.status == 403


@pytest.mark.asyncio
async def test_verify_code_rejects_unknown_key_with_403():
    prisma = SimpleNamespace(ln_users=SimpleNamespace(find_first=AsyncMock(return_value=None)))
    challenge = SimpleNamespace(user_id=None)

    response = await lightning._resolve_verify_code(prisma, challenge, "02" + "ab" * 32)

    assert response.status == 403
    assert json.loads(response.body)["reason"] == lightning.SIGNUP_DISABLED_REASON


@pytest.mark.asyncio
async def test_verify_code_still_logs_in_existing_key():
    user = SimpleNamespace(id=42)
    prisma = SimpleNamespace(
        ln_users=SimpleNamespace(find_first=AsyncMock(return_value=SimpleNamespace(users=user)))
    )

    code = await lightning._resolve_verify_code(prisma, SimpleNamespace(user_id=None), "02" + "ab" * 32)

    assert isinstance(code, str)
