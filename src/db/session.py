"""SQLAlchemy engine + session factory (sync).

The engine is created lazily on first access so that importing this module
never opens a connection — important for ``alembic`` autogenerate and tests
that swap the DSN before any session is requested.

Public API
----------
* :func:`get_engine` — return the process-wide engine (lazy, cached).
* :func:`get_session_factory` — return the ``sessionmaker`` bound to engine.
* :func:`get_db` — FastAPI dependency that yields a session.
* :data:`engine` — convenience module-level alias (lazy-resolved).
* :data:`SessionLocal` — convenience module-level alias (lazy-resolved).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from src.utils.logger import get_logger

log = get_logger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _build_engine() -> Engine:
    """Construct the SQLAlchemy engine from current settings."""
    db_url = settings.DATABASE_URL
    parsed = make_url(db_url)
    log.info(
        "db.engine.creating",
        host=parsed.host,
        port=parsed.port,
        database=parsed.database,
        source=settings.database_url_source,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
    )

    new_engine = create_engine(
        db_url,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_timeout=settings.postgres_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.postgres_echo,
        future=True,
        connect_args={
            "application_name": settings.app_name,
        },
    )

    @event.listens_for(new_engine, "connect")
    def _on_connect(dbapi_connection: Any, _: Any) -> None:  # pragma: no cover - infra
        log.debug("db.connection.opened")

    return new_engine


def get_engine() -> Engine:
    """Return the cached process-wide :class:`Engine`, creating if needed."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the cached :class:`sessionmaker` bound to :func:`get_engine`."""
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session.

    Rolls back on uncaught exception, always closes the session.

    Example::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)) -> list[Item]:
            return db.scalars(select(Item)).all()
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
    except Exception:
        log.exception("db.session.rollback")
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """Close the connection pool. Call on graceful shutdown."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        log.info("db.engine.disposing")
        _engine.dispose()
        _engine = None
        _session_factory = None


class _LazyEngine:
    """Lazy proxy so ``from src.db.session import engine`` works without
    opening a connection at import time.
    """

    def __getattr__(self, item: str) -> Any:
        return getattr(get_engine(), item)

    def __repr__(self) -> str:
        return f"<LazyEngine resolved={_engine is not None}>"


class _LazySessionFactory:
    """Lazy proxy for the module-level :data:`SessionLocal` alias."""

    def __call__(self, *args: Any, **kwargs: Any) -> Session:
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(get_session_factory(), item)

    def __repr__(self) -> str:
        return f"<LazySessionFactory resolved={_session_factory is not None}>"


# Convenience module-level aliases (lazy)
engine: Any = _LazyEngine()
SessionLocal: Any = _LazySessionFactory()
