"""Integration tests for opportunity and status API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def healthy_scanner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch scanner health check to report ok."""

    def _ok():
        from src.api.routes import health as health_routes

        return health_routes.ComponentCheck(status="ok", latency_ms=1.0)

    monkeypatch.setattr("src.api.routes.health._check_scanner", _ok)
    monkeypatch.setattr(
        "src.api.routes.health._scanner_summary",
        lambda: {"running": True, "heartbeat_at": "2026-05-25T00:00:00+00:00", "uptime_seconds": "60"},
    )


@pytest.mark.integration
class TestOpportunitiesAPI:
    def test_get_opportunities(self, client: TestClient) -> None:
        sample = [
            {
                "id": 1,
                "symbol": "BTC-USDT-SWAP",
                "tier": 1,
                "strategy": "FUNDING",
                "direction": "LONG",
                "status": "APPROVED",
                "total_score": 85,
                "grade": "EXCELLENT",
                "detected_at": "2026-05-25T10:00:00+00:00",
                "scores": {},
            },
        ]
        with patch(
            "src.api.routes.opportunities.OpportunityRepository",
        ) as mock_repo_cls:
            mock_repo_cls.return_value.get_opportunities.return_value = sample
            response = client.get("/opportunities?grade=EXCELLENT&limit=10")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["symbol"] == "BTC-USDT-SWAP"

    def test_get_opportunity_detail_not_found(self, client: TestClient) -> None:
        with patch("src.api.routes.opportunities.OpportunityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_opportunity_detail.return_value = None
            response = client.get("/opportunities/999")

        assert response.status_code == 404

    def test_get_opportunity_detail(self, client: TestClient) -> None:
        detail = {
            "id": 1,
            "symbol": "BTC-USDT-SWAP",
            "tier": 1,
            "strategy": "FUNDING",
            "direction": "LONG",
            "status": "APPROVED",
            "entry_price": "100",
            "detected_at": "2026-05-25T10:00:00+00:00",
            "context": {},
            "score": {"total_score": 85, "grade": "EXCELLENT"},
            "risk_decision": {"outcome": "APPROVED"},
        }
        with patch("src.api.routes.opportunities.OpportunityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_opportunity_detail.return_value = detail
            response = client.get("/opportunities/1")

        assert response.status_code == 200
        assert response.json()["id"] == 1


@pytest.mark.integration
class TestAlertsAPI:
    def test_get_alerts(self, client: TestClient) -> None:
        sample = [
            {
                "id": 1,
                "opportunity_id": 10,
                "symbol": "BTC-USDT-SWAP",
                "strategy_type": "FUNDING",
                "direction": "LONG",
                "entry_price": "100.0",
                "tp_price": "103.0",
                "sl_price": "98.5",
                "tp_pct": 3.0,
                "sl_pct": 1.5,
                "timeout_hours": 8,
                "status": "RUNNING",
                "entry_at": "2026-05-25T10:00:00+00:00",
                "closed_at": None,
                "close_price": None,
                "pnl_pct": None,
                "tier": 1,
                "duration_seconds": None,
            },
        ]
        with patch("src.api.routes.alerts.PaperTradeRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_trades.return_value = sample
            response = client.get("/alerts?limit=10&status=RUNNING")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["tier"] == 1
        assert body["items"][0]["status"] == "RUNNING"

    def test_get_alert_stats(self, client: TestClient) -> None:
        stats = {
            "total_trades": 5,
            "running": 2,
            "wins": 2,
            "losses": 1,
            "expired": 0,
            "win_rate": 66.67,
            "avg_pnl": 1.2,
            "by_strategy": {},
            "by_tier": {},
            "best_trade": None,
            "worst_trade": None,
            "pnl_by_day": [],
        }
        with patch("src.api.routes.alerts.PaperTradeRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_stats.return_value = stats
            response = client.get("/alerts/stats")

        assert response.status_code == 200
        assert response.json()["total_trades"] == 5


@pytest.mark.integration
class TestStatusAPI:
    def test_get_status(self, client: TestClient) -> None:
        with patch("src.api.routes.status.ScannerState") as mock_state_cls:
            mock_state_cls.return_value.get_status.return_value = {
                "running": True,
                "started_at": "2026-05-25T00:00:00+00:00",
                "heartbeat_at": "2026-05-25T00:01:00+00:00",
                "uptime_seconds": 60.0,
                "last_scan_by_tier": {"1": "2026-05-25T00:01:00+00:00"},
                "totals": {"approved": 3},
                "stale": False,
            }
            response = client.get("/status")

        assert response.status_code == 200
        body = response.json()
        assert body["scanner_running"] is True
        assert body["uptime_seconds"] == 60.0

    def test_get_stats(self, client: TestClient) -> None:
        with patch("src.api.routes.status.OpportunityRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_stats_today.return_value = {
                "total_today": 5,
                "by_grade": {"excellent": 2, "good": 2, "watch": 1},
                "by_strategy": {"funding": 4, "momentum": 1},
            }
            mock_repo.get_top_opportunities.return_value = [{"id": 1, "total_score": 90}]
            mock_repo_cls.return_value = mock_repo
            response = client.get("/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["total_today"] == 5
        assert len(body["top_opportunities"]) == 1


@pytest.mark.integration
def test_health_includes_scanner(
    client: TestClient,
    healthy_redis: None,
) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "scanner" in body["checks"]
    assert body["checks"]["scanner"]["status"] == "ok"
    assert body["scanner"]["running"] is True
