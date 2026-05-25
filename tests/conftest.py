"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.api.routes import health as health_routes
from src.db.session import get_db


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Mock SQLAlchemy session that succeeds on ``SELECT 1``."""
    session = MagicMock(spec=Session)
    execute_result = MagicMock()
    execute_result.scalar_one.return_value = 1
    session.execute.return_value = execute_result
    return session


@pytest.fixture
def app(mock_db_session: MagicMock):
    """Fresh FastAPI app with DB dependency overridden."""
    application = create_app()

    def _override_get_db() -> Generator[MagicMock, None, None]:
        yield mock_db_session

    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest.fixture
def healthy_scanner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch scanner health check to report ok."""

    def _ok() -> health_routes.ComponentCheck:
        return health_routes.ComponentCheck(status="ok", latency_ms=1.0)

    monkeypatch.setattr(health_routes, "_check_scanner", _ok)
    monkeypatch.setattr(
        health_routes,
        "_scanner_summary",
        lambda: {
            "running": True,
            "heartbeat_at": "2026-05-25T00:00:00+00:00",
            "uptime_seconds": "60",
        },
    )


@pytest.fixture
def client(app, healthy_scanner: None) -> Generator[TestClient, None, None]:
    """HTTP client backed by the test app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def healthy_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch Redis health check to report ok."""

    def _ok() -> health_routes.ComponentCheck:
        return health_routes.ComponentCheck(status="ok", latency_ms=1.0)

    monkeypatch.setattr(health_routes, "_check_redis", _ok)


@pytest.fixture
def down_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch Redis health check to report down."""

    def _down() -> health_routes.ComponentCheck:
        return health_routes.ComponentCheck(
            status="down",
            latency_ms=1.0,
            detail="ConnectionError",
        )

    monkeypatch.setattr(health_routes, "_check_redis", _down)


@pytest.fixture
def failing_db(app, mock_db_session: MagicMock) -> None:
    """Make the DB session raise on execute."""
    from sqlalchemy.exc import OperationalError

    mock_db_session.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("connection refused"),
    )
