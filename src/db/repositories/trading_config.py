"""CRUD for TradingConfig — trading mode, API keys, risk params."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import TradingConfig
from src.utils.logger import get_logger

log = get_logger(__name__)

DEFAULTS = {
    "mode": "paper",
    "api_key": None,
    "api_secret": None,
    "api_passphrase": None,
    "daily_loss_limit_pct": 5.0,
    "size_pct_tier1": 3.0,
    "size_pct_tier2": 2.0,
    "size_pct_tier3": 1.0,
    "max_leverage": 5,
}


class TradingConfigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> TradingConfig:
        row = self._session.get(TradingConfig, 1)
        if row is None:
            row = TradingConfig(id=1, **DEFAULTS)
            self._session.add(row)
            self._session.flush()
        return row

    def update(self, **kwargs: Any) -> TradingConfig:
        row = self.get()
        for k, v in kwargs.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(tz=timezone.utc)
        self._session.flush()
        log.info("trading_config.updated", fields=list(kwargs.keys()))
        return row

    @staticmethod
    def to_dict(row: TradingConfig) -> dict[str, Any]:
        return {
            "mode": row.mode,
            "api_key": "***" if row.api_key else None,   # never expose key
            "api_secret": "***" if row.api_secret else None,
            "api_passphrase": "***" if row.api_passphrase else None,
            "daily_loss_limit_pct": row.daily_loss_limit_pct,
            "size_pct_tier1": row.size_pct_tier1,
            "size_pct_tier2": row.size_pct_tier2,
            "size_pct_tier3": row.size_pct_tier3,
            "max_leverage": row.max_leverage,
            "updated_at": row.updated_at.isoformat(),
        }
