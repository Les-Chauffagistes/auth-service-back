from os import urandom
from typing import Literal, Union
from prisma import Prisma
from prisma.models import users
from src.settings import settings
from .lnurl_codec import encode_lnurl
from authentication_types.models import LNChallenge
from init import log


class LightningProviderAlreadyLinkedError(Exception):
    pass


async def create_challenge(db: Prisma):
    k1 = urandom(32).hex()
    await db.lnurl_auth.create(data={"k1": k1})

    callback_url = f"{settings.lightning_callback_url}?k1={k1}&tag=login"
    log.debug(callback_url)
    lnurl = encode_lnurl(callback_url)

    return LNChallenge(
        lnurl = lnurl,
        k1 = k1
    ).model_dump()


def verify_signature(k1: str, sig: str, key: str) -> bool:
    try:
        from ecdsa import BadSignatureError, SECP256k1, VerifyingKey
        from ecdsa.errors import MalformedPointError
        from ecdsa.util import sigdecode_der
    except ModuleNotFoundError as exc:
        raise RuntimeError("missing dependency: ecdsa") from exc

    challenge = bytes.fromhex(k1)
    signature = bytes.fromhex(sig)
    public_key = bytes.fromhex(key)

    if len(challenge) != 32:
        raise ValueError("k1 must be 32 bytes")
    if len(public_key) != 33 or public_key[0] not in (2, 3):
        raise ValueError("key must be a compressed secp256k1 public key")

    try:
        verifying_key = VerifyingKey.from_string(
            public_key,
            curve=SECP256k1,
            valid_encodings=("compressed",),
        )

        return verifying_key.verify_digest(
            signature,
            challenge,
            sigdecode=sigdecode_der,
        )
    except (BadSignatureError, MalformedPointError):
        return False


async def authenticate_with_lightning(
    db: Prisma, key: str
) -> Union[tuple[Literal["login"], users], tuple[Literal["onboarding"], str]]:
    ln_account = await db.ln_users.find_first(
        where={"ln_key": key},
        include={"users": True},
    )

    if ln_account is None:
        return ("onboarding", key)

    assert ln_account.users is not None
    return ("login", ln_account.users)


async def link_lightning_provider(db: Prisma, user_id: int, key: str):
    user = await db.users.find_unique(where={"id": user_id})
    if user is None:
        raise ValueError("User not found")

    ln_account = await db.ln_users.find_first(where={"ln_key": key})
    if ln_account is None:
        await db.ln_users.create(data={"ln_key": key, "user_id": user_id})
        return user

    if ln_account.user_id != user_id:
        raise LightningProviderAlreadyLinkedError("Lightning key already linked to another user")

    return user
