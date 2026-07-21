from urllib.parse import urlencode

from aiohttp import ClientSession
from prisma import Prisma

from src.settings import settings

DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_ME_URL = "https://discord.com/api/users/@me"
DISCORD_SCOPE = "identify"


class DiscordOAuthError(Exception):
    pass

import json
import base64

def encode_state(state: dict) -> str:
    json_str = json.dumps(state)
    return base64.urlsafe_b64encode(json_str.encode()).decode()

def decode_state(state_str: str) -> dict:
    json_str = base64.urlsafe_b64decode(state_str.encode()).decode()
    return json.loads(json_str)

def build_discord_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.discord_client_id,
            "redirect_uri": settings.discord_callback_url,
            "response_type": "code",
            "scope": DISCORD_SCOPE,
            "state": state
        }
    )
    return f"{DISCORD_AUTHORIZE_URL}?{query}"


async def _fetch_discord_token(code: str) -> str:
    payload = {
        "client_id": str(settings.discord_client_id),
        "client_secret": settings.discord_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.discord_callback_url,
    }

    async with ClientSession() as session:
        async with session.post(
            DISCORD_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            token_payload = await response.json(content_type=None)

    access_token = token_payload.get("access_token")
    if response.status != 200 or not access_token:
        raise DiscordOAuthError(token_payload.get("error_description", "unable to fetch Discord access token"))

    return access_token


async def _fetch_discord_identity(access_token: str) -> dict:
    async with ClientSession() as session:
        async with session.get(
            DISCORD_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            identity = await response.json(content_type=None)

    discord_id = identity.get("id")
    username = identity.get("username")
    if response.status != 200 or not discord_id or not username:
        raise DiscordOAuthError(identity.get("message", "unable to fetch Discord identity"))

    return identity


async def handle_login(db: Prisma, code: str):
    discord_access_token = await _fetch_discord_token(code)
    identity = await _fetch_discord_identity(discord_access_token)

    discord_id = identity["id"]
    discord_name = identity["username"]

    discord_account = await db.discord_users.find_unique(
        where={"id": discord_id},
        include={"users": True},
    )

    if discord_account is None:
        user = await db.users.create(data={"pseudo": discord_name})
        discord_account = await db.discord_users.create(
            data={
                "id": discord_id,
                "discord_name": discord_name,
                "user_id": user.id,
            },
            include={"users": True},
        )
    else:
        discord_account = await db.discord_users.update(
            where={"id": discord_id},
            data={"discord_name": discord_name},
            include={"users": True},
        )
        assert discord_account is not None

    assert discord_account.users is not None
    return discord_account.users
