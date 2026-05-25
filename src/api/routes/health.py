"""Health & readiness endpoints.

Three endpoints with distinct semantics:

* ``GET /health``   — overall health (DB + Redis checks).
* ``GET /live``     — liveness probe (no dependencies, never fails).
* ``GET /ready``    — readiness probe (same checks as ``/health`` but with
  the standard k8s 503-on-failure semantics).
"""

from __future__ import annotations

import time
from typing import Literal

import redis as redis_lib
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from src import __version__
from src.db.session import get_db
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["health"])

ComponentStatus = Literal["ok", "degraded", "down"]


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class ComponentCheck(BaseModel):
    """Result of one dependency check."""

    status: ComponentStatus = Field(..., description="ok | degraded | down")
    latency_ms: float = Field(..., ge=0.0)
    detail: str | None = Field(None, description="Error detail when not 'ok'")


class HealthResponse(BaseModel):
    """Aggregated health response."""

    status: ComponentStatus
    service: str
    version: str
    env: str
    checks: dict[str, ComponentCheck]
    scanner: dict[str, str | bool | None] = Field(
        default_factory=dict,
        description="Scanner worker status summary",
    )


# ---------------------------------------------------------------------------
# Internal check helpers
# ---------------------------------------------------------------------------
def _check_database(db: Session) -> ComponentCheck:
    """Run ``SELECT 1`` against PostgreSQL."""
    start = time.perf_counter()
    try:
        result = db.execute(text("SELECT 1")).scalar_one()
        latency_ms = (time.perf_counter() - start) * 1000.0
        if result != 1:
            return ComponentCheck(
                status="degraded",
                latency_ms=round(latency_ms, 2),
                detail=f"unexpected response: {result!r}",
            )
        return ComponentCheck(status="ok", latency_ms=round(latency_ms, 2))
    except SQLAlchemyError as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        log.warning("health.db.check_failed", error=str(exc))
        return ComponentCheck(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=type(exc).__name__,
        )


def _check_redis() -> ComponentCheck:
    """Run a PING against Redis."""
    start = time.perf_counter()
    client: redis_lib.Redis | None = None
    try:
        client = redis_lib.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
        )
        pong = client.ping()
        latency_ms = (time.perf_counter() - start) * 1000.0
        if not pong:
            return ComponentCheck(
                status="degraded",
                latency_ms=round(latency_ms, 2),
                detail="ping returned falsy",
            )
        return ComponentCheck(status="ok", latency_ms=round(latency_ms, 2))
    except redis_lib.RedisError as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        log.warning("health.redis.check_failed", error=str(exc))
        return ComponentCheck(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=type(exc).__name__,
        )
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 - defensive close
                pass


def _check_scanner() -> ComponentCheck:
    """Check scanner worker heartbeat via Redis."""
    start = time.perf_counter()
    try:
        from src.worker.scanner_state import ScannerState

        scanner_status, detail = ScannerState().check_health()
        latency_ms = (time.perf_counter() - start) * 1000.0
        if scanner_status == "ok":
            return ComponentCheck(status="ok", latency_ms=round(latency_ms, 2))
        if scanner_status == "degraded":
            return ComponentCheck(
                status="degraded",
                latency_ms=round(latency_ms, 2),
                detail=detail,
            )
        return ComponentCheck(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=detail,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - start) * 1000.0
        log.warning("health.scanner.check_failed", error=str(exc))
        return ComponentCheck(
            status="down",
            latency_ms=round(latency_ms, 2),
            detail=type(exc).__name__,
        )


def _aggregate(checks: dict[str, ComponentCheck]) -> ComponentStatus:
    """Combine component statuses into a single overall status."""
    statuses = {c.status for c in checks.values()}
    if "down" in statuses:
        return "down"
    if "degraded" in statuses:
        return "degraded"
    return "ok"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health (DB + Redis)",
    description="Reports overall health. Returns 200 always — inspect the "
    "`status` field for state. Use `/ready` for k8s readiness.",
)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """Aggregate health endpoint."""
    checks = {
        "database": _check_database(db),
        "redis": _check_redis(),
        "scanner": _check_scanner(),
    }
    overall = _aggregate(checks)
    scanner_summary = _scanner_summary()
    log.info("health.checked", overall=overall, checks={k: v.status for k, v in checks.items()})
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        version=__version__,
        env=settings.app_env.value,
        checks=checks,
        scanner=scanner_summary,
    )


def _scanner_summary() -> dict[str, str | bool | None]:
    """Lightweight scanner fields for the health payload."""
    try:
        from src.worker.scanner_state import ScannerState

        state = ScannerState().get_status()
        return {
            "running": state["running"],
            "heartbeat_at": state["heartbeat_at"],
            "uptime_seconds": str(state["uptime_seconds"])
            if state["uptime_seconds"] is not None
            else None,
        }
    except Exception:
        return {"running": False, "heartbeat_at": None, "uptime_seconds": None}


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 as long as the process is up. No dependency checks.",
)
def live() -> dict[str, str]:
    """Pure liveness — used by k8s livenessProbe."""
    return {"status": "alive"}


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Same checks as /health but returns 503 if any dependency is down.",
)
def ready(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    """Readiness — returns 503 when not ready to serve traffic."""
    payload = health(db)
    if payload.status == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
