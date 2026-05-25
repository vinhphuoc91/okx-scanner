"""FastAPI application factory.

Public surface:

* :func:`create_app` — build a configured :class:`fastapi.FastAPI` instance.
* :data:`app`         — module-level singleton used by ASGI servers.
* :func:`run`         — entry point that starts uvicorn (CLI ``okx-api``).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from config import settings
from src import __version__
from src.api.routes import health, opportunities, status, alerts, strategy_settings
from src.db.session import dispose_engine, get_engine
from src.utils.logger import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler — runs on startup and shutdown."""
    configure_logging()
    log.info(
        "app.startup",
        version=__version__,
        env=settings.app_env.value,
        debug=settings.app_debug,
    )

    # Eagerly initialize the DB engine so misconfiguration fails fast.
    try:
        get_engine()
    except Exception:
        log.exception("app.startup.db_init_failed")
        raise

    try:
        yield
    finally:
        log.info("app.shutdown.beginning")
        dispose_engine()
        log.info("app.shutdown.complete")


def create_app() -> FastAPI:
    """Build and return a configured FastAPI app.

    A factory is preferred over a module-level singleton because:
      * Tests can create isolated instances.
      * Configuration is resolved at call time, not at import time.
    """
    configure_logging()

    application = FastAPI(
        title="OKX Opportunity Scanner",
        description=(
            "Detects trading opportunities on OKX in real time using a "
            "configurable strategy + scoring pipeline."
        ),
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Middleware
    # -------------------------------------------------------------------------
    if settings.cors_origin_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    @application.middleware("http")
    async def _request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Attach a request_id + timing to every request and log it."""
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        except Exception:
            log.exception("http.request.unhandled_exception")
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            log.info(
                "http.request",
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
            )
            structlog.contextvars.clear_contextvars()

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------
    application.include_router(health.router)
    application.include_router(opportunities.router)
    application.include_router(status.router)
    application.include_router(alerts.router)
    application.include_router(strategy_settings.router)

    @application.get("/", include_in_schema=False)
    async def _root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": __version__,
            "env": settings.app_env.value,
        }

    return application


# ASGI entry point: ``uvicorn src.api.app:app``
app: FastAPI = create_app()


def run() -> None:  # pragma: no cover - thin CLI shim
    """CLI entrypoint (``okx-api``): start uvicorn programmatically."""
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers if not settings.api_reload else 1,
        reload=settings.api_reload,
        log_config=None,  # we configure logging ourselves
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover
    run()
