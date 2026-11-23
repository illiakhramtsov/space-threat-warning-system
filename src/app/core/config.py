import os
import socket
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str:
    """Select .env file based on ENV_FILE or APP_ENV (sandbox/production)."""
    explicit_file = os.getenv("ENV_FILE")
    if explicit_file and Path(explicit_file).exists():
        return explicit_file

    app_env = os.getenv("APP_ENV", "sandbox").lower()
    candidates = [
        f"config/.env.{app_env}",
        f".env.{app_env}",
        ".env",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return "config/.env.sandbox"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    APP_NAME: str = "Space Threat Warning System"
    APP_ENV: str = "sandbox"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-via-environment-variable"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./space_threats_sandbox.db"
    INSTANCE_NAME: str = socket.gethostname()

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
