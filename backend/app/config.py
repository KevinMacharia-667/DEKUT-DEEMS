"""
Application configuration loaded from environment variables via pydantic-settings.
"""

from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for the DeKUT Event Management System backend.
    Values are read from a `.env` file or from actual environment variables.
    """

    # ── Environment & Server ──────────────────────────────────────────
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./dekut_events.db"

    # ── JWT Authentication ────────────────────────────────────────────
    JWT_SECRET: str = "your_super_secret_jwt_key_here_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── CORS Origins ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if self.JWT_SECRET == "your_super_secret_jwt_key_here_change_in_production":
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default JWT_SECRET cannot be used in production mode! "
                    "Set a secure random JWT_SECRET in your environment or .env file."
                )
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
