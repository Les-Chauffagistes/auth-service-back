import pytest

from src.v1.services.discord.login import DiscordProviderAlreadyLinkedError, handle_link, handle_login


@pytest.mark.asyncio
async def test_handle_login_creates_discord_user_on_first_login(prisma_tx, monkeypatch: pytest.MonkeyPatch):
    async def fake_fetch_token(code: str) -> str:
        return "token-123"

    async def fake_fetch_identity(token: str) -> dict:
        return {"id": "discord-1", "username": "discord-alice"}

    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", fake_fetch_token)
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        fake_fetch_identity,
    )

    user = await handle_login(prisma_tx, "oauth-code")

    assert user.pseudo == "discord-alice"
    discord_account = await prisma_tx.discord_users.find_unique(
        where={"id": "discord-1"},
        include={"users": True},
    )
    assert discord_account is not None
    assert discord_account.discord_name == "discord-alice"
    assert discord_account.users is not None
    assert discord_account.users.id == user.id


@pytest.mark.asyncio
async def test_handle_login_updates_existing_discord_name(prisma_tx, monkeypatch: pytest.MonkeyPatch):
    async def fake_fetch_token(code: str) -> str:
        return "token-123"

    async def fake_fetch_identity_first(token: str) -> dict:
        return {"id": "discord-rename", "username": "first-name"}

    async def fake_fetch_identity_second(token: str) -> dict:
        return {"id": "discord-rename", "username": "second-name"}

    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", fake_fetch_token)
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        fake_fetch_identity_first,
    )
    user = await handle_login(prisma_tx, "oauth-code")

    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        fake_fetch_identity_second,
    )
    same_user = await handle_login(prisma_tx, "oauth-code")

    assert same_user.id == user.id
    discord_account = await prisma_tx.discord_users.find_unique(
        where={"id": "discord-rename"},
        include={"users": True},
    )
    assert discord_account is not None
    assert discord_account.discord_name == "second-name"


@pytest.mark.asyncio
async def test_handle_link_attaches_discord_account_to_existing_user(prisma_tx, monkeypatch: pytest.MonkeyPatch):
    user = await prisma_tx.users.create(data={"pseudo": "linked-user"})

    async def fake_fetch_token(code: str) -> str:
        return "token-123"

    async def fake_fetch_identity(token: str) -> dict:
        return {"id": "discord-link", "username": "linked-name"}

    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", fake_fetch_token)
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        fake_fetch_identity,
    )

    result = await handle_link(prisma_tx, "oauth-code", user.id)

    assert result.id == user.id
    discord_account = await prisma_tx.discord_users.find_unique(where={"id": "discord-link"})
    assert discord_account is not None
    assert discord_account.user_id == user.id


@pytest.mark.asyncio
async def test_handle_link_rejects_when_discord_is_linked_to_another_user(prisma_tx, monkeypatch: pytest.MonkeyPatch):
    user_a = await prisma_tx.users.create(data={"pseudo": "a"})
    user_b = await prisma_tx.users.create(data={"pseudo": "b"})
    await prisma_tx.discord_users.create(
        data={"id": "discord-linked", "discord_name": "name", "user_id": user_a.id}
    )

    async def fake_fetch_token(code: str) -> str:
        return "token-123"

    async def fake_fetch_identity(token: str) -> dict:
        return {"id": "discord-linked", "username": "linked-name"}

    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", fake_fetch_token)
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        fake_fetch_identity,
    )

    with pytest.raises(DiscordProviderAlreadyLinkedError):
        await handle_link(prisma_tx, "oauth-code", user_b.id)
