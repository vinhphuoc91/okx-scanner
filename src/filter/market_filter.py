"""Config-driven market filter and volume-based tier assignment."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from config.settings import Settings, get_settings
from src.schemas.filter import (
    FilteredInstrument,
    FilterRejection,
    FilterResult,
    TieredInstruments,
)
from src.schemas.market import NormalizedInstrument, NormalizedTicker
from src.utils.logger import get_logger

log = get_logger(__name__)

_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


def _infer_inst_type(inst_id: str) -> str:
    """Infer OKX instrument type from ``instId`` naming convention."""
    if inst_id.endswith("-SWAP"):
        return "SWAP"
    return "SPOT"


def _is_usdt_pair(inst_id: str, quote_currencies: frozenset[str]) -> bool:
    """Return True when *inst_id* is a USDT-quoted pair."""
    for quote in quote_currencies:
        if inst_id.endswith(f"-{quote}") or inst_id.endswith(f"-{quote}-SWAP"):
            return True
    return False


def _compute_spread_pct(bid: Decimal | None, ask: Decimal | None) -> Decimal | None:
    """Compute bid-ask spread as a percentage of mid price."""
    if bid is None or ask is None or bid <= _ZERO or ask <= _ZERO:
        return None
    if ask < bid:
        return None
    mid = (bid + ask) / Decimal("2")
    if mid <= _ZERO:
        return None
    return (ask - bid) / mid * _HUNDRED


def _volume_24h_usd(ticker: NormalizedTicker) -> Decimal | None:
    """Return 24 h quote volume as USD proxy (USDT ≈ USD)."""
    if ticker.volume_24h_quote is not None:
        return ticker.volume_24h_quote
    if ticker.volume_24h_base is not None and ticker.last_price > _ZERO:
        return ticker.volume_24h_base * ticker.last_price
    return None


class MarketFilter:
    """Filter tickers and assign scan tiers by 24 h volume.

    All thresholds are read from :class:`config.settings.Settings`.
    Methods are deterministic for a fixed ``reference_time`` and metadata map.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        instrument_metadata: Mapping[str, NormalizedInstrument] | None = None,
        reference_time: datetime | None = None,
    ) -> None:
        """Initialize the filter.

        Parameters
        ----------
        settings:
            Application settings (defaults to cached singleton).
        instrument_metadata:
            Optional map of ``inst_id`` → :class:`NormalizedInstrument` for
            listing-age and type checks beyond ticker data.
        reference_time:
            Fixed "now" for listing-age checks (defaults to UTC now).
        """
        self._settings = settings or get_settings()
        self._metadata = instrument_metadata or {}
        self._reference_time = reference_time or datetime.now(tz=timezone.utc)

    @property
    def _quote_currencies(self) -> frozenset[str]:
        return frozenset(self._settings.filter_quote_currency_list)

    @property
    def _allowed_inst_types(self) -> frozenset[str]:
        return frozenset(self._settings.filter_inst_type_list)

    def filter_instruments(self, tickers: list[NormalizedTicker]) -> FilterResult:
        """Apply all filter rules to *tickers*.

        Parameters
        ----------
        tickers:
            Normalized ticker snapshots (typically from OKX REST/WS).

        Returns
        -------
        FilterResult
            Passed instruments and rejected items with reasons.
        """
        passed: list[FilteredInstrument] = []
        rejected: list[FilterRejection] = []

        for ticker in tickers:
            reasons = self._evaluate(ticker)
            if reasons:
                rejection = FilterRejection(inst_id=ticker.inst_id, reasons=tuple(reasons))
                rejected.append(rejection)
                log.info(
                    "filter.rejected",
                    inst_id=ticker.inst_id,
                    reasons=list(reasons),
                )
            else:
                instrument = self._to_filtered(ticker)
                passed.append(instrument)
                log.info(
                    "filter.passed",
                    inst_id=ticker.inst_id,
                    volume_24h_usd=str(instrument.volume_24h_usd),
                    spread_pct=str(instrument.spread_pct),
                    inst_type=instrument.inst_type,
                )

        log.info(
            "filter.complete",
            total=len(tickers),
            passed=len(passed),
            rejected=len(rejected),
        )
        return FilterResult(passed=tuple(passed), rejected=tuple(rejected))

    def assign_tiers(self, instruments: list[FilteredInstrument]) -> TieredInstruments:
        """Partition *instruments* into tiers by descending 24 h volume.

        Tier boundaries (by rank, 1-indexed):

        * Tier 1 — ranks 1 … ``filter_tier1_size`` (default 50)
        * Tier 2 — ranks ``filter_tier1_size + 1`` … ``filter_tier2_size`` (default 200)
        * Tier 3 — all remaining

        Parameters
        ----------
        instruments:
            Filtered instruments (typically ``FilterResult.passed``).

        Returns
        -------
        TieredInstruments
            Instruments with ``tier`` and ``scan_interval_seconds`` set.
        """
        ranked = sorted(
            instruments,
            key=lambda item: (-item.volume_24h_usd, item.inst_id),
        )

        tier1: list[FilteredInstrument] = []
        tier2: list[FilteredInstrument] = []
        tier3: list[FilteredInstrument] = []

        tier1_limit = self._settings.filter_tier1_size
        tier2_limit = self._settings.filter_tier2_size

        for rank, item in enumerate(ranked, start=1):
            if rank <= tier1_limit:
                tier, interval = 1, self._settings.filter_tier1_interval_seconds
            elif rank <= tier2_limit:
                tier, interval = 2, self._settings.filter_tier2_interval_seconds
            else:
                tier, interval = 3, self._settings.filter_tier3_interval_seconds

            assigned = item.model_copy(
                update={"tier": tier, "scan_interval_seconds": interval},
            )
            if tier == 1:
                tier1.append(assigned)
            elif tier == 2:
                tier2.append(assigned)
            else:
                tier3.append(assigned)

            log.info(
                "filter.tier_assigned",
                inst_id=item.inst_id,
                tier=tier,
                rank=rank,
                volume_24h_usd=str(item.volume_24h_usd),
                scan_interval_seconds=interval,
            )

        log.info(
            "filter.tiers_complete",
            tier1=len(tier1),
            tier2=len(tier2),
            tier3=len(tier3),
        )
        return TieredInstruments(
            tier1=tuple(tier1),
            tier2=tuple(tier2),
            tier3=tuple(tier3),
        )

    def _evaluate(self, ticker: NormalizedTicker) -> list[str]:
        """Return rejection reasons for *ticker* (empty list = pass)."""
        reasons: list[str] = []
        inst_id = ticker.inst_id
        meta = self._metadata.get(inst_id)

        inst_type = meta.inst_type if meta else _infer_inst_type(inst_id)
        if inst_type not in self._allowed_inst_types:
            reasons.append(f"inst_type_not_allowed:{inst_type}")

        if not _is_usdt_pair(inst_id, self._quote_currencies):
            reasons.append("not_usdt_pair")

        volume = _volume_24h_usd(ticker)
        min_volume = Decimal(str(self._settings.filter_min_volume_usd))
        if volume is None:
            reasons.append("missing_volume_24h_usd")
        elif volume < min_volume:
            reasons.append(f"volume_below_min:{volume}<{min_volume}")

        spread = _compute_spread_pct(ticker.bid_price, ticker.ask_price)
        max_spread = Decimal(str(self._settings.filter_max_spread_pct))
        if spread is None:
            reasons.append("missing_or_invalid_spread")
        elif spread > max_spread:
            reasons.append(f"spread_above_max:{spread}>{max_spread}")

        listing_time = None
        if meta and meta.listed_at is not None:
            listing_time = meta.listed_at
        elif meta and hasattr(meta, "created_at"):
            listing_time = getattr(meta, "created_at", None)

        if listing_time is not None:
            min_age = timedelta(days=self._settings.filter_min_listing_age_days)
            age = self._reference_time - listing_time
            if age < min_age:
                reasons.append(
                    f"listing_too_new:{age.days}d<{self._settings.filter_min_listing_age_days}d",
                )

        return reasons

    def _to_filtered(self, ticker: NormalizedTicker) -> FilteredInstrument:
        """Build a :class:`FilteredInstrument` from a passing ticker."""
        meta = self._metadata.get(ticker.inst_id)
        inst_type = meta.inst_type if meta else _infer_inst_type(ticker.inst_id)
        volume = _volume_24h_usd(ticker)
        spread = _compute_spread_pct(ticker.bid_price, ticker.ask_price)
        assert volume is not None and spread is not None  # guarded by _evaluate
        return FilteredInstrument(
            inst_id=ticker.inst_id,
            inst_type=inst_type,
            volume_24h_usd=volume,
            spread_pct=spread,
            last_price=ticker.last_price,
        )
