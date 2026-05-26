"""Strategy settings repository — per-strategy risk profiles."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import StrategySensitivity, StrategySettings, SystemConfig
from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_STRATEGY_SETTINGS: dict[str, dict[str, Any]] = {
    "FUNDING": {
        "is_enabled": True,
        "min_score": 70,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": StrategySensitivity.MEDIUM,
        "tp_tier1": 2.0, "tp_tier2": 3.0, "tp_tier3": 4.0,
        "sl_tier1": 1.0, "sl_tier2": 1.5, "sl_tier3": 2.0,
        "timeout_tier1": 8, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5, "atr_sl_multiplier_t2": 2.0, "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0, "atr_tp_multiplier_t2": 4.0, "atr_tp_multiplier_t3": 5.0,
    },
    "MOMENTUM": {
        "is_enabled": True,
        "min_score": 75,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": StrategySensitivity.MEDIUM,
        "tp_tier1": 3.0, "tp_tier2": 4.0, "tp_tier3": 5.0,
        "sl_tier1": 1.5, "sl_tier2": 2.0, "sl_tier3": 2.5,
        "timeout_tier1": 8, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": True,
        "confirmation_candles": 2,
        "atr_sl_multiplier_t1": 2.0, "atr_sl_multiplier_t2": 2.5, "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0, "atr_tp_multiplier_t2": 5.0, "atr_tp_multiplier_t3": 6.0,
    },
    "BREAKOUT": {
        "is_enabled": True,
        "min_score": 78,
        "max_concurrent": 2,
        "cooldown_hours": 4.0,
        "sensitivity": StrategySensitivity.LOW,
        "tp_tier1": 4.0, "tp_tier2": 6.0, "tp_tier3": 8.0,
        "sl_tier1": 2.0, "sl_tier2": 3.0, "sl_tier3": 4.0,
        "timeout_tier1": 6, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": True,
        "confirmation_candles": 2,
        "atr_sl_multiplier_t1": 2.5, "atr_sl_multiplier_t2": 3.0, "atr_sl_multiplier_t3": 3.5,
        "atr_tp_multiplier_t1": 5.0, "atr_tp_multiplier_t2": 6.0, "atr_tp_multiplier_t3": 7.0,
    },
    "VOLUME_ANOMALY": {
        "is_enabled": True,
        "min_score": 72,
        "max_concurrent": 2,
        "cooldown_hours": 1.0,
        "sensitivity": StrategySensitivity.HIGH,
        "tp_tier1": 3.0, "tp_tier2": 5.0, "tp_tier3": 7.0,
        "sl_tier1": 1.5, "sl_tier2": 2.5, "sl_tier3": 3.5,
        "timeout_tier1": 4, "timeout_tier2": 8, "timeout_tier3": 12,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5, "atr_sl_multiplier_t2": 2.0, "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0, "atr_tp_multiplier_t2": 4.0, "atr_tp_multiplier_t3": 5.0,
    },
    "TREND_PULLBACK": {
        "is_enabled": True,
        "min_score": 75,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": StrategySensitivity.MEDIUM,
        "tp_tier1": 3.0, "tp_tier2": 4.0, "tp_tier3": 5.0,
        "sl_tier1": 1.5, "sl_tier2": 2.0, "sl_tier3": 2.5,
        "timeout_tier1": 8, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": True,
        "confirmation_candles": 2,
        "atr_sl_multiplier_t1": 2.0, "atr_sl_multiplier_t2": 2.5, "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0, "atr_tp_multiplier_t2": 5.0, "atr_tp_multiplier_t3": 6.0,
    },
    "CORRELATION_DIVERGENCE": {
        "is_enabled": True,
        "min_score": 70,
        "max_concurrent": 3,
        "cooldown_hours": 2.0,
        "sensitivity": StrategySensitivity.MEDIUM,
        "tp_tier1": 3.0, "tp_tier2": 4.0, "tp_tier3": 5.0,
        "sl_tier1": 1.5, "sl_tier2": 2.0, "sl_tier3": 2.5,
        "timeout_tier1": 8, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.5, "atr_sl_multiplier_t2": 2.0, "atr_sl_multiplier_t3": 2.5,
        "atr_tp_multiplier_t1": 3.0, "atr_tp_multiplier_t2": 4.0, "atr_tp_multiplier_t3": 5.0,
    },
    "LIQUIDATION_ZONE": {
        "is_enabled": True,
        "min_score": 75,
        "max_concurrent": 2,
        "cooldown_hours": 4.0,
        "sensitivity": StrategySensitivity.LOW,
        "tp_tier1": 4.0, "tp_tier2": 5.0, "tp_tier3": 6.0,
        "sl_tier1": 2.0, "sl_tier2": 2.5, "sl_tier3": 3.0,
        "timeout_tier1": 8, "timeout_tier2": 12, "timeout_tier3": 24,
        "requires_confirmation": True,
        "confirmation_candles": 2,
        "atr_sl_multiplier_t1": 2.0, "atr_sl_multiplier_t2": 2.5, "atr_sl_multiplier_t3": 3.0,
        "atr_tp_multiplier_t1": 4.0, "atr_tp_multiplier_t2": 5.0, "atr_tp_multiplier_t3": 6.0,
    },
    "STAT_ARBITRAGE": {
        "is_enabled": True,
        "min_score": 72,
        "max_concurrent": 3,
        "cooldown_hours": 1.0,
        "sensitivity": StrategySensitivity.MEDIUM,
        "tp_tier1": 2.0, "tp_tier2": 3.0, "tp_tier3": 4.0,
        "sl_tier1": 1.0, "sl_tier2": 1.5, "sl_tier3": 2.0,
        "timeout_tier1": 6, "timeout_tier2": 8, "timeout_tier3": 12,
        "requires_confirmation": False,
        "confirmation_candles": 1,
        "atr_sl_multiplier_t1": 1.0, "atr_sl_multiplier_t2": 1.5, "atr_sl_multiplier_t3": 2.0,
        "atr_tp_multiplier_t1": 2.0, "atr_tp_multiplier_t2": 3.0, "atr_tp_multiplier_t3": 4.0,
    },
}

DEFAULT_GLOBAL_CONFIG = {
    "max_total_concurrent_trades": 5,
    "alert_min_score": 65,
    "auto_refresh_interval_seconds": 10,
}


def _decimal(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


class StrategySettingsRepository:
    """CRUD helpers for strategy risk profiles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all_settings(self) -> dict[str, StrategySettings]:
        """Return all strategy settings keyed by strategy type."""
        rows = self._session.scalars(
            select(StrategySettings).order_by(StrategySettings.strategy_type),
        ).all()
        return {row.strategy_type: row for row in rows}

    def get_settings(self, strategy_type: str) -> StrategySettings | None:
        """Return settings for one strategy."""
        return self._session.scalar(
            select(StrategySettings).where(
                StrategySettings.strategy_type == strategy_type.upper(),
            ),
        )

    def get_global_config(self) -> SystemConfig:
        """Return singleton global config (creates default if missing)."""
        row = self._session.get(SystemConfig, 1)
        if row is None:
            row = SystemConfig(id=1, **DEFAULT_GLOBAL_CONFIG)
            self._session.add(row)
            self._session.flush()
        return row

    def update_settings(self, strategy_type: str, **kwargs: Any) -> StrategySettings:
        """Update one strategy's settings."""
        key = strategy_type.upper()
        row = self.get_settings(key)
        if row is None:
            raise KeyError(f"Unknown strategy: {key}")

        if "sensitivity" in kwargs and isinstance(kwargs["sensitivity"], str):
            kwargs["sensitivity"] = StrategySensitivity(kwargs["sensitivity"])

        merged = {
            "tp_tier1": float(row.tp_tier1),
            "sl_tier1": float(row.sl_tier1),
            "tp_tier2": float(row.tp_tier2),
            "sl_tier2": float(row.sl_tier2),
            "tp_tier3": float(row.tp_tier3),
            "sl_tier3": float(row.sl_tier3),
            "atr_tp_multiplier_t1": float(row.atr_tp_multiplier_t1),
            "atr_sl_multiplier_t1": float(row.atr_sl_multiplier_t1),
            "atr_tp_multiplier_t2": float(row.atr_tp_multiplier_t2),
            "atr_sl_multiplier_t2": float(row.atr_sl_multiplier_t2),
            "atr_tp_multiplier_t3": float(row.atr_tp_multiplier_t3),
            "atr_sl_multiplier_t3": float(row.atr_sl_multiplier_t3),
        }
        for field in kwargs:
            if field.startswith(("tp_tier", "sl_tier", "atr_tp_multiplier", "atr_sl_multiplier")):
                merged[field] = float(kwargs[field])

        for tier in (1, 2, 3):
            tp = merged.get(f"tp_tier{tier}")
            sl = merged.get(f"sl_tier{tier}")
            if tp is not None and sl is not None and tp <= sl:
                raise ValueError(f"Tier {tier}: take-profit must exceed stop-loss")
            atr_tp = merged.get(f"atr_tp_multiplier_t{tier}")
            atr_sl = merged.get(f"atr_sl_multiplier_t{tier}")
            if atr_tp is not None and atr_sl is not None and atr_tp <= atr_sl:
                raise ValueError(f"Tier {tier}: ATR TP multiplier must exceed SL multiplier")

        decimal_fields = {
            "tp_tier1", "tp_tier2", "tp_tier3", "sl_tier1", "sl_tier2", "sl_tier3",
            "atr_sl_multiplier_t1", "atr_sl_multiplier_t2", "atr_sl_multiplier_t3",
            "atr_tp_multiplier_t1", "atr_tp_multiplier_t2", "atr_tp_multiplier_t3",
        }
        for field, value in kwargs.items():
            if field == "cooldown_hours":
                setattr(row, field, _decimal(value))
            elif field in decimal_fields:
                setattr(row, field, _decimal(value))
            else:
                setattr(row, field, value)

        row.updated_at = datetime.now(tz=timezone.utc)
        self._session.flush()
        log.info("strategy_settings.updated", strategy=key, fields=list(kwargs.keys()))
        return row

    def update_global_config(self, **kwargs: Any) -> SystemConfig:
        """Update global scanner settings."""
        row = self.get_global_config()
        for field, value in kwargs.items():
            setattr(row, field, value)
        row.updated_at = datetime.now(tz=timezone.utc)
        self._session.flush()
        log.info("system_config.updated", fields=list(kwargs.keys()))
        return row

    def reset_to_defaults(self) -> dict[str, StrategySettings]:
        """Reset all strategies to factory defaults."""
        result: dict[str, StrategySettings] = {}
        for strategy_type, defaults in DEFAULT_STRATEGY_SETTINGS.items():
            row = self.get_settings(strategy_type)
            if row is None:
                continue
            for field, value in defaults.items():
                if field in {
                    "tp_tier1", "tp_tier2", "tp_tier3", "sl_tier1", "sl_tier2", "sl_tier3",
                    "atr_sl_multiplier_t1", "atr_sl_multiplier_t2", "atr_sl_multiplier_t3",
                    "atr_tp_multiplier_t1", "atr_tp_multiplier_t2", "atr_tp_multiplier_t3",
                }:
                    setattr(row, field, _decimal(value))
                elif field == "cooldown_hours":
                    setattr(row, field, _decimal(value))
                else:
                    setattr(row, field, value)
            row.updated_at = datetime.now(tz=timezone.utc)
            result[strategy_type] = row

        global_row = self.get_global_config()
        for field, value in DEFAULT_GLOBAL_CONFIG.items():
            setattr(global_row, field, value)
        global_row.updated_at = datetime.now(tz=timezone.utc)

        self._session.flush()
        log.info("strategy_settings.reset")
        return result

    @staticmethod
    def to_dict(row: StrategySettings) -> dict[str, Any]:
        return {
            "strategy_type": row.strategy_type,
            "is_enabled": row.is_enabled,
            "min_score": row.min_score,
            "max_concurrent": row.max_concurrent,
            "cooldown_hours": float(row.cooldown_hours),
            "sensitivity": row.sensitivity.value,
            "tp_tier1": float(row.tp_tier1),
            "tp_tier2": float(row.tp_tier2),
            "tp_tier3": float(row.tp_tier3),
            "sl_tier1": float(row.sl_tier1),
            "sl_tier2": float(row.sl_tier2),
            "sl_tier3": float(row.sl_tier3),
            "timeout_tier1": row.timeout_tier1,
            "timeout_tier2": row.timeout_tier2,
            "timeout_tier3": row.timeout_tier3,
            "requires_confirmation": row.requires_confirmation,
            "confirmation_candles": row.confirmation_candles,
            "atr_sl_multiplier_t1": float(row.atr_sl_multiplier_t1),
            "atr_sl_multiplier_t2": float(row.atr_sl_multiplier_t2),
            "atr_sl_multiplier_t3": float(row.atr_sl_multiplier_t3),
            "atr_tp_multiplier_t1": float(row.atr_tp_multiplier_t1),
            "atr_tp_multiplier_t2": float(row.atr_tp_multiplier_t2),
            "atr_tp_multiplier_t3": float(row.atr_tp_multiplier_t3),
            "updated_at": row.updated_at.isoformat(),
        }

    @staticmethod
    def global_to_dict(row: SystemConfig) -> dict[str, Any]:
        return {
            "max_total_concurrent_trades": row.max_total_concurrent_trades,
            "alert_min_score": row.alert_min_score,
            "auto_refresh_interval_seconds": row.auto_refresh_interval_seconds,
            "updated_at": row.updated_at.isoformat(),
        }
