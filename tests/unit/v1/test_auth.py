from types import SimpleNamespace

import jwt

from src.v1.auth import resolve_authenticated_user_id


def test_resolve_authenticated_user_id_returns_none_when_cookie_is_missing():
    request = SimpleNamespace(cookies={})

    assert resolve_authenticated_user_id(request) is None


def test_resolve_authenticated_user_id_returns_none_when_token_is_invalid(monkeypatch):
    request = SimpleNamespace(cookies={"access_token": "bad-token"})

    def _raise_invalid(_: str):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr("src.v1.auth.decode_access_token", _raise_invalid)

    assert resolve_authenticated_user_id(request) is None


def test_resolve_authenticated_user_id_returns_none_when_sub_is_not_an_int(monkeypatch):
    request = SimpleNamespace(cookies={"access_token": "token"})
    monkeypatch.setattr("src.v1.auth.decode_access_token", lambda _: {"sub": "abc"})

    assert resolve_authenticated_user_id(request) is None


def test_resolve_authenticated_user_id_returns_int_user_id(monkeypatch):
    request = SimpleNamespace(cookies={"access_token": "token"})
    monkeypatch.setattr("src.v1.auth.decode_access_token", lambda _: {"sub": "42"})

    assert resolve_authenticated_user_id(request) == 42
