"""Tests for health / readiness endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_live_returns_200(client: TestClient) -> None:
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.unit
def test_health_all_ok(client: TestClient, healthy_redis: None) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "okx-scanner"
    assert body["version"] == "0.1.0"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"


@pytest.mark.unit
def test_health_db_down(client: TestClient, failing_db: None, healthy_redis: None) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["database"]["status"] == "down"
    assert body["checks"]["redis"]["status"] == "ok"


@pytest.mark.unit
def test_health_redis_down(client: TestClient, down_redis: None) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "down"
    assert body["checks"]["redis"]["status"] == "down"


@pytest.mark.unit
def test_ready_returns_200_when_healthy(client: TestClient, healthy_redis: None) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.unit
def test_ready_returns_503_when_down(client: TestClient, down_redis: None) -> None:
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "down"


@pytest.mark.unit
def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "okx-scanner"
    assert body["version"] == "0.1.0"
    assert "env" in body
