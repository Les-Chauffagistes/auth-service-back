from prisma import Prisma

from ...excpetions import UsernameAlreadyInUseException
from .utils import check_account_exists, hash_password


class CredentialsProviderAlreadyLinkedError(Exception):
    pass


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


async def link_username_password_account(prisma: Prisma, user_id: int, username: str, password: str):
    user = await prisma.users.find_unique(where={"id": user_id})
    if user is None:
        raise ValueError("User not found")

    if await check_account_exists(prisma, username):
        raise UsernameAlreadyInUseException

    existing_credentials = await prisma.password_users.find_first(where={"user_id": user_id})
    if existing_credentials is not None:
        raise CredentialsProviderAlreadyLinkedError("Credentials provider already linked")

    hashed = await hash_password(password)
    await prisma.password_users.create(
        data={
            "username": username,
            "password": hashed,
            "user_id": user_id,
        }
    )
    return user