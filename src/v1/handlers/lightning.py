from aiohttp.web_request import Request
from aiohttp.web import json_response
from prisma import Prisma
from prisma.enums import lnurl_auth_status

from ..services.lightning.login import authenticate_with_lightning, create_challenge, verify_signature
from ..app import routes

@routes.get("/auth/lightning/challenge")
async def get_challenge(request: Request):
    prisma = request.app["prisma"]
    payload = await create_challenge(prisma)
    return json_response(payload)

@routes.get("/auth/lightning/verify")
async def verify_challenge(request: Request):
    prisma: Prisma = request.app["prisma"]
    k1 = request.query.get("k1", "")
    sig = request.query.get("sig", "")
    key = request.query.get("key", "")

    if not k1 or not sig or not key:
        return json_response({"status": "ERROR", "reason": "missing k1, sig or key"}, status=400)

    challenge = await prisma.lnurl_auth.find_unique(where={"k1": k1})
    if challenge is None:
        return json_response({"status": "ERROR", "reason": "unknown k1"}, status=400)

    if challenge.status != lnurl_auth_status.pending:
        return json_response({"status": "ERROR", "reason": "k1 already used"}, status=409)

    try:
        is_valid = verify_signature(k1, sig, key)
    except ValueError:
        return json_response({"status": "ERROR", "reason": "invalid hex payload"}, status=400)
    except RuntimeError as exc:
        return json_response({"status": "ERROR", "reason": str(exc)}, status=500)

    if not is_valid:
        return json_response({"status": "ERROR", "reason": "invalid signature"}, status=401)

    await prisma.lnurl_auth.update(
        where={"k1": k1},
        data={"status": lnurl_auth_status.done},
    )

    return json_response({"status": "OK"})
