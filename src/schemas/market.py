"""Normalized market-data schemas (Pydantic v2).

These models represent OKX REST/WS payloads after normalization — the
canonical shape used by the collector, cache, and downstream pipeline.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedInstrument(BaseModel):
    """A tradable OKX instrument (spot, swap, etc.)."""

    model_config = ConfigDict(frozen=True)

    inst_id: str = Field(..., description="OKX instrument id, e.g. BTC-USDT")
    inst_type: str = Field(..., description="SPOT | SWAP | FUTURES | …")
    base_ccy: str
    quote_ccy: str
    settle_ccy: str | None = None
    tick_size: Decimal
    lot_size: Decimal
    min_size: Decimal
    contract_value: Decimal | None = None
    is_active: bool = True
    listed_at: datetime | None = None
    expiry_at: datetime | None = None


class NormalizedTicker(BaseModel):
    """Latest ticker snapshot for one instrument."""

    model_config = ConfigDict(frozen=True)

    inst_id: str
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    open_24h: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    volume_24h_base: Decimal | None = None
    volume_24h_quote: Decimal | None = None
    timestamp: datetime | None = None


class NormalizedCandle(BaseModel):
    """Single OHLCV candle bar."""

    model_config = ConfigDict(frozen=True)

    inst_id: str
    timeframe: str = Field(..., description="Bar size, e.g. 5m, 15m, 1H")
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    volume_quote: Decimal | None = None
    confirm: bool = True


class NormalizedFundingRate(BaseModel):
    """Perpetual-swap funding rate snapshot."""

    model_config = ConfigDict(frozen=True)

    inst_id: str
    funding_rate: Decimal
    funding_time: datetime
    next_funding_rate: Decimal | None = None
    next_funding_time: datetime | None = None
