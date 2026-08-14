from ..services.user import get_users_by_ids
from aiohttp.web_response import json_response

from ..app import routes
from ..services.user import get_user_by_id


@routes.get("/user/{user_id}")
async def get_user(request):
    user_id = request.match_info["user_id"]
    try:
        user = await get_user_by_id(request.app["prisma"], int(user_id))
        if user is None:
            return json_response({"error": "User not found"}, status=404)
        return json_response({"id": user.id, "pseudo": user.pseudo})

    except ValueError:
        return json_response({"error": "Invalid user ID"}, status=400)

    except Exception:
        return json_response({"error": "Unable to fetch user"}, status=500)


@routes.post("/users/by-ids")
async def get_users(request):
    try:
        body = await request.json()
        user_ids = body.get("ids", [])
        users = await get_users_by_ids(request.app["prisma"], user_ids)
        return json_response([{"id": user.id, "pseudo": user.pseudo} for user in users])

    except ValueError:
        return json_response({"error": "Invalid JSON"}, status=400)

    except Exception:
        return json_response({"error": "Unable to fetch users"}, status=500)
