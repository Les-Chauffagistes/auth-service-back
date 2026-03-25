from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    callback_url: str
    jwt_secret: str
    server_port: int = 8080
    database_url: str

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()  # type: ignore[call-arg]
