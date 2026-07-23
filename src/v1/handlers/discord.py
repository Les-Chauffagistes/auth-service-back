from uuid import uuid4
from aiohttp.web import HTTPFound, json_response
from aiohttp.web_request import Request
from prisma import Prisma

from ..auth import resolve_authenticated_user_id
from ..cookie import set_cookie_and_redirect
from ..app import routes
from ..jwt import create_access_token, create_refresh_token
from ..services.discord.login import (
    DiscordOAuthError,
    DiscordProviderAlreadyLinkedError,
    build_discord_authorize_url,
    decode_state,
    encode_state,
    handle_link,
    handle_login,
)
@routes.get("/discord/login")
async def discord_login(request: Request):
    flow = request.query.get("flow", "login")
    if flow not in ("login", "link"):
        return json_response({"error": "Invalid flow"}, status=400)

    state_payload: dict[str, str | None] = {
        "redirect": request.query.get("redirect"),
        "nonce": str(uuid4()),
        "flow": flow,
    }
    if flow == "link":
        linked_user_id = resolve_authenticated_user_id(request)
        if linked_user_id is None:
            return json_response({"error": "Unauthorized"}, status=401)

    state = encode_state({**state_payload})
    return HTTPFound(build_discord_authorize_url(state))


@routes.get("/discord/callback")
async def discord_callback(request: Request):
    prisma: Prisma = request.app["prisma"]
    code = request.query.get("code")
    error = request.query.get("error")
    state_str = request.query.get("state")


    if error:
        return json_response({"error": f"Discord OAuth error: {error}"}, status=400)

    if not code:
        return json_response({"error": "Missing authorization code"}, status=400)

    if not state_str:
        return json_response({"error": "Missing state"}, status=400)

    try:
        state = decode_state(state_str)
    except Exception:
        return json_response({"error": "Invalid state"}, status=400)

    flow: str = state.get("flow", "login")
    if flow not in ("login", "link"):
        return json_response({"error": "Invalid flow"}, status=400)
    try:
        if flow == "link":
            linked_user_id = resolve_authenticated_user_id(request)
            if linked_user_id is None:
                return json_response({"error": "Unauthorized"}, status=401)
            user = await handle_link(prisma, code, linked_user_id)
        else:
            user = await handle_login(prisma, code)
    except DiscordOAuthError as exc:
        return json_response({"error": str(exc)}, status=401)
    except DiscordProviderAlreadyLinkedError as exc:
        return json_response({"error": str(exc)}, status=409)

    redirect: str | None = state.get("redirect")
    if not redirect:
        return json_response({"error": "Missing redirect"}, status=400)
    
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(HTTPFound(redirect), access_token, refresh_token)

    return response
