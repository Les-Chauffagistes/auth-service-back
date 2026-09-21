from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lightning_callback_url: str
    jwt_secret: str
    server_port: int = 8080
    database_url: str
    discord_callback_url: str
    discord_client_id: int
    discord_client_secret: str
    domain_name: str
    # "development" est le seul cas où les cookies auth passent en clair (dev sur
    # localhost, sans TLS) — tout le reste (staging/production) doit rester secure.
    environment: Literal["development", "staging", "production"] = "production"


    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()  # type: ignore[call-arg]
