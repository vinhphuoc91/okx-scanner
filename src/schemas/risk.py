"""Risk evaluation schemas."""

from __future__ import annotations

from src.utils.compat import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RejectionCode(StrEnum):
    """Machine-readable hard-reject reasons."""

    SPREAD_TOO_HIGH = "SPREAD_TOO_HIGH"
    LOW_VOLUME = "LOW_VOLUME"
    EXTREME_FUNDING = "EXTREME_FUNDING"
    SCORE_TOO_LOW = "SCORE_TOO_LOW"


class RiskDecision(BaseModel):
    """Outcome of the risk filter for one scored opportunity."""

    model_config = ConfigDict(frozen=True)

    approved: bool
    rejection_codes: tuple[RejectionCode, ...] = Field(default_factory=tuple)
    raw_checks: dict[str, Any] = Field(default_factory=dict)
    opportunity_id: int | None = None
