"""Opportunity-detection strategies."""

from src.strategy.base import BaseStrategy, BenchmarkSnapshot, MarketContext
from src.strategy.breakout import BreakoutStrategy
from src.strategy.correlation_divergence import CorrelationDivergenceStrategy
from src.strategy.funding import FundingStrategy
from src.strategy.liquidation_zone import LiquidationZoneStrategy
from src.strategy.momentum import MomentumStrategy, calc_ema, calc_rsi
from src.strategy.stat_arb import StatArbitrageStrategy
from src.strategy.trend_pullback import TrendPullbackStrategy
from src.strategy.volume_anomaly import VolumeAnomalyStrategy

__all__ = [
    "BaseStrategy",
    "BenchmarkSnapshot",
    "BreakoutStrategy",
    "CorrelationDivergenceStrategy",
    "FundingStrategy",
    "LiquidationZoneStrategy",
    "MarketContext",
    "MomentumStrategy",
    "StatArbitrageStrategy",
    "TrendPullbackStrategy",
    "VolumeAnomalyStrategy",
    "calc_ema",
    "calc_rsi",
]
