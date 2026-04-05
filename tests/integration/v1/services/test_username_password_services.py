import pytest

from src.v1.excpetions import UnkownUserExpcetion, UsernameAlreadyInUseException, WrongCredentialsException
from src.v1.services.username_password.login import login_with_username_password
from src.v1.services.username_password.register import create_username_password_account


@pytest.mark.asyncio
async def test_create_username_password_account_persists_user_and_password_account(prisma_tx):
    user = await create_username_password_account(prisma_tx, "integration-alice", "secret")

    assert user.pseudo == "integration-alice"

    password_account = await prisma_tx.password_users.find_unique(
        where={"username": "integration-alice"},
        include={"users": True},
    )
    assert password_account is not None
    assert password_account.users is not None
    assert password_account.users.id == user.id


@pytest.mark.asyncio
async def test_create_username_password_account_rejects_duplicate_username(prisma_tx):
    await create_username_password_account(prisma_tx, "duplicate-alice", "secret")

    with pytest.raises(UsernameAlreadyInUseException):
        await create_username_password_account(prisma_tx, "duplicate-alice", "other-secret")


@pytest.mark.asyncio
async def test_login_with_username_password_returns_user_when_credentials_are_valid(prisma_tx):
    created_user = await create_username_password_account(prisma_tx, "login-alice", "secret")

    user = await login_with_username_password(prisma_tx, "login-alice", "secret")

    assert user.id == created_user.id
    assert user.pseudo == "login-alice"


@pytest.mark.asyncio
async def test_login_with_username_password_raises_for_wrong_password(prisma_tx):
    await create_username_password_account(prisma_tx, "wrong-password-alice", "secret")

    with pytest.raises(WrongCredentialsException):
        await login_with_username_password(prisma_tx, "wrong-password-alice", "bad-secret")


@pytest.mark.asyncio
async def test_login_with_username_password_raises_for_unknown_user(prisma_tx):
    with pytest.raises(UnkownUserExpcetion):
        await login_with_username_password(prisma_tx, "unknown-alice", "secret")
