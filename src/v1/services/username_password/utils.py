import asyncio
import bcrypt
from prisma import Prisma


async def check_account_exists(prisma: Prisma, username: str) -> bool:
    return await prisma.password_users.find_first(where={"username": username}) is not None


async def hash_password(password: str) -> str:
    hashed = await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt())
    return hashed.decode()


async def verify_password(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed.encode())