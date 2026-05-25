"""Schemas for market filtering and tier assignment."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FilteredInstrument(BaseModel):
    """An instrument that passed all market filters."""

    model_config = ConfigDict(frozen=True)

    inst_id: str
    inst_type: str = Field(..., description="SPOT or SWAP")
    volume_24h_usd: Decimal
    spread_pct: Decimal
    last_price: Decimal
    tier: int | None = Field(None, ge=1, le=3)
    scan_interval_seconds: int | None = Field(None, ge=1)


class FilterRejection(BaseModel):
    """A ticker rejected by the filter with explicit reasons."""

    model_config = ConfigDict(frozen=True)

    inst_id: str
    reasons: tuple[str, ...] = Field(..., min_length=1)


class FilterResult(BaseModel):
    """Outcome of :meth:`MarketFilter.filter_instruments`."""

    model_config = ConfigDict(frozen=True)

    passed: tuple[FilteredInstrument, ...]
    rejected: tuple[FilterRejection, ...]


class TieredInstruments(BaseModel):
    """Instruments partitioned into scan tiers by 24 h volume rank."""

    model_config = ConfigDict(frozen=True)

    tier1: tuple[FilteredInstrument, ...]
    tier2: tuple[FilteredInstrument, ...]
    tier3: tuple[FilteredInstrument, ...]
