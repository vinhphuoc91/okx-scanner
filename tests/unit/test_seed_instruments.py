"""Unit tests for instrument seeding helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_seed_path = Path(__file__).resolve().parents[2] / "scripts" / "seed_instruments.py"
_spec = importlib.util.spec_from_file_location("seed_instruments", _seed_path)
assert _spec and _spec.loader
_seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seed)
_is_target_quote = _seed._is_target_quote


@pytest.mark.unit
class TestIsTargetQuote:
    def test_accepts_spot_usdt(self) -> None:
        raw = {"instId": "BTC-USDT", "quoteCcy": "USDT"}
        assert _is_target_quote(raw, "USDT") is True

    def test_accepts_swap_usdt_margined(self) -> None:
        raw = {"instId": "BTC-USDT-SWAP", "settleCcy": "USDT"}
        assert _is_target_quote(raw, "USDT") is True

    def test_rejects_non_usdt(self) -> None:
        raw = {"instId": "BTC-USDC", "quoteCcy": "USDC"}
        assert _is_target_quote(raw, "USDT") is False
