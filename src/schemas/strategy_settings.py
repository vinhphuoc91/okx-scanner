"""Strategy risk profile settings schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StrategySettingsUpdate(BaseModel):
    """Partial update payload for one strategy."""

    is_enabled: bool | None = None
    min_score: int | None = Field(None, ge=50, le=95)
    max_concurrent: int | None = Field(None, ge=1, le=10)
    cooldown_hours: float | None = Field(None, ge=0.5, le=24)
    sensitivity: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    tp_tier1: float | None = Field(None, gt=0)
    tp_tier2: float | None = Field(None, gt=0)
    tp_tier3: float | None = Field(None, gt=0)
    sl_tier1: float | None = Field(None, gt=0)
    sl_tier2: float | None = Field(None, gt=0)
    sl_tier3: float | None = Field(None, gt=0)
    timeout_tier1: int | None = Field(None, ge=1, le=168)
    timeout_tier2: int | None = Field(None, ge=1, le=168)
    timeout_tier3: int | None = Field(None, ge=1, le=168)
    requires_confirmation: bool | None = None
    confirmation_candles: int | None = Field(None, ge=1, le=4)
    atr_sl_multiplier_t1: float | None = Field(None, gt=0)
    atr_sl_multiplier_t2: float | None = Field(None, gt=0)
    atr_sl_multiplier_t3: float | None = Field(None, gt=0)
    atr_tp_multiplier_t1: float | None = Field(None, gt=0)
    atr_tp_multiplier_t2: float | None = Field(None, gt=0)
    atr_tp_multiplier_t3: float | None = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_tp_sl_pairs(self) -> StrategySettingsUpdate:
        pct_pairs = [
            (self.tp_tier1, self.sl_tier1),
            (self.tp_tier2, self.sl_tier2),
            (self.tp_tier3, self.sl_tier3),
        ]
        for tp, sl in pct_pairs:
            if tp is not None and sl is not None and tp <= sl:
                raise ValueError("Take-profit must be greater than stop-loss for each tier")

        atr_pairs = [
            (self.atr_tp_multiplier_t1, self.atr_sl_multiplier_t1),
            (self.atr_tp_multiplier_t2, self.atr_sl_multiplier_t2),
            (self.atr_tp_multiplier_t3, self.atr_sl_multiplier_t3),
        ]
        for tp, sl in atr_pairs:
            if tp is not None and sl is not None and tp <= sl:
                raise ValueError("ATR take-profit multiplier must exceed stop-loss multiplier for each tier")
        return self


class GlobalSettingsUpdate(BaseModel):
    """Update payload for global scanner settings."""

    max_total_concurrent_trades: int | None = Field(None, ge=5, le=50)
    alert_min_score: int | None = Field(None, ge=50, le=95)
    auto_refresh_interval_seconds: int | None = Field(None, ge=5, le=300)
