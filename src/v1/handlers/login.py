import jwt
from aiohttp.web_request import Request
from aiohttp.web import json_response
from authentication_types.models import User, ExchangeCodePayload, Status
from prisma import Prisma

from ..auth import resolve_authenticated_user_id
from ..cookie import delete_cookies, set_cookie_and_redirect, ACCESS_TOKEN_COOKIE_NAME
from ..jwt import (
    create_access_token,
    create_onboarding_token,
    create_refresh_token,
    decode_access_token,
    decode_onboarding_token,
    rotate_refresh_token,
)
from ..services.lightning.exchange import consume_exchange_code
from ..app import routes


@routes.get("/me")
async def me(request: Request):
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not access_token:
        return json_response({"error": "Missing token"}, status=401)

    try:
        payload = decode_access_token(access_token)
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid token"}, status=401)

    return json_response(
        User(user_id=payload["sub"], pseudo=payload["pseudo"]).model_dump()
    )


@routes.post("/refresh")
async def refresh_token(request: Request):
    provided_refresh_token = request.cookies.get("refresh_token")

    if not provided_refresh_token:
        try:
            raw_payload = await request.json()
        except ValueError:
            raw_payload = {}
        provided_refresh_token = raw_payload.get("refresh_token")

    if not provided_refresh_token:
        return json_response({"error": "Missing refresh token"}, status=401)

    prisma = request.app["prisma"]

    try:
        user, new_refresh_token = await rotate_refresh_token(
            prisma, provided_refresh_token
        )
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Refresh token expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid refresh token"}, status=401)

    access_token = create_access_token(user.id, user.pseudo)
    payload = decode_access_token(access_token)
    response = set_cookie_and_redirect(
        json_response({"user_id": payload["sub"], "pseudo": payload["pseudo"]}),
        access_token,
        new_refresh_token,
    )

    return response


@routes.delete("/logout")
async def logout(_: Request):
    response = delete_cookies()
    return response


@routes.post("/exchange")
async def exchange(request: Request):
    try:
        body: dict = await request.json()
    except ValueError:
        return json_response({"error": "Invalid JSON"}, status=400)

    code = body.get("code")
    if not code:
        return json_response({"error": "Missing code"}, status=400)

    payload = consume_exchange_code(code)
    if payload is None:
        return json_response({"error": "Invalid or expired code"}, status=401)

    if payload["type"] == "onboarding":
        session_token = create_onboarding_token(payload["ln_key"])
        return json_response(ExchangeCodePayload(
            status=Status.onboarding,
            session_token=session_token
        ).model_dump(mode="json"))

    prisma: Prisma = request.app["prisma"]
    user = await prisma.users.find_unique(where={"id": payload["user_id"]})
    if user is None:
        return json_response({"error": "User not found"}, status=404)

    access_token = create_access_token(user.id, user.pseudo)
    refresh_token = await create_refresh_token(prisma, user.id)

    return set_cookie_and_redirect(
        json_response(
            ExchangeCodePayload(
                status=Status.logged_in,
                user=User(user_id=str(user.id), pseudo=user.pseudo),
            ).model_dump(mode="json")
        ),
        access_token,
        refresh_token,
    )

@routes.post("/lightning/complete")
async def complete_lightning_onboarding(request: Request):
    try:
        body: dict = await request.json()
    except ValueError:
        return json_response({"error": "Invalid JSON"}, status=400)

    session_token = body.get("session_token")
    pseudo = body.get("pseudo")

    if not session_token or not pseudo:
        return json_response({"error": "Missing session_token or pseudo"}, status=400)

    try:
        token_payload = decode_onboarding_token(session_token)
    except jwt.ExpiredSignatureError:
        return json_response({"error": "Session expired"}, status=401)
    except jwt.InvalidTokenError:
        return json_response({"error": "Invalid session token"}, status=401)

    ln_key = token_payload["ln_key"]
    prisma: Prisma = request.app["prisma"]

    existing_pseudo = await prisma.users.find_first(where={"pseudo": pseudo})
    if existing_pseudo is not None:
        return json_response({"error": "Pseudo already taken"}, status=409)

    existing_ln = await prisma.ln_users.find_first(where={"ln_key": ln_key})
    if existing_ln is not None:
        return json_response({"error": "Key already registered"}, status=409)

    user = await prisma.users.create(data={"pseudo": pseudo})
    await prisma.ln_users.create(data={"ln_key": ln_key, "user_id": user.id})

    access_token = create_access_token(user.id, user.pseudo)
    new_refresh_token = await create_refresh_token(prisma, user.id)

    return set_cookie_and_redirect(
        json_response(
            ExchangeCodePayload(
                status=Status.logged_in,
                user=User(user_id=str(user.id), pseudo=user.pseudo),
            ).model_dump(mode="json")
        ),
        access_token,
        new_refresh_token,
    )


@routes.get("/providers")
async def get_linked_providers(request: Request):
    if not request.cookies.get(ACCESS_TOKEN_COOKIE_NAME):
        return json_response({"error": "Missing token"}, status=401)

    user_id = resolve_authenticated_user_id(request)
    if user_id is None:
        return json_response({"error": "Invalid token"}, status=401)

    prisma: Prisma = request.app["prisma"]
    has_discord = await prisma.discord_users.find_first(where={"user_id": user_id}) is not None
    has_lightning = await prisma.ln_users.find_first(where={"user_id": user_id}) is not None
    credentials = await prisma.password_users.find_first(where={"user_id": user_id})

    return json_response(
        {
            "discord": has_discord,
            "lightning": has_lightning,
            "credentials": credentials is not None,
            "username": credentials.username if credentials is not None else None,
        }
    )
