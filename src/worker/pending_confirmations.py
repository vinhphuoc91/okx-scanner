"""Redis-backed store for opportunities awaiting M15 confirmation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import redis
from redis.exceptions import RedisError

from config import settings
from src.utils.logger import get_logger

log = get_logger(__name__)

_KEY_PREFIX = "pending_confirm:"
_INDEX_KEY = "pending_confirm:index"
MAX_PENDING = 20


_MAX_CONFIRM_SECONDS = 15 * 60


@dataclass
class PendingConfirmation:
    """Opportunity waiting for M15 entry confirmation."""

    opportunity_id: int
    symbol: str
    strategy: str
    direction: str
    tier: int
    signal_price: str
    atr_value: float
    sl_multiplier: float
    tp_multiplier: float
    timeout_hours: int
    confirmation_candles: int
    created_at: str

    @property
    def timeout_seconds(self) -> int:
        return max(_MAX_CONFIRM_SECONDS, self.confirmation_candles * 15 * 60)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> PendingConfirmation:
        data = json.loads(raw)
        return cls(**data)


class PendingConfirmationStore:
    """Persist pending confirmations in Redis with TTL."""

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        client: redis.Redis | None = None,  # type: ignore[type-arg]
    ) -> None:
        self._owns_client = client is None
        self._client: redis.Redis = client or redis.from_url(  # type: ignore[type-arg, assignment]
            redis_url or settings.redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
        )

    def close(self) -> None:
        if self._owns_client:
            try:
                self._client.close()
            except RedisError:
                log.warning("pending_confirm.close.failed")

    def _key(self, opportunity_id: int) -> str:
        return f"{_KEY_PREFIX}{opportunity_id}"

    def save(self, pending: PendingConfirmation) -> None:
        key = self._key(pending.opportunity_id)
        try:
            pipe = self._client.pipeline()
            pipe.setex(key, pending.timeout_seconds, pending.to_json())
            pipe.sadd(_INDEX_KEY, str(pending.opportunity_id))
            pipe.execute()
        except RedisError:
            log.exception("pending_confirm.save.failed", opportunity_id=pending.opportunity_id)

    def get(self, opportunity_id: int) -> PendingConfirmation | None:
        try:
            raw = self._client.get(self._key(opportunity_id))
            if not raw:
                return None
            return PendingConfirmation.from_json(raw)
        except RedisError:
            log.warning("pending_confirm.get.failed", opportunity_id=opportunity_id)
            return None

    def list_all_with_stale(self) -> tuple[list[PendingConfirmation], list[int]]:
        """Return active pending items and IDs whose Redis keys have expired."""
        try:
            ids = self._client.smembers(_INDEX_KEY)
            result: list[PendingConfirmation] = []
            stale: list[str] = []
            stale_ids: list[int] = []
            for opp_id in ids:
                pending = self.get(int(opp_id))
                if pending is None:
                    stale.append(opp_id)
                    stale_ids.append(int(opp_id))
                else:
                    result.append(pending)
            if stale:
                self._client.srem(_INDEX_KEY, *stale)
            return result, stale_ids
        except RedisError:
            log.warning("pending_confirm.list.failed")
            return [], []

    def list_all(self) -> list[PendingConfirmation]:
        active, _ = self.list_all_with_stale()
        return active

    def active_count(self) -> int:
        return len(self.list_all())

    def has_symbol_strategy(
        self,
        symbol: str,
        strategy: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        for pending in self.list_all():
            if pending.symbol != symbol or pending.strategy != strategy:
                continue
            if exclude_id is not None and pending.opportunity_id == exclude_id:
                continue
            return True
        return False

    def remove(self, opportunity_id: int) -> None:
        try:
            pipe = self._client.pipeline()
            pipe.delete(self._key(opportunity_id))
            pipe.srem(_INDEX_KEY, str(opportunity_id))
            pipe.execute()
        except RedisError:
            log.warning("pending_confirm.remove.failed", opportunity_id=opportunity_id)

    def count(self) -> int:
        try:
            return int(self._client.scard(_INDEX_KEY))
        except RedisError:
            return 0

    @staticmethod
    def build(
        *,
        opportunity_id: int,
        symbol: str,
        strategy: str,
        direction: str,
        tier: int,
        signal_price: Decimal,
        atr_value: float,
        sl_multiplier: float,
        tp_multiplier: float,
        timeout_hours: int,
        confirmation_candles: int,
    ) -> PendingConfirmation:
        return PendingConfirmation(
            opportunity_id=opportunity_id,
            symbol=symbol,
            strategy=strategy,
            direction=direction,
            tier=tier,
            signal_price=str(signal_price),
            atr_value=atr_value,
            sl_multiplier=sl_multiplier,
            tp_multiplier=tp_multiplier,
            timeout_hours=timeout_hours,
            confirmation_candles=confirmation_candles,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    def pending_to_dict(self, pending: PendingConfirmation) -> dict[str, Any]:
        return {
            "opportunity_id": pending.opportunity_id,
            "symbol": pending.symbol,
            "strategy_type": pending.strategy,
            "direction": pending.direction,
            "tier": pending.tier,
            "signal_price": pending.signal_price,
            "atr_value": pending.atr_value,
            "sl_multiplier": pending.sl_multiplier,
            "tp_multiplier": pending.tp_multiplier,
            "status": "PENDING",
            "confirmation_status": "PENDING",
            "entry_at": pending.created_at,
            "created_at": pending.created_at,
        }
