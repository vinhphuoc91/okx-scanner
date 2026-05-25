#!/usr/bin/env python3
"""Seed the ``instruments`` table from OKX public REST API.

Fetches SPOT + SWAP instruments, filters USDT quote pairs, and upserts
into PostgreSQL.

Usage::

    python scripts/seed_instruments.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from sqlalchemy.engine.url import make_url

from config.settings import get_settings
from src.collector.normalizer import normalize_instrument
from src.collector.rest_client import OKXRestClient
from src.db.models import Instrument, InstrumentType
from src.db.session import dispose_engine, get_session_factory
from src.utils.logger import configure_logging, get_logger

log = get_logger(__name__)

_USDT = "USDT"
_INST_TYPES = ("SPOT", "SWAP")


def _is_target_quote(raw: dict, quote_ccy: str) -> bool:
    """Return True for USDT SPOT pairs and USDT-margined SWAP contracts."""
    target = quote_ccy.upper()
    quote = str(raw.get("quoteCcy", "")).upper()
    settle = str(raw.get("settleCcy", "")).upper()
    inst_id = str(raw.get("instId", "")).upper()

    if quote == target or settle == target:
        return True
    if inst_id.endswith(f"-{target}"):
        return True
    # OKX perpetuals use instId like BTC-USDT-SWAP (quote is USDT, suffix is SWAP)
    return inst_id.endswith(f"-{target}-SWAP")


def _to_instrument_type(value: str) -> InstrumentType:
    """Map OKX instType string to ORM enum."""
    try:
        return InstrumentType(value.upper())
    except ValueError:
        log.warning("seed.unknown_inst_type", inst_type=value)
        return InstrumentType.SPOT


def _upsert_instrument(session, normalized, existing: Instrument | None) -> str:
    """Insert or update one instrument row. Returns ``inserted`` or ``updated``."""
    now = datetime.now(tz=UTC)
    if existing is None:
        row = Instrument(
            inst_id=normalized.inst_id,
            inst_type=_to_instrument_type(normalized.inst_type),
            base_ccy=normalized.base_ccy,
            quote_ccy=normalized.quote_ccy,
            settle_ccy=normalized.settle_ccy,
            tick_size=normalized.tick_size,
            lot_size=normalized.lot_size,
            min_size=normalized.min_size,
            contract_value=normalized.contract_value,
            is_active=normalized.is_active,
            listed_at=normalized.listed_at,
            expiry_at=normalized.expiry_at,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return "inserted"

    existing.inst_type = _to_instrument_type(normalized.inst_type)
    existing.base_ccy = normalized.base_ccy
    existing.quote_ccy = normalized.quote_ccy
    existing.settle_ccy = normalized.settle_ccy
    existing.tick_size = Decimal(normalized.tick_size)
    existing.lot_size = Decimal(normalized.lot_size)
    existing.min_size = Decimal(normalized.min_size)
    existing.contract_value = (
        Decimal(normalized.contract_value) if normalized.contract_value is not None else None
    )
    existing.is_active = normalized.is_active
    existing.listed_at = normalized.listed_at
    existing.expiry_at = normalized.expiry_at
    existing.updated_at = now
    return "updated"


def seed_instruments(*, quote_ccy: str = _USDT) -> dict[str, int]:
    """Fetch and upsert USDT instruments. Returns count summary."""
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    factory = get_session_factory()
    session = factory()

    try:
        with OKXRestClient() as client:
            for inst_type in _INST_TYPES:
                raw_rows = client.get_instruments(inst_type)
                log.info("seed.fetch_complete", inst_type=inst_type, total=len(raw_rows))

                for raw in raw_rows:
                    inst_id = str(raw.get("instId", ""))
                    if not _is_target_quote(raw, quote_ccy):
                        skipped += 1
                        continue

                    try:
                        normalized = normalize_instrument(raw)
                    except ValueError:
                        log.warning("seed.normalize_failed", inst_id=inst_id)
                        errors += 1
                        continue

                    existing = session.scalar(
                        select(Instrument).where(Instrument.inst_id == normalized.inst_id)
                    )
                    action = _upsert_instrument(session, normalized, existing)
                    if action == "inserted":
                        inserted += 1
                    else:
                        updated += 1

        session.commit()
    except Exception:
        session.rollback()
        log.exception("seed.failed")
        raise
    finally:
        session.close()

    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "total_upserted": inserted + updated,
    }
    active = get_settings()
    log.info("seed.complete", **summary, quote_ccy=quote_ccy, env=active.app_env.value)
    return summary


def _refresh_settings() -> None:
    """Reload settings from the environment and reset the DB engine pool."""
    dispose_engine()
    get_settings.cache_clear()


def main() -> int:
    """CLI entry point."""
    configure_logging()
    _refresh_settings()
    settings = get_settings()
    db = make_url(settings.DATABASE_URL)
    log.info(
        "seed.db_config",
        host=db.host,
        port=db.port,
        database=db.database,
        source=settings.database_url_source,
    )
    try:
        summary = seed_instruments()
        print(
            f"Seeded instruments: {summary['inserted']} inserted, "
            f"{summary['updated']} updated, "
            f"{summary['skipped']} skipped, "
            f"{summary['errors']} errors"
        )
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
