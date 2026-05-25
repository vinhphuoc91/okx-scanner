"""Unit tests for strategy settings repository."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base, StrategySensitivity, StrategySettings, SystemConfig
from src.db.repositories.strategy_settings import (
    DEFAULT_STRATEGY_SETTINGS,
    StrategySettingsRepository,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[StrategySettings.__table__, SystemConfig.__table__],
    )
    factory = sessionmaker(bind=engine)
    sess = factory()
    now_fields = {}
    for idx, (strategy_type, defaults) in enumerate(DEFAULT_STRATEGY_SETTINGS.items(), start=1):
        row = StrategySettings(
            id=idx,
            strategy_type=strategy_type,
            cooldown_hours=Decimal(str(defaults["cooldown_hours"])),
            tp_tier1=Decimal(str(defaults["tp_tier1"])),
            tp_tier2=Decimal(str(defaults["tp_tier2"])),
            tp_tier3=Decimal(str(defaults["tp_tier3"])),
            sl_tier1=Decimal(str(defaults["sl_tier1"])),
            sl_tier2=Decimal(str(defaults["sl_tier2"])),
            sl_tier3=Decimal(str(defaults["sl_tier3"])),
            **{k: v for k, v in defaults.items() if k not in {
                "cooldown_hours", "tp_tier1", "tp_tier2", "tp_tier3",
                "sl_tier1", "sl_tier2", "sl_tier3",
            }},
        )
        sess.add(row)
    sess.add(SystemConfig(id=1, max_total_concurrent_trades=5, alert_min_score=65, auto_refresh_interval_seconds=10))
    sess.commit()
    yield sess
    sess.close()


@pytest.mark.unit
class TestStrategySettingsRepository:
    def test_get_all_settings(self, session: Session) -> None:
        repo = StrategySettingsRepository(session)
        all_settings = repo.get_all_settings()
        assert len(all_settings) == 5
        assert all_settings["FUNDING"].min_score == 70

    def test_update_settings(self, session: Session) -> None:
        repo = StrategySettingsRepository(session)
        updated = repo.update_settings("FUNDING", min_score=72, max_concurrent=5)
        assert updated.min_score == 72
        assert updated.max_concurrent == 5

    def test_tier_params(self, session: Session) -> None:
        repo = StrategySettingsRepository(session)
        row = repo.get_settings("MOMENTUM")
        assert row is not None
        params = row.tier_params(2)
        assert params["tp_pct"] == 4.0
        assert params["sl_pct"] == 2.0
        assert params["timeout_hours"] == 12

    def test_reject_tp_below_sl(self, session: Session) -> None:
        repo = StrategySettingsRepository(session)
        with pytest.raises(ValueError, match="take-profit"):
            repo.update_settings("FUNDING", tp_tier1=1.0, sl_tier1=2.0)

    def test_reset_to_defaults(self, session: Session) -> None:
        repo = StrategySettingsRepository(session)
        repo.update_settings("BREAKOUT", min_score=80)
        repo.reset_to_defaults()
        row = repo.get_settings("BREAKOUT")
        assert row is not None
        assert row.min_score == 78
        assert row.sensitivity == StrategySensitivity.LOW
