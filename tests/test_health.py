"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that /health endpoint returns 200 OK with correct payload."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"

    def test_root_endpoint_returns_200(self, client: TestClient):
        """Test that / endpoint returns 200 OK with correct payload."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"

    def test_health_endpoint_content_type_json(self, client: TestClient):
        """Test that /health returns Content-Type: application/json."""
        response = client.get("/health")
        
        assert response.headers["content-type"] == "application/json"
