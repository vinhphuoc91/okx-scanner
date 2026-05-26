"""Strategy detection schemas."""

from __future__ import annotations

from datetime import datetime
from src.utils.compat import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyType(StrEnum):
    """Supported opportunity-detection strategies."""

    FUNDING = "FUNDING"
    MOMENTUM = "MOMENTUM"
    BREAKOUT = "BREAKOUT"
    VOLUME_ANOMALY = "VOLUME_ANOMALY"
    TREND_PULLBACK = "TREND_PULLBACK"
    CORRELATION_DIVERGENCE = "CORRELATION_DIVERGENCE"
    LIQUIDATION_ZONE = "LIQUIDATION_ZONE"
    STAT_ARBITRAGE = "STAT_ARBITRAGE"


class Direction(StrEnum):
    """Trade direction signal."""

    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class Candidate(BaseModel):
    """A trading opportunity detected by a strategy."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., description="OKX instId")
    strategy_type: StrategyType
    direction: Direction
    raw_signals: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)
