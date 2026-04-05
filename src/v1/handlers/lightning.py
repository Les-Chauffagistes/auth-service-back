from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web import json_response
from aiohttp import WSMsgType
from prisma import Prisma
from prisma.enums import lnurl_auth_status
from authentication_types.models import LNCallbackSuccessPayload

from ..services.lightning.login import (
    authenticate_with_lightning,
    create_challenge,
    verify_signature,
)
from ..services.lightning.exchange import create_exchange_code, create_onboarding_code
from ..app import routes

_ws_registry: dict[str, web.WebSocketResponse] = {}


@routes.get("/auth/lightning/challenge")
async def get_challenge(request: Request):
    prisma = request.app["prisma"]
    payload = await create_challenge(prisma)
    return json_response(payload)


@routes.get("/auth/lightning/ws")
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


@routes.get("/auth/lightning/verify")
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

    auth_result = await authenticate_with_lightning(prisma, key)

    await prisma.lnurl_auth.update(
        where={"k1": k1},
        data={"status": lnurl_auth_status.done},
    )

    ws = _ws_registry.pop(k1, None)
    if ws is not None and not ws.closed:
        if auth_result[0] == "login":
            code = create_exchange_code(auth_result[1].id)
        else:
            code = create_onboarding_code(auth_result[1])
        await ws.send_json(
            LNCallbackSuccessPayload(status="OK", code=code).model_dump()
        )
        await ws.close()

    return json_response({"status": "OK"})
