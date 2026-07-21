from prisma import Prisma

from ...excpetions import UnkownUserExpcetion, WrongCredentialsException
from .utils import verify_password


async def login_with_username_password(prisma: Prisma, username: str, password: str):
    account = await prisma.password_users.find_first(
        where={"username": username},
        include={"users": True},
    )

    if account is None:
        raise UnkownUserExpcetion

    if not await verify_password(password, account.password):
        raise WrongCredentialsException

    assert account.users is not None
    return account.users