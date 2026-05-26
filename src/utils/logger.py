"""Structured JSON logging powered by ``structlog``.

In production we emit one JSON object per log record so that log aggregators
(Loki, Elastic, CloudWatch, etc.) can index every field. In development we
default to a human-readable rendered format unless ``APP_ENV != development``.

Public API
----------
* :func:`configure_logging` — call once at process start, idempotent.
* :func:`get_logger` — return a bound :class:`structlog.stdlib.BoundLogger`.

Usage::

    from src.utils.logger import configure_logging, get_logger

    configure_logging()
    log = get_logger(__name__)
    log.info("scan.start", instruments=42, threshold=70)
"""

from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from config import settings

_CONFIGURED: bool = False


def _drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Uvicorn injects a ``color_message`` field; we don't want it in JSON."""
    event_dict.pop("color_message", None)
    return event_dict


def _add_service_context(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Attach service-level identifiers to every record."""
    event_dict.setdefault("service", settings.app_name)
    event_dict.setdefault("env", settings.app_env.value)
    return event_dict


def _build_processors(*, json_output: bool) -> list[Processor]:
    """Return the processor chain for structlog.

    Parameters
    ----------
    json_output : bool
        When True, render the final event as JSON (production). When False,
        render with the colorized console renderer (development).
    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _drop_color_message_key,
        _add_service_context,
    ]

    if json_output:
        shared.append(structlog.processors.dict_tracebacks)
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(structlog.dev.ConsoleRenderer(colors=True))

    return shared


def configure_logging(
    *,
    level: str | None = None,
    json_output: bool | None = None,
    force: bool = False,
) -> None:
    """Configure ``structlog`` and the stdlib ``logging`` module.

    Idempotent unless ``force=True``. Subsequent calls without ``force`` are
    no-ops, which makes it safe to call from FastAPI lifespan, worker entry
    points, and tests.

    Parameters
    ----------
    level : str, optional
        Log level name (e.g. ``"INFO"``). Defaults to ``settings.app_log_level``.
    json_output : bool, optional
        Force JSON output on/off. When ``None`` we emit JSON unless we are
        in the development environment.
    force : bool
        Re-run configuration even if already configured.
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED and not force:
        return

    resolved_level: str = (level or settings.app_log_level).upper()
    use_json: bool = json_output if json_output is not None else (not settings.is_development)

    processors = _build_processors(json_output=use_json)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging._nameToLevel[resolved_level]
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Pipe stdlib logging (uvicorn, sqlalchemy, etc.) through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=_build_processors(json_output=use_json)[:-1],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                processors[-1],
            ],
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)

    # Quiet down chatty third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(
            logging.WARNING if resolved_level != "DEBUG" else logging.INFO
        )

    _CONFIGURED = True


def get_logger(name: str | None = None, **initial_values: Any) -> structlog.stdlib.BoundLogger:
    """Return a logger bound with optional initial context.

    Parameters
    ----------
    name : str, optional
        Logger name (typically ``__name__``).
    **initial_values
        Key/value pairs that will appear on every record emitted by this
        logger instance (e.g. ``request_id=...``).
    """
    if not _CONFIGURED:
        configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    if initial_values:
        logger = logger.bind(**initial_values)
    return logger
