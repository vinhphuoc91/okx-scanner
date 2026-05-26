"""OKX authenticated trading client — place/cancel orders, fetch balance."""
from __future__ import annotations

import hashlib
import hmac
import base64
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from config.settings import get_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

_BASE = "https://www.okx.com"


def _sign(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    msg = f"{timestamp}{method.upper()}{path}{body}"
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()


class OKXTradingClient:
    """Authenticated OKX REST client for order execution."""

    def __init__(self, api_key: str, api_secret: str, api_passphrase: str) -> None:
        self._key = api_key
        self._secret = api_secret
        self._passphrase = api_passphrase

    def _headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return {
            "OK-ACCESS-KEY": self._key,
            "OK-ACCESS-SIGN": _sign(self._secret, ts, method, path, body),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=10) as client:
            r = client.get(_BASE + path, headers=self._headers("GET", path))
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        import json
        raw = json.dumps(body)
        with httpx.Client(timeout=10) as client:
            r = client.post(_BASE + path, content=raw, headers=self._headers("POST", path, raw))
            r.raise_for_status()
            return r.json()

    def get_balance(self) -> dict[str, Any]:
        """Return USDT balance from trading account."""
        data = self._get("/api/v5/account/balance?ccy=USDT")
        try:
            details = data["data"][0]["details"]
            usdt = next((d for d in details if d["ccy"] == "USDT"), None)
            return {
                "available": Decimal(usdt["availBal"]) if usdt else Decimal("0"),
                "total": Decimal(usdt["eq"]) if usdt else Decimal("0"),
            }
        except Exception:
            log.warning("trading_client.balance_parse_failed", raw=data)
            return {"available": Decimal("0"), "total": Decimal("0")}

    def place_order(
        self,
        *,
        inst_id: str,
        direction: str,        # "LONG" | "SHORT"
        size_usdt: Decimal,
        entry_price: Decimal,
        sl_price: Decimal,
        tp_price: Decimal,
        leverage: int = 5,
    ) -> dict[str, Any]:
        """Place a market order with attached SL/TP algo orders."""
        side = "buy" if direction == "LONG" else "sell"
        pos_side = "long" if direction == "LONG" else "short"

        # Set leverage first
        self._post("/api/v5/account/set-leverage", {
            "instId": inst_id, "lever": str(leverage), "mgnMode": "cross"
        })

        # Calculate size in contracts (1 contract = 1 USD notional for SWAP)
        sz = str((size_usdt / entry_price).quantize(Decimal("0.1")))

        # Place market order
        order = self._post("/api/v5/trade/order", {
            "instId": inst_id,
            "tdMode": "cross",
            "side": side,
            "posSide": pos_side,
            "ordType": "market",
            "sz": sz,
        })
        log.info("trading_client.order_placed", inst_id=inst_id, direction=direction,
                 size_usdt=str(size_usdt), order=order)

        # Attach SL/TP algo
        self._post("/api/v5/trade/order-algo", {
            "instId": inst_id,
            "tdMode": "cross",
            "side": "sell" if direction == "LONG" else "buy",
            "posSide": pos_side,
            "ordType": "oco",
            "sz": sz,
            "tpTriggerPx": str(tp_price),
            "tpOrdPx": "-1",
            "slTriggerPx": str(sl_price),
            "slOrdPx": "-1",
        })
        return order

    def cancel_algo_orders(self, inst_id: str) -> None:
        """Cancel all pending algo orders for an instrument."""
        algos = self._get(f"/api/v5/trade/orders-algo-pending?instId={inst_id}&ordType=oco")
        orders = [{"algoId": o["algoId"], "instId": inst_id} for o in algos.get("data", [])]
        if orders:
            self._post("/api/v5/trade/cancel-algos", orders)

    def test_connection(self) -> bool:
        """Return True if credentials are valid."""
        try:
            self._get("/api/v5/account/balance?ccy=USDT")
            return True
        except Exception as e:
            log.warning("trading_client.test_failed", error=str(e))
            return False
