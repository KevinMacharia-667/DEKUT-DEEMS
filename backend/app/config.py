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
    # Defaults to "production" so a missing or forgotten setting fails safe.
    APP_ENV: str = "production"
    ENVIRONMENT: str = "production"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./dekut_events.db"

    # ── JWT Authentication ────────────────────────────────────────────
    JWT_SECRET: str = "your_super_secret_jwt_key_here_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Rate Limiting (Brute-Force & Abuse Defense) ───────────────────
    AUTH_RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── CORS Origins ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        env_val = (self.APP_ENV or self.ENVIRONMENT or "production").lower()
        if env_val != "development":
            if self.JWT_SECRET == "your_super_secret_jwt_key_here_change_in_production":
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default JWT_SECRET cannot be used unless APP_ENV=development is explicitly set! "
                    "In production mode, set a strong, unique JWT_SECRET in your environment or .env file."
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
