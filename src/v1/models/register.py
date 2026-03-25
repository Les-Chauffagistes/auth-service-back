from pydantic import BaseModel


class RegisterPayload(BaseModel):
    username: str
    password: str