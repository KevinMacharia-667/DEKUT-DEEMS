"""
SQLAlchemy database engine, session factory, and declarative Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def normalise_database_url(url: str) -> str:
    """Hosts often hand out 'postgres://' URLs; SQLAlchemy 2 only accepts 'postgresql://'."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = normalise_database_url(settings.DATABASE_URL)

# Handle SQLite-specific connect args (needed for multi-thread access)
connect_args = {}
engine_options = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Hosted Postgres (e.g. Neon) closes idle connections when it scales to zero:
    # test each pooled connection before use and recycle them every 5 minutes.
    engine_options = {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Set True for SQL debug logging
    **engine_options,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
    pass
