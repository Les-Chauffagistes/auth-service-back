from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.settings import settings
from src.v1.services.lightning.bech32_fallback import _convertbits, bech32_decode, bech32_encode
from src.v1.services.lightning.lnurl_codec import decode_lnurl, encode_lnurl
from src.v1.services.lightning.login import authenticate_with_lightning, create_challenge, verify_signature
from src.v1.services.lightning.login import LightningProviderAlreadyLinkedError, link_lightning_provider


@pytest.mark.asyncio
async def test_create_challenge_persists_k1_and_returns_lnurl(monkeypatch: pytest.MonkeyPatch):
    db = SimpleNamespace(
        lnurl_auth=SimpleNamespace(create=AsyncMock()),
    )
    monkeypatch.setattr("src.v1.services.lightning.login.urandom", lambda _: b"\x11" * 32)
    monkeypatch.setattr("src.v1.services.lightning.login.encode_lnurl", lambda value: f"encoded::{value}")

    payload = await create_challenge(db)

    expected_k1 = "11" * 32
    expected_url = f"{settings.lightning_callback_url}?k1={expected_k1}&tag=login"
    assert payload == {"lnurl": f"encoded::{expected_url}", "k1": expected_k1}
    db.lnurl_auth.create.assert_awaited_once_with(data={"k1": expected_k1})


@pytest.mark.asyncio
async def test_authenticate_with_lightning_returns_login_tuple_for_existing_user():
    user = SimpleNamespace(id=1, pseudo="hugo")
    account = SimpleNamespace(ln_key="pubkey", users=user)
    db = SimpleNamespace(
        ln_users=SimpleNamespace(find_first=AsyncMock(return_value=account), create=AsyncMock()),
        users=SimpleNamespace(create=AsyncMock()),
    )

    kind, data = await authenticate_with_lightning(db, "pubkey")

    assert kind == "login"
    assert data is user
    db.users.create.assert_not_awaited()
    db.ln_users.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_with_lightning_returns_onboarding_tuple_for_unknown_key():
    db = SimpleNamespace(
        ln_users=SimpleNamespace(find_first=AsyncMock(return_value=None), create=AsyncMock()),
        users=SimpleNamespace(create=AsyncMock()),
    )

    kind, data = await authenticate_with_lightning(db, "new-pubkey")

    assert kind == "onboarding"
    assert data == "new-pubkey"
    db.users.create.assert_not_awaited()
    db.ln_users.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_link_lightning_provider_creates_link_for_new_key():
    user = SimpleNamespace(id=1, pseudo="hugo")
    db = SimpleNamespace(
        users=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        ln_users=SimpleNamespace(find_first=AsyncMock(return_value=None), create=AsyncMock()),
    )

    result = await link_lightning_provider(db, user.id, "new-pubkey")

    assert result is user
    db.ln_users.create.assert_awaited_once_with(data={"ln_key": "new-pubkey", "user_id": 1})


@pytest.mark.asyncio
async def test_link_lightning_provider_raises_when_key_is_linked_elsewhere():
    user = SimpleNamespace(id=1, pseudo="hugo")
    existing = SimpleNamespace(user_id=2)
    db = SimpleNamespace(
        users=SimpleNamespace(find_unique=AsyncMock(return_value=user)),
        ln_users=SimpleNamespace(find_first=AsyncMock(return_value=existing), create=AsyncMock()),
    )

    with pytest.raises(LightningProviderAlreadyLinkedError):
        await link_lightning_provider(db, user.id, "existing-pubkey")


def test_verify_signature_raises_for_invalid_k1_length():
    with pytest.raises(ValueError, match="k1 must be 32 bytes"):
        verify_signature("aa", "304402200102", "02" + "11" * 32)


def test_verify_signature_raises_for_invalid_compressed_public_key():
    with pytest.raises(ValueError, match="compressed secp256k1 public key"):
        verify_signature("11" * 32, "304402200102", "04" + "11" * 64)


def test_encode_and_decode_lnurl_round_trip_without_pypi_bech32(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.v1.services.lightning.lnurl_codec._load_pypi_bech32", lambda: None)
    url = "https://example.com/auth/lightning/verify?k1=abc&tag=login"

    encoded = encode_lnurl(url)

    assert decode_lnurl(encoded) == url


def test_decode_lnurl_raises_when_pypi_module_returns_wrong_hrp(monkeypatch: pytest.MonkeyPatch):
    module = SimpleNamespace(
        bech32_decode=lambda value: ("wrong", [1, 2, 3]),
        convertbits=lambda words, frombits, tobits, pad=False: [104, 105],
    )
    monkeypatch.setattr("src.v1.services.lightning.lnurl_codec._load_pypi_bech32", lambda: module)

    with pytest.raises(ValueError, match="invalid lnurl bech32 payload"):
        decode_lnurl("lnurl1example")


def test_bech32_encode_and_decode_round_trip():
    payload = b"https://example.com"

    encoded = bech32_encode("lnurl", payload)

    assert bech32_decode(encoded) == payload


def test_bech32_decode_raises_when_separator_is_missing():
    with pytest.raises(ValueError, match="invalid bech32 string"):
        bech32_decode("invalid-value")


def test_convertbits_raises_on_invalid_padding():
    with pytest.raises(ValueError, match="invalid padding for convertbits"):
        _convertbits([31], 5, 8, pad=False)
