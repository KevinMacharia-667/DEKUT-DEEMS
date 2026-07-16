"""
Application configuration loaded from environment variables via pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for the DeKUT Event Management System backend.
    Values are read from a `.env` file or from actual environment variables.
    """

    # ── Server ────────────────────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./dekut_events.db"

    # ── JWT Authentication ────────────────────────────────────────────
    JWT_SECRET: str = "your_super_secret_jwt_key_here_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
