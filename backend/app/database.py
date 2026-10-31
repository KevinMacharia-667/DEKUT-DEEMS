"""
SQLAlchemy database engine, session factory, and declarative Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def normalise_database_url(url: str) -> str:
    """
    Point Postgres URLs at the installed psycopg2 driver. Hosts hand out 'postgres://' or
    'postgresql://' URLs; SQLAlchemy 2 rejects the first, and from 2.1 a bare 'postgresql://'
    means psycopg 3, which is not installed.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
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
