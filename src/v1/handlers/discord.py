from uuid import uuid4
from aiohttp.web import HTTPFound, json_response
from aiohttp.web_request import Request
from prisma import Prisma

from src.settings import settings
from ..cookie import set_cookie_and_redirect
from ..app import routes
from ..jwt import create_access_token, create_refresh_token
from ..services.discord.login import DiscordOAuthError, build_discord_authorize_url, decode_state, encode_state, handle_login


@routes.get("/auth/discord/login")
async def discord_login(request: Request):
    state = encode_state({
        "redirect": request.query.get("redirect"),
        "nonce": str(uuid4())
    })
    return HTTPFound(build_discord_authorize_url(state))


@routes.get("/auth/discord/callback")
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
        user = await handle_login(prisma, code)
    except DiscordOAuthError as exc:
        return json_response({"error": str(exc)}, status=401)

    state = decode_state(state_str)
    redirect: str | None = state.get("redirect")
    if not redirect:
        return json_response({"error": "Missing redirect"}, status=400)
    
    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)
    response = set_cookie_and_redirect(HTTPFound(redirect), access_token, refresh_token)

    return response
