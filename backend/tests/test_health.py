"""Tests for health check endpoints."""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    def test_health_endpoint_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"

    def test_root_endpoint_returns_200(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"
