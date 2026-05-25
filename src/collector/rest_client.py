"""Synchronous OKX REST API client (public endpoints only)."""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from src.collector.normalizer import candle_array_to_dict
from src.collector.rate_limiter import RateLimiter
from src.utils.logger import get_logger

log = get_logger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_DEFAULT_TIMEOUT = 10.0


def _is_retryable(exc: BaseException) -> bool:
    """Return True when *exc* warrants a retry."""
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError | httpx.ReadError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return False


class OKXRestClient:
    """Thin synchronous wrapper around OKX v5 public REST endpoints.

    Features
    --------
    * Configurable base URL via :mod:`config.settings`
    * Tenacity retry (3 attempts, 1 s / 2 s / 4 s backoff)
    * Sliding-window rate limit (20 req / 2 s)
    * Per-symbol error isolation — one bad symbol never aborts a batch
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        rate_limiter: RateLimiter | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        """Create a REST client.

        Parameters
        ----------
        base_url:
            Override OKX base URL (defaults to ``settings.okx_api_base_url``).
        timeout:
            Request timeout in seconds.
        rate_limiter:
            Optional custom rate limiter (defaults to 20 req / 2 s).
        client:
            Optional pre-built :class:`httpx.Client` (useful in tests).
        """
        self._base_url = (base_url or settings.okx_api_base_url).rstrip("/")
        self._timeout = timeout
        self._rate_limiter = rate_limiter or RateLimiter(max_requests=20, window_seconds=2.0)
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OKXRestClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute one HTTP request with rate limiting and retry."""
        self._rate_limiter.acquire()
        start = time.perf_counter()
        symbol = kwargs.pop("_log_symbol", None)

        try:
            response = self._client.request(method, path, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000.0
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            code = str(payload.get("code", "0"))
            if code != "0":
                msg = payload.get("msg", "unknown error")
                log.error(
                    "okx.rest.api_error",
                    path=path,
                    symbol=symbol,
                    code=code,
                    msg=msg,
                    latency_ms=round(latency_ms, 2),
                )
                raise httpx.HTTPStatusError(
                    f"OKX API error {code}: {msg}",
                    request=response.request,
                    response=response,
                )
            log.debug(
                "okx.rest.success",
                path=path,
                symbol=symbol,
                latency_ms=round(latency_ms, 2),
            )
            return payload
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            log.warning(
                "okx.rest.error",
                path=path,
                symbol=symbol,
                error=type(exc).__name__,
                detail=str(exc),
                latency_ms=round(latency_ms, 2),
            )
            raise

    def get_instruments(self, inst_type: str = "SPOT") -> list[dict[str, Any]]:
        """Fetch all instruments for *inst_type*.

        Parameters
        ----------
        inst_type:
            OKX instrument type (``SPOT``, ``SWAP``, …).

        Returns
        -------
        list[dict]
            Raw OKX ``data`` rows.
        """
        payload = self._request(
            "GET",
            "/api/v5/public/instruments",
            params={"instType": inst_type},
            _log_symbol=inst_type,
        )
        data: list[dict[str, Any]] = payload.get("data") or []
        log.info("okx.rest.instruments", inst_type=inst_type, count=len(data))
        return data

    def get_tickers(
        self,
        inst_type: str = "SPOT",
        inst_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch ticker snapshots.

        When *inst_id* is provided, returns at most one row. Errors for a
        single symbol are logged and yield an empty list rather than raising.
        """
        params: dict[str, str] = {"instType": inst_type}
        if inst_id:
            params["instId"] = inst_id
        try:
            payload = self._request(
                "GET",
                "/api/v5/market/tickers",
                params=params,
                _log_symbol=inst_id or inst_type,
            )
            data: list[dict[str, Any]] = payload.get("data") or []
            log.info(
                "okx.rest.tickers",
                inst_type=inst_type,
                symbol=inst_id,
                count=len(data),
            )
            return data
        except Exception:
            log.exception("okx.rest.tickers.failed", inst_type=inst_type, symbol=inst_id)
            return []

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch OHLCV candles for *symbol*.

        Parameters
        ----------
        symbol:
            Instrument id (``BTC-USDT``).
        timeframe:
            Bar size (``5m``, ``15m``, ``1H``, …).
        limit:
            Number of bars (max 300 on OKX).

        Returns
        -------
        list[dict]
            Candle rows as dicts ready for :func:`normalize_candle`.
        """
        try:
            payload = self._request(
                "GET",
                "/api/v5/market/candles",
                params={"instId": symbol, "bar": timeframe, "limit": str(limit)},
                _log_symbol=symbol,
            )
            rows: list[list[Any]] = payload.get("data") or []
            candles: list[dict[str, Any]] = []
            for row in rows:
                try:
                    candles.append(candle_array_to_dict(row))
                except ValueError as exc:
                    log.warning(
                        "okx.rest.candles.row_skip",
                        symbol=symbol,
                        timeframe=timeframe,
                        error=str(exc),
                    )
            log.info(
                "okx.rest.candles",
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles),
            )
            return candles
        except Exception:
            log.exception(
                "okx.rest.candles.failed",
                symbol=symbol,
                timeframe=timeframe,
            )
            return []

    def get_funding_rates(self, inst_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch funding-rate history / latest for swap instruments.

        Parameters
        ----------
        inst_id:
            Optional single instrument filter (``BTC-USDT-SWAP``).

        Returns
        -------
        list[dict]
            Raw funding-rate rows; empty list on per-symbol failure.
        """
        params: dict[str, str] = {}
        if inst_id:
            params["instId"] = inst_id
        try:
            payload = self._request(
                "GET",
                "/api/v5/public/funding-rate",
                params=params or None,
                _log_symbol=inst_id or "ALL",
            )
            data: list[dict[str, Any]] = payload.get("data") or []
            log.info("okx.rest.funding_rates", symbol=inst_id, count=len(data))
            return data
        except Exception:
            log.exception("okx.rest.funding_rates.failed", symbol=inst_id)
            return []

    def get_candles_batch(
        self,
        symbols: list[str],
        timeframe: str,
        *,
        limit: int = 100,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch candles for multiple symbols; failures are isolated per symbol."""
        results: dict[str, list[dict[str, Any]]] = {}
        for symbol in symbols:
            results[symbol] = self.get_candles(symbol, timeframe, limit=limit)
        return results

    def get_open_interest(self, inst_id: str) -> list[dict[str, Any]]:
        """Fetch current open interest for a swap instrument."""
        try:
            payload = self._request(
                "GET",
                "/api/v5/public/open-interest",
                params={"instType": "SWAP", "instId": inst_id},
                _log_symbol=inst_id,
            )
            data: list[dict[str, Any]] = payload.get("data") or []
            log.info("okx.rest.open_interest", symbol=inst_id, count=len(data))
            return data
        except Exception:
            log.exception("okx.rest.open_interest.failed", symbol=inst_id)
            return []

    def get_open_interest_history(
        self,
        inst_id: str,
        *,
        period: str = "4H",
    ) -> list[list[Any]]:
        """Fetch OI history rows ``[ts, oi, oiCcy, oiUsd]``."""
        try:
            payload = self._request(
                "GET",
                "/api/v5/rubik/stat/contracts/open-interest-history",
                params={"instId": inst_id, "period": period},
                _log_symbol=inst_id,
            )
            data: list[list[Any]] = payload.get("data") or []
            log.info(
                "okx.rest.open_interest_history",
                symbol=inst_id,
                period=period,
                count=len(data),
            )
            return data
        except Exception:
            log.exception("okx.rest.open_interest_history.failed", symbol=inst_id)
            return []
