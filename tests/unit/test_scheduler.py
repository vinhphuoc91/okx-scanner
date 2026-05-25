"""Unit tests for TierScheduler."""

from __future__ import annotations

import pytest

from config.settings import Settings
from src.worker.scheduler import TierScheduler


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "filter_tier1_interval_seconds": 60,
        "filter_tier2_interval_seconds": 300,
        "filter_tier3_interval_seconds": 900,
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


@pytest.mark.unit
class TestTierScheduler:
    def test_all_tiers_due_initially(self) -> None:
        scheduler = TierScheduler(settings=_settings())
        assert scheduler.get_due_tiers(now=0.0) == [1, 2, 3]

    def test_tier1_due_after_60s(self) -> None:
        scheduler = TierScheduler(settings=_settings())
        scheduler.mark_scanned(1, now=0.0)
        assert 1 not in scheduler.get_due_tiers(now=59.0)
        assert 1 in scheduler.get_due_tiers(now=60.0)

    def test_tier2_due_after_300s(self) -> None:
        scheduler = TierScheduler(settings=_settings())
        scheduler.mark_scanned(2, now=0.0)
        assert 2 not in scheduler.get_due_tiers(now=299.0)
        assert 2 in scheduler.get_due_tiers(now=300.0)

    def test_not_due_before_interval(self) -> None:
        scheduler = TierScheduler(settings=_settings())
        scheduler.mark_scanned(1, now=100.0)
        scheduler.mark_scanned(2, now=100.0)
        scheduler.mark_scanned(3, now=100.0)
        assert scheduler.get_due_tiers(now=150.0) == []

    def test_tier3_due_after_900s(self) -> None:
        scheduler = TierScheduler(settings=_settings())
        scheduler.mark_scanned(3, now=0.0)
        assert 3 not in scheduler.get_due_tiers(now=899.0)
        assert 3 in scheduler.get_due_tiers(now=900.0)
