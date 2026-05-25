"""Integration tests for OKXRestClient (mocked HTTP — no live calls)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from src.collector.rest_client import OKXRestClient


def _okx_response(data: list[dict[str, Any]] | list[list[Any]]) -> dict[str, Any]:
    return {"code": "0", "msg": "", "data": data}


def _make_client(handler: httpx.MockTransport) -> OKXRestClient:
    http = httpx.Client(base_url="https://test.okx.com", transport=handler)
    return OKXRestClient(base_url="https://test.okx.com", client=http, rate_limiter=None)


@pytest.mark.integration
class TestOKXRestClientSuccess:
    def test_get_instruments(self) -> None:
        payload = _okx_response([{"instId": "BTC-USDT", "instType": "SPOT"}])

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v5/public/instruments"
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_instruments("SPOT")
        assert len(rows) == 1
        assert rows[0]["instId"] == "BTC-USDT"

    def test_get_tickers_single_symbol(self) -> None:
        payload = _okx_response([{"instId": "BTC-USDT", "last": "65000"}])

        def handler(request: httpx.Request) -> httpx.Response:
            assert "instId=BTC-USDT" in str(request.url)
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_tickers("SPOT", inst_id="BTC-USDT")
        assert rows[0]["last"] == "65000"

    def test_get_candles(self) -> None:
        payload = _okx_response(
            [["1716633600000", "1", "2", "0.5", "1.5", "100", "100", "100", "1"]]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v5/market/candles"
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_candles("BTC-USDT", "5m")
        assert rows[0]["o"] == "1"

    def test_get_funding_rates(self) -> None:
        payload = _okx_response(
            [{"instId": "BTC-USDT-SWAP", "fundingRate": "0.0001", "fundingTime": "1"}]
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_funding_rates("BTC-USDT-SWAP")
        assert rows[0]["instId"] == "BTC-USDT-SWAP"


@pytest.mark.integration
class TestOKXRestClientRetry:
    def test_retries_on_500_then_succeeds(self) -> None:
        calls = {"count": 0}
        payload = _okx_response([{"instId": "BTC-USDT", "instType": "SPOT"}])

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] < 3:
                return httpx.Response(500, json={"code": "500", "msg": "error"})
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_instruments("SPOT")
        assert calls["count"] == 3
        assert len(rows) == 1

    def test_retries_on_429(self) -> None:
        calls = {"count": 0}
        payload = _okx_response([{"instId": "ETH-USDT", "last": "3500"}])

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(429, json={"code": "429", "msg": "rate limit"})
            return httpx.Response(200, json=payload)

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_tickers("SPOT", inst_id="ETH-USDT")
        assert calls["count"] == 2
        assert rows[0]["instId"] == "ETH-USDT"


@pytest.mark.integration
class TestOKXRestClientErrors:
    def test_timeout_returns_empty_for_tickers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_tickers("SPOT", inst_id="BTC-USDT")
        assert rows == []

    def test_candles_failure_isolated(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"code": "500", "msg": "fail"})

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_candles("BTC-USDT", "5m")
        assert rows == []

    def test_okx_api_error_code_raises_on_instruments(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": "51000", "msg": "bad", "data": []})

        with _make_client(httpx.MockTransport(handler)) as client:
            with pytest.raises(httpx.HTTPStatusError):
                client.get_instruments("SPOT")

    def test_single_symbol_ticker_failure_returns_empty(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            return httpx.Response(500, json={"code": "500", "msg": "fail"})

        with _make_client(httpx.MockTransport(handler)) as client:
            rows = client.get_tickers("SPOT", inst_id="BAD-USDT")
        assert rows == []
        assert attempts["n"] == 3  # exhausted retries
