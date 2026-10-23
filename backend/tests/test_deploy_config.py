"""
Deployment settings: CORS origins from the host's environment, Postgres URL
normalisation, and the guard that stops seed.py wiping a hosted database.
"""

import pytest

from app.config import Settings
from app.database import normalise_database_url
import seed


def test_cors_origins_accept_comma_separated_and_json(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ORIGINS", "https://tukio-web.onrender.com, https://tukio.example.org/")
    assert Settings().CORS_ORIGINS == ["https://tukio-web.onrender.com", "https://tukio.example.org"]

    monkeypatch.setenv("CORS_ORIGINS", '["https://a.example.com", "https://b.example.com"]')
    assert Settings().CORS_ORIGINS == ["https://a.example.com", "https://b.example.com"]


def test_postgres_scheme_is_normalised():
    assert normalise_database_url("postgres://u:p@host/db") == "postgresql://u:p@host/db"
    assert normalise_database_url("postgresql://u:p@host/db?sslmode=require") == "postgresql://u:p@host/db?sslmode=require"
    assert normalise_database_url("sqlite:///./dekut_events.db") == "sqlite:///./dekut_events.db"


def test_seed_refuses_hosted_database_without_confirmation(monkeypatch):
    monkeypatch.delenv("SEED_CONFIRM_RESET", raising=False)
    with pytest.raises(SystemExit, match="DROPS ALL TABLES"):
        seed.check_safe_to_seed("postgresql://u:p@host/db")


def test_seed_refuses_hosted_database_with_demo_password(monkeypatch):
    monkeypatch.setenv("SEED_CONFIRM_RESET", "yes")
    monkeypatch.setattr(seed, "DEFAULT_PASSWORD", seed.LOCAL_DEMO_PASSWORD)
    with pytest.raises(SystemExit, match="public demo password"):
        seed.check_safe_to_seed("postgresql://u:p@host/db")


def test_seed_allows_local_sqlite_and_confirmed_hosted_database(monkeypatch):
    seed.check_safe_to_seed("sqlite:///./dekut_events.db")
    monkeypatch.setenv("SEED_CONFIRM_RESET", "yes")
    monkeypatch.setattr(seed, "DEFAULT_PASSWORD", "a-long-private-passphrase")
    seed.check_safe_to_seed("postgresql://u:p@host/db")
