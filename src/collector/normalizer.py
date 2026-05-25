"""Convert raw OKX JSON payloads into normalized Pydantic schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from src.schemas.market import (
    NormalizedCandle,
    NormalizedFundingRate,
    NormalizedInstrument,
    NormalizedTicker,
)
from src.utils.logger import get_logger

log = get_logger(__name__)

_MS_EPOCH_THRESHOLD = 10**12


def _parse_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Parse a string/number into :class:`Decimal`, returning *default* on failure."""
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def calc_oi_change_pct(history_rows: list[list[Any]], *, lookback: int = 1) -> float | None:
    """Compute percent OI change between latest and *lookback* rows ago."""
    if len(history_rows) <= lookback:
        return None
    try:
        latest = Decimal(str(history_rows[0][1]))
        prior = Decimal(str(history_rows[lookback][1]))
    except (IndexError, InvalidOperation, ValueError, TypeError):
        return None
    if prior <= 0:
        return None
    return float((latest - prior) / prior * Decimal("100"))


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse OKX millisecond epoch string/int into timezone-aware UTC datetime."""
    if value is None or value == "":
        return None
    try:
        ms = int(value)
        if ms < _MS_EPOCH_THRESHOLD:
            ms *= 1000
        return datetime.fromtimestamp(ms / 1000.0, tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def _require_str(raw: dict[str, Any], key: str) -> str:
    """Return a non-empty string field or raise."""
    value = raw.get(key)
    if not value:
        raise ValueError(f"missing required field: {key}")
    return str(value)


def normalize_instrument(raw: dict[str, Any]) -> NormalizedInstrument:
    """Convert an OKX ``/public/instruments`` row into :class:`NormalizedInstrument`."""
    inst_id = _require_str(raw, "instId")
    inst_type = _require_str(raw, "instType")

    tick_size = _parse_decimal(raw.get("tickSz"))
    lot_size = _parse_decimal(raw.get("lotSz"))
    min_size = _parse_decimal(raw.get("minSz"))
    if tick_size is None or lot_size is None or min_size is None:
        log.warning(
            "normalizer.instrument.invalid_sizes",
            inst_id=inst_id,
            tickSz=raw.get("tickSz"),
            lotSz=raw.get("lotSz"),
            minSz=raw.get("minSz"),
        )
        raise ValueError(f"invalid size fields for instrument {inst_id}")

    state = str(raw.get("state", "live")).lower()
    is_active = state == "live"

    if state not in ("live", "suspend", "preopen", "test"):
        log.warning("normalizer.instrument.unknown_state", inst_id=inst_id, state=state)

    base_ccy = str(raw.get("baseCcy") or inst_id.split("-")[0])
    quote_raw = raw.get("quoteCcy") or raw.get("settleCcy")
    if quote_raw:
        quote_ccy = str(quote_raw)
    elif inst_id.endswith("-SWAP") and len(inst_id.split("-")) >= 3:
        quote_ccy = inst_id.split("-")[1]
    else:
        quote_ccy = inst_id.split("-")[-1]

    return NormalizedInstrument(
        inst_id=inst_id,
        inst_type=inst_type,
        base_ccy=base_ccy,
        quote_ccy=quote_ccy,
        settle_ccy=str(raw["settleCcy"]) if raw.get("settleCcy") else None,
        tick_size=tick_size,
        lot_size=lot_size,
        min_size=min_size,
        contract_value=_parse_decimal(raw.get("ctVal")),
        is_active=is_active,
        listed_at=_parse_timestamp(raw.get("listTime")),
        expiry_at=_parse_timestamp(raw.get("expTime")),
    )


def normalize_ticker(raw: dict[str, Any]) -> NormalizedTicker:
    """Convert an OKX ticker row into :class:`NormalizedTicker`."""
    inst_id = _require_str(raw, "instId")
    last_price = _parse_decimal(raw.get("last"))
    if last_price is None:
        log.warning("normalizer.ticker.missing_last", inst_id=inst_id, raw_last=raw.get("last"))
        raise ValueError(f"missing last price for ticker {inst_id}")

    if last_price <= 0:
        log.warning("normalizer.ticker.non_positive_last", inst_id=inst_id, last=str(last_price))

    vol_base = _parse_decimal(raw.get("vol24h"))
    if vol_base is not None and vol_base == 0:
        log.warning("normalizer.ticker.zero_volume", inst_id=inst_id)

    return NormalizedTicker(
        inst_id=inst_id,
        last_price=last_price,
        bid_price=_parse_decimal(raw.get("bidPx")),
        ask_price=_parse_decimal(raw.get("askPx")),
        bid_size=_parse_decimal(raw.get("bidSz")),
        ask_size=_parse_decimal(raw.get("askSz")),
        open_24h=_parse_decimal(raw.get("open24h")),
        high_24h=_parse_decimal(raw.get("high24h")),
        low_24h=_parse_decimal(raw.get("low24h")),
        volume_24h_base=vol_base,
        volume_24h_quote=_parse_decimal(raw.get("volCcy24h")),
        timestamp=_parse_timestamp(raw.get("ts")),
    )


def normalize_candle(raw: dict[str, Any], symbol: str, timeframe: str) -> NormalizedCandle:
    """Convert an OKX candle row into :class:`NormalizedCandle`."""
    open_time = _parse_timestamp(raw.get("ts"))
    open_px = _parse_decimal(raw.get("o"))
    high_px = _parse_decimal(raw.get("h"))
    low_px = _parse_decimal(raw.get("l"))
    close_px = _parse_decimal(raw.get("c"))
    volume = _parse_decimal(raw.get("vol"), Decimal("0"))

    if open_time is None or None in (open_px, high_px, low_px, close_px):
        log.warning(
            "normalizer.candle.invalid_ohlc",
            symbol=symbol,
            timeframe=timeframe,
            raw=raw,
        )
        raise ValueError(f"invalid candle OHLC for {symbol} {timeframe}")

    if high_px < low_px:  # type: ignore[operator]
        log.warning(
            "normalizer.candle.high_below_low",
            symbol=symbol,
            high=str(high_px),
            low=str(low_px),
        )

    confirm_raw = raw.get("confirm")
    confirm = str(confirm_raw) == "1" if confirm_raw is not None else True

    return NormalizedCandle(
        inst_id=symbol,
        timeframe=timeframe,
        open_time=open_time,
        open=open_px,
        high=high_px,
        low=low_px,
        close=close_px,
        volume=volume or Decimal("0"),
        volume_quote=_parse_decimal(raw.get("volCcy")),
        confirm=confirm,
    )


def normalize_funding_rate(raw: dict[str, Any]) -> NormalizedFundingRate:
    """Convert an OKX funding-rate row into :class:`NormalizedFundingRate`."""
    inst_id = _require_str(raw, "instId")
    funding_rate = _parse_decimal(raw.get("fundingRate"))
    funding_time = _parse_timestamp(raw.get("fundingTime"))

    if funding_rate is None or funding_time is None:
        log.warning(
            "normalizer.funding_rate.invalid",
            inst_id=inst_id,
            fundingRate=raw.get("fundingRate"),
            fundingTime=raw.get("fundingTime"),
        )
        raise ValueError(f"invalid funding rate for {inst_id}")

    return NormalizedFundingRate(
        inst_id=inst_id,
        funding_rate=funding_rate,
        funding_time=funding_time,
        next_funding_rate=_parse_decimal(raw.get("nextFundingRate")),
        next_funding_time=_parse_timestamp(raw.get("nextFundingTime")),
    )


def candle_array_to_dict(row: list[Any]) -> dict[str, Any]:
    """Map OKX candle array ``[ts,o,h,l,c,vol,…]`` to a dict for normalization."""
    if len(row) < 6:
        raise ValueError(f"candle array too short: {row!r}")
    keys = ["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
    return {keys[i]: row[i] for i in range(min(len(row), len(keys)))}
