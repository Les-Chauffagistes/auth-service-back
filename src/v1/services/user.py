from prisma import Prisma


async def get_user_by_id(prisma: Prisma, user_id:int):
    return await prisma.users.find_unique(where={"id": user_id})

async def get_users_by_ids(prisma: Prisma, user_ids: list[int]):
    return await prisma.users.find_many(where={"id": {"in": user_ids}})
