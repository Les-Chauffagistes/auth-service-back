from prisma import Prisma

from ...excpetions import UsernameAlreadyInUseException
from .utils import check_account_exists, hash_password


async def create_username_password_account(prisma: Prisma, username: str, password: str):
    if await check_account_exists(prisma, username):
        raise UsernameAlreadyInUseException

    hashed = await hash_password(password)

    user = await prisma.users.create(data={"pseudo": username})
    await prisma.password_users.create(data={
        "username": username,
        "password": hashed,
        "user_id": user.id,
    })

    return user