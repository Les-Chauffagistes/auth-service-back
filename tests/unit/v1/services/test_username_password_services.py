from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.v1.excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from src.v1.services.username_password.login import login_with_username_password
from src.v1.services.username_password.register import create_username_password_account
from src.v1.services.username_password.utils import check_account_exists, hash_password, verify_password


@pytest.mark.asyncio
async def test_login_with_username_password_raises_when_user_is_unknown():
    prisma = SimpleNamespace(
        password_users=SimpleNamespace(find_first=AsyncMock(return_value=None)),
    )

    with pytest.raises(UnkownUserExpcetion):
        await login_with_username_password(prisma, "alice", "secret")


@pytest.mark.asyncio
async def test_login_with_username_password_raises_when_password_is_invalid(monkeypatch: pytest.MonkeyPatch):
    account = SimpleNamespace(password="stored-hash", users=SimpleNamespace(id=1, pseudo="alice"))
    prisma = SimpleNamespace(
        password_users=SimpleNamespace(find_first=AsyncMock(return_value=account)),
    )
    monkeypatch.setattr(
        "src.v1.services.username_password.login.verify_password",
        AsyncMock(return_value=False),
    )

    with pytest.raises(WrongCredentialsException):
        await login_with_username_password(prisma, "alice", "bad-secret")


@pytest.mark.asyncio
async def test_login_with_username_password_returns_user_on_success(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=1, pseudo="alice")
    account = SimpleNamespace(password="stored-hash", users=user)
    prisma = SimpleNamespace(
        password_users=SimpleNamespace(find_first=AsyncMock(return_value=account)),
    )
    monkeypatch.setattr(
        "src.v1.services.username_password.login.verify_password",
        AsyncMock(return_value=True),
    )

    result = await login_with_username_password(prisma, "alice", "secret")

    assert result is user


@pytest.mark.asyncio
async def test_create_username_password_account_raises_when_username_is_already_used(monkeypatch: pytest.MonkeyPatch):
    prisma = SimpleNamespace(
        users=SimpleNamespace(create=AsyncMock()),
        password_users=SimpleNamespace(create=AsyncMock()),
    )
    monkeypatch.setattr(
        "src.v1.services.username_password.register.check_account_exists",
        AsyncMock(return_value=True),
    )

    with pytest.raises(UsernameAlreadyInUseException):
        await create_username_password_account(prisma, "alice", "secret")

    prisma.users.create.assert_not_awaited()
    prisma.password_users.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_username_password_account_persists_user_and_password_account(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=42, pseudo="alice")
    prisma = SimpleNamespace(
        users=SimpleNamespace(create=AsyncMock(return_value=user)),
        password_users=SimpleNamespace(create=AsyncMock()),
    )
    monkeypatch.setattr(
        "src.v1.services.username_password.register.check_account_exists",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "src.v1.services.username_password.register.hash_password",
        AsyncMock(return_value="hashed-secret"),
    )

    result = await create_username_password_account(prisma, "alice", "secret")

    assert result is user
    prisma.users.create.assert_awaited_once_with(data={"pseudo": "alice"})
    prisma.password_users.create.assert_awaited_once_with(
        data={"username": "alice", "password": "hashed-secret", "user_id": 42},
    )


@pytest.mark.asyncio
async def test_check_account_exists_returns_true_when_prisma_finds_a_match():
    prisma = SimpleNamespace(
        password_users=SimpleNamespace(find_first=AsyncMock(return_value=object())),
    )

    assert await check_account_exists(prisma, "alice") is True


@pytest.mark.asyncio
async def test_check_account_exists_returns_false_when_prisma_returns_none():
    prisma = SimpleNamespace(
        password_users=SimpleNamespace(find_first=AsyncMock(return_value=None)),
    )

    assert await check_account_exists(prisma, "alice") is False


@pytest.mark.asyncio
async def test_hash_password_and_verify_password_round_trip():
    hashed = await hash_password("secret")

    assert hashed != "secret"
    assert isinstance(hashed, str)
    assert await verify_password("secret", hashed) is True
    assert await verify_password("wrong-secret", hashed) is False
