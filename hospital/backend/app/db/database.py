"""Small SQLAlchemy setup for VITAVIA's SQLite audit database."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import PROJECT_ROOT, settings


BACKEND_ROOT = PROJECT_ROOT / "backend"


class Base(DeclarativeBase):
    """Base class used exclusively by SQLAlchemy ORM models."""


def _resolve_database_url(database_url: str) -> str:
    """Resolve relative SQLite paths against backend so launches use one predictable file."""
    if database_url == "sqlite:///:memory:" or not database_url.startswith("sqlite:///"):
        return database_url

    database_path = Path(database_url.removeprefix("sqlite:///"))
    if database_path.is_absolute():
        return database_url
    return f"sqlite:///{(BACKEND_ROOT / database_path).resolve()}"


def _create_engine(database_url: str) -> Engine:
    """Create a SQLite-compatible engine without adding external database drivers."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


configured_database_url = _resolve_database_url(settings.database_url)
engine = _create_engine(configured_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
_initialized_url: Optional[str] = None


def configure_database(database_url: str) -> None:
    """Switch database binding for isolated tests without changing production configuration."""
    global configured_database_url, engine, SessionLocal, _initialized_url
    engine.dispose()
    configured_database_url = _resolve_database_url(database_url)
    engine = _create_engine(configured_database_url)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    _initialized_url = None


def init_db() -> None:
    """Create history tables once for the configured SQLite database; never drop data."""
    global _initialized_url
    if _initialized_url == configured_database_url:
        return
    # Import registers ORM models with Base before metadata creation.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _initialized_url = configured_database_url


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a compact transactional session for centralized persistence operations."""
    init_db()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
