"""Database session management for the FastAPI app."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from .db_backend import build_engine, build_session_factory
from .settings import AppSettings

settings = AppSettings()
engine = build_engine(settings.database_url)
SessionLocal = build_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields one session per request."""

    with SessionLocal() as session:
        yield session
        session.commit()
