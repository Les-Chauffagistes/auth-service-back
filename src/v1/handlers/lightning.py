from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web import json_response
from aiohttp import WSMsgType
from prisma import Prisma
from prisma.enums import lnurl_auth_status
from authentication_types.models import LNCallbackSuccessPayload

from ..auth import resolve_authenticated_user_id
from ..services.lightning.login import (
    authenticate_with_lightning,
    create_challenge,
    link_lightning_provider,
    LightningProviderAlreadyLinkedError,
    verify_signature,
)
from ..services.lightning.exchange import create_exchange_code, create_onboarding_code
from ..app import routes

_ws_registry: dict[str, web.WebSocketResponse] = {}


@routes.get("/lightning/challenge")
async def get_challenge(request: Request):
    prisma = request.app["prisma"]
    flow = request.query.get("flow", "login")
    if flow not in ("login", "link"):
        return json_response({"error": "Invalid flow"}, status=400)

    if flow == "link":
        linked_user_id = resolve_authenticated_user_id(request)
        if linked_user_id is None:
            return json_response({"error": "Unauthorized"}, status=401)
        payload = await create_challenge(prisma)
        await prisma.lnurl_auth.update(
            where={"k1": payload["k1"]},
            data={"user_id": linked_user_id},
        )
        return json_response(payload)

    payload = await create_challenge(prisma)
    return json_response(payload)


@routes.get("/lightning/ws")
async def lightning_ws(request: Request):
    k1 = request.query.get("k1", "")
    if not k1:
        return json_response({"status": "ERROR", "reason": "missing k1"}, status=400)

    prisma: Prisma = request.app["prisma"]
    challenge = await prisma.lnurl_auth.find_unique(where={"k1": k1})
    if challenge is None or challenge.status != lnurl_auth_status.pending:
        return json_response({"status": "ERROR", "reason": "invalid k1"}, status=400)

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    existing = _ws_registry.get(k1)
    if existing is not None and not existing.closed:
        await existing.close()
    _ws_registry[k1] = ws

    try:
        async for msg in ws:
            if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    finally:
        _ws_registry.pop(k1, None)

    return ws


def _check_signature(k1: str, sig: str, key: str) -> web.Response | None:
    """Returns an error response if the signature is missing/invalid, otherwise None."""
    try:
        is_valid = verify_signature(k1, sig, key)
    except ValueError:
        return json_response(
            {"status": "ERROR", "reason": "invalid hex payload"}, status=400
        )
    except RuntimeError as exc:
        return json_response({"status": "ERROR", "reason": str(exc)}, status=500)

    if not is_valid:
        return json_response(
            {"status": "ERROR", "reason": "invalid signature"}, status=401
        )
    return None


async def _resolve_verify_code(prisma: Prisma, challenge, key: str) -> web.Response | str:
    """Returns an error response, or the exchange/onboarding code for the challenge."""
    linked_user_id = challenge.user_id
    if linked_user_id is not None:
        try:
            linked_user = await link_lightning_provider(prisma, linked_user_id, key)
        except LightningProviderAlreadyLinkedError as exc:
            return json_response({"status": "ERROR", "reason": str(exc)}, status=409)
        except ValueError as exc:
            return json_response({"status": "ERROR", "reason": str(exc)}, status=404)
        return create_exchange_code(linked_user.id)

    auth_result = await authenticate_with_lightning(prisma, key)
    if auth_result[0] == "login":
        return create_exchange_code(auth_result[1].id)
    return create_onboarding_code(auth_result[1])


@routes.get("/lightning/verify")
async def verify_challenge(request: Request):
    prisma: Prisma = request.app["prisma"]
    k1 = request.query.get("k1", "")
    sig = request.query.get("sig", "")
    key = request.query.get("key", "")

    if not k1 or not sig or not key:
        return json_response(
            {"status": "ERROR", "reason": "missing k1, sig or key"}, status=400
        )

    challenge = await prisma.lnurl_auth.find_unique(where={"k1": k1})
    if challenge is None:
        return json_response({"status": "ERROR", "reason": "unknown k1"}, status=400)

    if challenge.status != lnurl_auth_status.pending:
        return json_response(
            {"status": "ERROR", "reason": "k1 already used"}, status=409
        )

    signature_error = _check_signature(k1, sig, key)
    if signature_error is not None:
        return signature_error

    code_or_error = await _resolve_verify_code(prisma, challenge, key)
    if isinstance(code_or_error, web.Response):
        return code_or_error
    code = code_or_error

    await prisma.lnurl_auth.update(
        where={"k1": k1},
        data={"status": lnurl_auth_status.done},
    )

    ws = _ws_registry.pop(k1, None)
    if ws is not None and not ws.closed:
        await ws.send_json(
            LNCallbackSuccessPayload(status="OK", code=code).model_dump()
        )
        await ws.close()

    return json_response({"status": "OK"})
