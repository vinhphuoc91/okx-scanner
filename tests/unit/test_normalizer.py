"""Unit tests for OKX payload normalizers."""

from __future__ import annotations

import json
from datetime import datetime

from src.utils.compat import UTC
from decimal import Decimal
from pathlib import Path

import pytest

from src.collector.normalizer import (
    candle_array_to_dict,
    normalize_candle,
    normalize_funding_rate,
    normalize_instrument,
    normalize_ticker,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.unit
class TestNormalizeInstrument:
    def test_from_fixture(self) -> None:
        raw = _load("okx_instrument.json")
        result = normalize_instrument(raw)
        assert result.inst_id == "BTC-USDT"
        assert result.inst_type == "SPOT"
        assert result.base_ccy == "BTC"
        assert result.quote_ccy == "USDT"
        assert result.tick_size == Decimal("0.1")
        assert result.is_active is True
        assert result.listed_at == datetime(2020, 8, 10, 2, 26, 23, tzinfo=UTC)

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValueError, match="instId"):
            normalize_instrument({"instType": "SPOT"})

    def test_invalid_sizes_raises(self) -> None:
        raw = _load("okx_instrument.json")
        raw["tickSz"] = ""
        with pytest.raises(ValueError, match="invalid size"):
            normalize_instrument(raw)

    def test_suspend_state(self) -> None:
        raw = _load("okx_instrument.json")
        raw["state"] = "suspend"
        result = normalize_instrument(raw)
        assert result.is_active is False


@pytest.mark.unit
class TestNormalizeTicker:
    def test_from_fixture(self) -> None:
        raw = _load("okx_ticker.json")
        result = normalize_ticker(raw)
        assert result.inst_id == "ETH-USDT"
        assert result.last_price == Decimal("3500.12")
        assert result.volume_24h_base == Decimal("12345.678")

    def test_missing_last_raises(self) -> None:
        raw = _load("okx_ticker.json")
        del raw["last"]
        with pytest.raises(ValueError, match="last price"):
            normalize_ticker(raw)

    def test_zero_volume_does_not_crash(self) -> None:
        raw = _load("okx_ticker.json")
        raw["vol24h"] = "0"
        result = normalize_ticker(raw)
        assert result.volume_24h_base == Decimal("0")

    def test_extreme_price(self) -> None:
        raw = _load("okx_ticker.json")
        raw["last"] = "999999999.99999999"
        result = normalize_ticker(raw)
        assert result.last_price == Decimal("999999999.99999999")


@pytest.mark.unit
class TestNormalizeCandle:
    def test_from_fixture(self) -> None:
        raw = _load("okx_candle.json")
        result = normalize_candle(raw, symbol="ETH-USDT", timeframe="5m")
        assert result.inst_id == "ETH-USDT"
        assert result.timeframe == "5m"
        assert result.close == Decimal("3520.50")
        assert result.confirm is True

    def test_missing_ohlc_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid candle"):
            normalize_candle({"ts": "1716633600000"}, symbol="X", timeframe="5m")

    def test_candle_array_to_dict(self) -> None:
        row = ["1716633600000", "1", "2", "0.5", "1.5", "100", "100", "100", "1"]
        d = candle_array_to_dict(row)
        assert d["o"] == "1"
        assert d["confirm"] == "1"

    def test_high_below_low_still_parses(self) -> None:
        raw = _load("okx_candle.json")
        raw["h"] = "1"
        raw["l"] = "9999"
        result = normalize_candle(raw, symbol="ETH-USDT", timeframe="15m")
        assert result.high == Decimal("1")
        assert result.low == Decimal("9999")


@pytest.mark.unit
class TestNormalizeFundingRate:
    def test_from_fixture(self) -> None:
        raw = _load("okx_funding_rate.json")
        result = normalize_funding_rate(raw)
        assert result.inst_id == "BTC-USDT-SWAP"
        assert result.funding_rate == Decimal("0.0001")
        assert result.next_funding_rate == Decimal("0.00015")

    def test_missing_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid funding"):
            normalize_funding_rate({"instId": "BTC-USDT-SWAP"})
