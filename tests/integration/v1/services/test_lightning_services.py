import pytest

from src.v1.services.lightning.login import authenticate_with_lightning, create_challenge


@pytest.mark.asyncio
async def test_create_challenge_persists_pending_challenge(prisma_tx, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.v1.services.lightning.login.urandom", lambda _: b"\x22" * 32)
    monkeypatch.setattr("src.v1.services.lightning.login.encode_lnurl", lambda value: f"encoded::{value}")

    payload = await create_challenge(prisma_tx)

    expected_k1 = "22" * 32
    assert payload["k1"] == expected_k1
    assert payload["lnurl"].endswith(f"k1={expected_k1}&tag=login")
    challenge = await prisma_tx.lnurl_auth.find_unique(where={"k1": expected_k1})
    assert challenge is not None
    assert challenge.status == "pending"


@pytest.mark.asyncio
async def test_authenticate_with_lightning_returns_onboarding_for_unknown_key(prisma_tx):
    kind, data = await authenticate_with_lightning(prisma_tx, "ln-pubkey-new")

    assert kind == "onboarding"
    assert data == "ln-pubkey-new"

    ln_account = await prisma_tx.ln_users.find_first(where={"ln_key": "ln-pubkey-new"})
    assert ln_account is None


@pytest.mark.asyncio
async def test_authenticate_with_lightning_returns_login_for_existing_key(prisma_tx):
    user = await prisma_tx.users.create(data={"pseudo": "satoshi"})
    await prisma_tx.ln_users.create(data={"ln_key": "ln-pubkey-existing", "user_id": user.id})

    kind, data = await authenticate_with_lightning(prisma_tx, "ln-pubkey-existing")

    assert kind == "login"
    assert data.id == user.id


@pytest.mark.asyncio
async def test_authenticate_with_lightning_does_not_duplicate_ln_account(prisma_tx):
    user = await prisma_tx.users.create(data={"pseudo": "satoshi2"})
    await prisma_tx.ln_users.create(data={"ln_key": "ln-pubkey-dup", "user_id": user.id})

    await authenticate_with_lightning(prisma_tx, "ln-pubkey-dup")
    await authenticate_with_lightning(prisma_tx, "ln-pubkey-dup")

    ln_accounts = await prisma_tx.ln_users.find_many(where={"ln_key": "ln-pubkey-dup"})
    assert len(ln_accounts) == 1
