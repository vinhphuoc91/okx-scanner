"""OKX public WebSocket client for real-time ticker streaming."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from config import settings
from src.collector.cache import MarketCache
from src.collector.normalizer import normalize_ticker
from src.schemas.market import NormalizedTicker
from src.utils.logger import get_logger

log = get_logger(__name__)

_RECONNECT_DELAY_SECONDS = 5.0


class OKXWebSocketClient:
    """Subscribe to OKX ``tickers`` channel and push updates into :class:`MarketCache`.

    Auto-reconnects within 5 seconds on disconnect. Designed to run inside an
    asyncio event loop (typically the worker process).
    """

    def __init__(
        self,
        *,
        ws_url: str | None = None,
        cache: MarketCache | None = None,
        inst_types: list[str] | None = None,
        on_ticker: Callable[[NormalizedTicker], None] | None = None,
        reconnect_delay: float = _RECONNECT_DELAY_SECONDS,
    ) -> None:
        """Create a WebSocket client.

        Parameters
        ----------
        ws_url:
            Override public WS URL (defaults to ``settings.okx_ws_public_url``).
        cache:
            Cache instance for ticker writes (created lazily if ``None``).
        inst_types:
            Instrument types to subscribe (default ``["SPOT", "SWAP"]``).
        on_ticker:
            Optional callback invoked after each normalized ticker.
        reconnect_delay:
            Seconds to wait before reconnecting after a drop.
        """
        self._ws_url = ws_url or settings.okx_ws_public_url
        self._cache = cache
        self._inst_types = inst_types or ["SPOT", "SWAP"]
        self._on_ticker = on_ticker
        self._reconnect_delay = reconnect_delay
        self._running = False

    @property
    def cache(self) -> MarketCache:
        """Lazy-init cache."""
        if self._cache is None:
            self._cache = MarketCache()
        return self._cache

    def _build_subscribe_message(self) -> dict[str, Any]:
        """Build OKX subscribe payload for tickers channels."""
        args = [{"channel": "tickers", "instType": t} for t in self._inst_types]
        return {"op": "subscribe", "args": args}

    def _handle_message(self, raw_message: str) -> None:
        """Parse one WS frame and update cache when it is a ticker push."""
        try:
            message: dict[str, Any] = json.loads(raw_message)
        except json.JSONDecodeError:
            log.warning("okx.ws.invalid_json", raw=raw_message[:200])
            return

        if message.get("event") in ("subscribe", "unsubscribe"):
            log.info("okx.ws.event", event=message.get("event"), arg=message.get("arg"))
            return

        arg = message.get("arg") or {}
        if arg.get("channel") != "tickers":
            return

        data = message.get("data") or []
        for row in data:
            if not isinstance(row, dict):
                continue
            inst_id = row.get("instId", "unknown")
            try:
                ticker = normalize_ticker(row)
                self.cache.set_ticker(ticker)
                if self._on_ticker:
                    self._on_ticker(ticker)
                log.debug("okx.ws.ticker.updated", inst_id=inst_id)
            except ValueError as exc:
                log.warning(
                    "okx.ws.ticker.normalize_failed",
                    inst_id=inst_id,
                    error=str(exc),
                )

    async def _connect_and_listen(self) -> None:
        """Open one WS session and read until disconnect."""
        log.info("okx.ws.connecting", url=self._ws_url)
        async with websockets.connect(
            self._ws_url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        ) as ws:
            subscribe = self._build_subscribe_message()
            await ws.send(json.dumps(subscribe))
            log.info("okx.ws.connected", inst_types=self._inst_types)

            async for message in ws:
                if not self._running:
                    break
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                self._handle_message(message)

    async def run(self) -> None:
        """Run the client loop with auto-reconnect."""
        self._running = True
        while self._running:
            try:
                await self._connect_and_listen()
            except ConnectionClosed as exc:
                log.warning(
                    "okx.ws.disconnected",
                    code=exc.code,
                    reason=exc.reason,
                )
            except Exception:
                log.exception("okx.ws.error")

            if not self._running:
                break

            log.info("okx.ws.reconnecting", delay_seconds=self._reconnect_delay)
            await asyncio.sleep(self._reconnect_delay)

        log.info("okx.ws.stopped")

    def stop(self) -> None:
        """Signal the run loop to exit after the current connection closes."""
        self._running = False
        log.info("okx.ws.stop_requested")
