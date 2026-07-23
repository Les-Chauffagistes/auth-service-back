from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock

import pytest

from src.v1.services.discord.login import (
    DiscordProviderAlreadyLinkedError,
    DiscordOAuthError,
    _fetch_discord_identity,
    _fetch_discord_token,
    build_discord_authorize_url,
    decode_state,
    encode_state,
    handle_link,
    handle_login,
)


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def json(self, content_type=None):
        return self._payload


class _FakeSession:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []

    def post(self, *args, **kwargs):
        self.post_calls.append({"args": args, "kwargs": kwargs})
        return self.response

    def get(self, *args, **kwargs):
        self.get_calls.append({"args": args, "kwargs": kwargs})
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_encode_state_and_decode_state_are_inverse_operations():
    state = {"redirect": "/dashboard", "nonce": "abc"}

    encoded = encode_state(state)

    assert decode_state(encoded) == state


def test_build_discord_authorize_url_contains_expected_query_params():
    url = build_discord_authorize_url("opaque-state")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "discord.com"
    assert parsed.path == "/oauth2/authorize"
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["identify"]
    assert query["state"] == ["opaque-state"]
    assert "client_id" in query
    assert "redirect_uri" in query


@pytest.mark.asyncio
async def test_fetch_discord_token_returns_access_token(monkeypatch: pytest.MonkeyPatch):
    session = _FakeSession(_FakeResponse(200, {"access_token": "token-123"}))
    monkeypatch.setattr("src.v1.services.discord.login.ClientSession", lambda: session)

    token = await _fetch_discord_token("oauth-code")

    assert token == "token-123"
    assert len(session.post_calls) == 1


@pytest.mark.asyncio
async def test_fetch_discord_token_raises_on_non_200(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.v1.services.discord.login.ClientSession",
        lambda: _FakeSession(_FakeResponse(401, {"error_description": "bad code"})),
    )

    with pytest.raises(DiscordOAuthError, match="bad code"):
        await _fetch_discord_token("oauth-code")


@pytest.mark.asyncio
async def test_fetch_discord_identity_returns_identity(monkeypatch: pytest.MonkeyPatch):
    session = _FakeSession(_FakeResponse(200, {"id": "123", "username": "alice"}))
    monkeypatch.setattr("src.v1.services.discord.login.ClientSession", lambda: session)

    identity = await _fetch_discord_identity("token-123")

    assert identity == {"id": "123", "username": "alice"}
    assert len(session.get_calls) == 1


@pytest.mark.asyncio
async def test_fetch_discord_identity_raises_when_payload_is_incomplete(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.v1.services.discord.login.ClientSession",
        lambda: _FakeSession(_FakeResponse(200, {"id": "123"})),
    )

    with pytest.raises(DiscordOAuthError, match="unable to fetch Discord identity"):
        await _fetch_discord_identity("token-123")


@pytest.mark.asyncio
async def test_handle_login_creates_user_and_discord_account_for_new_identity(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=10, pseudo="alice")
    discord_account = SimpleNamespace(users=user)
    db = SimpleNamespace(
        users=SimpleNamespace(create=AsyncMock(return_value=user)),
        discord_users=SimpleNamespace(
            find_unique=AsyncMock(return_value=None),
            create=AsyncMock(return_value=discord_account),
            update=AsyncMock(),
        ),
    )
    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", AsyncMock(return_value="token-123"))
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        AsyncMock(return_value={"id": "123", "username": "alice"}),
    )

    result = await handle_login(db, "oauth-code")

    assert result is user
    db.users.create.assert_awaited_once_with(data={"pseudo": "alice"})
    db.discord_users.create.assert_awaited_once_with(
        data={"id": "123", "discord_name": "alice", "user_id": 10},
        include={"users": True},
    )
    db.discord_users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_login_updates_existing_discord_account(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=10, pseudo="alice")
    existing_account = SimpleNamespace(users=user)
    updated_account = SimpleNamespace(users=user)
    db = SimpleNamespace(
        users=SimpleNamespace(create=AsyncMock()),
        discord_users=SimpleNamespace(
            find_unique=AsyncMock(return_value=existing_account),
            create=AsyncMock(),
            update=AsyncMock(return_value=updated_account),
        ),
    )
    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", AsyncMock(return_value="token-123"))
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        AsyncMock(return_value={"id": "123", "username": "alice-renamed"}),
    )

    result = await handle_login(db, "oauth-code")

    assert result is user
    db.users.create.assert_not_awaited()
    db.discord_users.create.assert_not_awaited()
    db.discord_users.update.assert_awaited_once_with(
        where={"id": "123"},
        data={"discord_name": "alice-renamed"},
        include={"users": True},
    )


@pytest.mark.asyncio
async def test_handle_link_creates_discord_link_for_target_user(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=7, pseudo="target")
    db = SimpleNamespace(
        users=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        discord_users=SimpleNamespace(
            find_unique=AsyncMock(return_value=None),
            create=AsyncMock(),
            update=AsyncMock(),
        ),
    )
    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", AsyncMock(return_value="token-123"))
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        AsyncMock(return_value={"id": "discord-777", "username": "alice"}),
    )

    result = await handle_link(db, "oauth-code", user.id)

    assert result is user
    db.discord_users.create.assert_awaited_once_with(
        data={"id": "discord-777", "discord_name": "alice", "user_id": 7}
    )
    db.discord_users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_link_raises_conflict_when_discord_is_already_linked_elsewhere(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=7, pseudo="target")
    existing = SimpleNamespace(user_id=99)
    db = SimpleNamespace(
        users=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        discord_users=SimpleNamespace(
            find_unique=AsyncMock(return_value=existing),
            create=AsyncMock(),
            update=AsyncMock(),
        ),
    )
    monkeypatch.setattr("src.v1.services.discord.login._fetch_discord_token", AsyncMock(return_value="token-123"))
    monkeypatch.setattr(
        "src.v1.services.discord.login._fetch_discord_identity",
        AsyncMock(return_value={"id": "discord-777", "username": "alice"}),
    )

    with pytest.raises(DiscordProviderAlreadyLinkedError):
        await handle_link(db, "oauth-code", user.id)
