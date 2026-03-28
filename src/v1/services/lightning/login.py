from os import urandom
from prisma import Prisma
from src.settings import settings
from .lnurl_codec import encode_lnurl


async def create_challenge(db: Prisma):
    k1 = urandom(32).hex()
    await db.lnurl_auth.create(data={"k1": k1})

    callback_url = f"{settings.lightning_callback_url}?k1={k1}&tag=login"
    lnurl = encode_lnurl(callback_url)

    return {"lnurl": lnurl, "k1": k1}


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


async def authenticate_with_lightning(db: Prisma, key: str):
    ln_account = await db.ln_users.find_first(
        where={"ln_key": key},
        include={"users": True},
    )

    if ln_account is None:
        user = await db.users.create(data={})
        ln_account = await db.ln_users.create(
            data={"ln_key": key, "user_id": user.id},
            include={"users": True},
        )

    assert ln_account.users is not None
    return ln_account
