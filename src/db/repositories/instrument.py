"""Instrument repository — DB access for the instruments table."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Instrument
from src.utils.logger import get_logger

log = get_logger(__name__)


class InstrumentRepository:
    """CRUD helpers for :class:`~src.db.models.Instrument`."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to an ORM session."""
        self._session = session

    def update_instrument_tier(
        self,
        symbol: str,
        tier: int,
        *,
        scan_interval_seconds: int | None = None,
    ) -> Instrument | None:
        """Set scan tier (and optional interval) for *symbol*.

        Parameters
        ----------
        symbol:
            OKX ``instId`` (e.g. ``BTC-USDT``).
        tier:
            Tier number (1, 2, or 3).
        scan_interval_seconds:
            Optional scan cadence override for this instrument.

        Returns
        -------
        Instrument | None
            Updated row, or ``None`` when *symbol* is not found.
        """
        instrument = self._session.scalar(
            select(Instrument).where(Instrument.inst_id == symbol),
        )
        if instrument is None:
            log.warning("instrument.tier.not_found", symbol=symbol, tier=tier)
            return None

        instrument.tier = tier
        if scan_interval_seconds is not None:
            instrument.scan_interval_seconds = scan_interval_seconds
        instrument.updated_at = datetime.now(tz=timezone.utc)

        log.info(
            "instrument.tier.updated",
            symbol=symbol,
            tier=tier,
            scan_interval_seconds=scan_interval_seconds,
        )
        return instrument

    def get_active_instruments(self) -> list[Instrument]:
        """Return all active instruments ordered by ``inst_id``."""
        stmt = (
            select(Instrument)
            .where(Instrument.is_active.is_(True))
            .order_by(Instrument.inst_id)
        )
        return list(self._session.scalars(stmt).all())

    def get_instruments_by_tier(self, tier: int) -> list[Instrument]:
        """Return active instruments assigned to *tier*."""
        stmt = (
            select(Instrument)
            .where(Instrument.is_active.is_(True), Instrument.tier == tier)
            .order_by(Instrument.inst_id)
        )
        return list(self._session.scalars(stmt).all())
