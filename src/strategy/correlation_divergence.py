"""Correlation divergence — alt catch-up / drag-down vs BTC benchmark."""

from __future__ import annotations

from datetime import datetime, timezone

from config.settings import Settings, get_settings
from src.schemas.strategy import Candidate, Direction, StrategyType
from src.strategy.base import BaseStrategy, MarketContext
from src.strategy.helpers import calc_price_change_pct, volume_not_declining
from src.utils.logger import get_logger

log = get_logger(__name__)

_BENCHMARK_SYMBOLS = frozenset({"BTC-USDT-SWAP", "ETH-USDT-SWAP"})


class CorrelationDivergenceStrategy(BaseStrategy):
    """Detect alts lagging BTC/ETH moves for catch-up trades."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def name(self) -> str:
        return StrategyType.CORRELATION_DIVERGENCE.value

    def scan(self, market_data: MarketContext) -> list[Candidate]:
        inst_id = market_data.inst_id
        try:
            if inst_id in _BENCHMARK_SYMBOLS:
                return []

            tier = market_data.tier or 3
            max_tier = self._settings.correlation_min_tier
            if tier > max_tier:
                log.debug(
                    "strategy.correlation.skip",
                    inst_id=inst_id,
                    reason="tier_too_low",
                    tier=tier,
                    max_tier=max_tier,
                )
                return []

            benchmark = market_data.benchmark
            if benchmark is None:
                log.debug("strategy.correlation.skip", inst_id=inst_id, reason="missing_benchmark")
                return []

            candles = market_data.candles_h1
            coin_change_1h = calc_price_change_pct(candles, 1)
            if coin_change_1h is None:
                log.debug("strategy.correlation.skip", inst_id=inst_id, reason="insufficient_candles")
                return []

            btc_change = benchmark.btc_change_1h
            divergence = btc_change - coin_change_1h
            min_div = self._settings.correlation_min_divergence
            strong_div = self._settings.correlation_strong_divergence

            direction: Direction | None = None
            if btc_change > 0 and divergence >= min_div:
                direction = Direction.LONG
            elif btc_change < 0 and divergence <= -min_div:
                direction = Direction.SHORT

            if direction is None:
                log.debug(
                    "strategy.correlation.no_signal",
                    inst_id=inst_id,
                    divergence=round(divergence, 4),
                    btc_change_1h=btc_change,
                    coin_change_1h=coin_change_1h,
                )
                return []

            if direction == Direction.LONG and not benchmark.btc_trend_up:
                log.debug("strategy.correlation.skip", inst_id=inst_id, reason="btc_not_uptrend_for_long")
                return []

            if direction == Direction.SHORT and benchmark.btc_change_1h >= 0:
                log.debug("strategy.correlation.skip", inst_id=inst_id, reason="btc_not_down_for_short")
                return []

            vol_ok = volume_not_declining(market_data.candles_m15)
            if not vol_ok:
                log.info("strategy.correlation.rejected", inst_id=inst_id, reason="volume_declining")
                return []

            abs_div = abs(divergence)
            confidence = 0.55
            if abs_div >= strong_div:
                confidence = min(0.55 + (abs_div - strong_div) / strong_div * 0.35, 0.95)
            elif abs_div >= min_div:
                confidence = 0.55 + (abs_div - min_div) / max(strong_div - min_div, 0.01) * 0.2

            last_price = market_data.ticker.last_price if market_data.ticker else None
            candidate = Candidate(
                symbol=inst_id,
                strategy_type=StrategyType.CORRELATION_DIVERGENCE,
                direction=direction,
                raw_signals={
                    "btc_change_1h": str(round(btc_change, 4)),
                    "eth_change_1h": str(round(benchmark.eth_change_1h, 4)),
                    "coin_change_1h": str(round(coin_change_1h, 4)),
                    "divergence_pct": str(round(divergence, 4)),
                    "btc_trend": "UP" if benchmark.btc_trend_up else "DOWN",
                    "volume_ok": str(vol_ok),
                    "btc_change_4h": str(round(benchmark.btc_change_4h, 4)),
                    "btc_change_24h": str(round(benchmark.btc_change_24h, 4)),
                    "last_price": str(last_price) if last_price is not None else "",
                },
                detected_at=datetime.now(tz=timezone.utc),
                confidence=round(confidence, 4),
            )
            log.info(
                "strategy.correlation.signal",
                inst_id=inst_id,
                direction=direction.value,
                divergence_pct=round(divergence, 4),
                btc_change_1h=round(btc_change, 4),
                coin_change_1h=round(coin_change_1h, 4),
                confidence=confidence,
            )
            return [candidate]

        except Exception:
            log.exception("strategy.correlation.error", inst_id=inst_id)
            return []
