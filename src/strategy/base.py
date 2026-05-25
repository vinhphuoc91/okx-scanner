"""Strategy engine base types and abstract strategy interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from abc import ABC, abstractmethod

from src.schemas.market import (
    NormalizedCandle,
    NormalizedFundingRate,
    NormalizedTicker,
)
from src.schemas.strategy import Candidate


@dataclass(frozen=True)
class BenchmarkSnapshot:
    """BTC/ETH benchmark moves for correlation strategies."""

    btc_change_1h: float
    btc_change_4h: float
    btc_change_24h: float
    eth_change_1h: float
    eth_change_4h: float
    eth_change_24h: float
    btc_trend_up: bool
    btc_price: str
    eth_price: str


@dataclass(frozen=True)
class MarketContext:
    """Market data bundle passed to strategy scanners.

    Attributes
    ----------
    symbol:
        OKX instrument id (``instId``). Falls back to ``ticker.inst_id`` when set.
    ticker:
        Latest ticker snapshot.
    candles_m15:
        M15 OHLCV bars (oldest → newest recommended).
    candles_h1:
        H1 OHLCV bars (oldest → newest recommended).
    funding_rate:
        Latest funding-rate snapshot (SWAP instruments).
    tier:
        Instrument tier (1–3) when known.
    spot_ticker:
        Matching spot ticker for stat-arb (``BTC-USDT`` for ``BTC-USDT-SWAP``).
    open_interest:
        Current open interest in contracts.
    open_interest_change_4h_pct:
        Percent OI change over ~4H window.
    benchmark:
        BTC/ETH benchmark snapshot for correlation divergence.
    basis_history_pct:
        Recent perp-spot basis % readings (oldest → newest).
    """

    symbol: str = ""
    ticker: NormalizedTicker | None = None
    candles_m15: list[NormalizedCandle] = field(default_factory=list)
    candles_h1: list[NormalizedCandle] = field(default_factory=list)
    funding_rate: NormalizedFundingRate | None = None
    tier: int | None = None
    spot_ticker: NormalizedTicker | None = None
    open_interest: Decimal | None = None
    open_interest_change_4h_pct: float | None = None
    benchmark: BenchmarkSnapshot | None = None
    basis_history_pct: list[float] = field(default_factory=list)

    @property
    def inst_id(self) -> str:
        """Resolved instrument id."""
        if self.symbol:
            return self.symbol
        if self.ticker is not None:
            return self.ticker.inst_id
        if self.funding_rate is not None:
            return self.funding_rate.inst_id
        return ""


class BaseStrategy(ABC):
    """Abstract base for all opportunity-detection strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy identifier."""

    @abstractmethod
    def scan(self, market_data: MarketContext) -> list[Candidate]:
        """Analyse *market_data* and return zero or more candidates.

        Implementations must not raise for bad/missing data on a single symbol;
        log and return an empty list instead.
        """
