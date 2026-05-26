"""Scoring result schemas."""

from __future__ import annotations

from src.utils.compat import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.strategy import Candidate


class Grade(StrEnum):
    """Score grade bucket."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WATCH = "WATCH"
    IGNORE = "IGNORE"


class ScoreBreakdown(BaseModel):
    """Per-component score contributions."""

    model_config = ConfigDict(frozen=True)

    trend_score: float = Field(..., ge=0.0, le=30.0)
    momentum_score: float = Field(..., ge=0.0, le=25.0)
    liquidity_score: float = Field(..., ge=0.0, le=25.0)
    volume_score: float = Field(..., ge=0.0, le=20.0)
    funding_score: float = Field(..., ge=0.0, le=40.0)
    spread_score: float = Field(..., ge=0.0, le=20.0)
    risk_penalty: float = Field(..., ge=-25.0, le=0.0)

    @property
    def raw_total(self) -> float:
        """Sum before clamping to 0–100."""
        return (
            self.trend_score
            + self.momentum_score
            + self.liquidity_score
            + self.volume_score
            + self.funding_score
            + self.spread_score
            + self.risk_penalty
        )


class ScoredOpportunity(BaseModel):
    """Candidate enriched with multi-factor score."""

    model_config = ConfigDict(frozen=True)

    candidate: Candidate
    breakdown: ScoreBreakdown
    total_score: int = Field(..., ge=0, le=100)
    grade: Grade
    model_version: str = "v1"
    opportunity_id: int | None = None
