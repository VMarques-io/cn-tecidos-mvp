"""Tests for webhook endpoint handling."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestWebhookEndpoint:
    def test_valid_text_message_returns_200(self, client, valid_text_message_payload):
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={"response": "Olá!", "flow_step": "idle"})
            response = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            assert response.status_code == 200
            assert response.json()["status"] == "processed"

    def test_from_me_true_is_ignored(self, client, from_me_message_payload):
        response = client.post("/api/v1/evolution/webhook", json=from_me_message_payload)
        assert response.status_code == 200
        assert response.json()["result"]["status"] == "ignored"
        assert response.json()["result"]["reason"] == "from_me"

    def test_group_message_is_ignored(self, client, group_message_payload):
        response = client.post("/api/v1/evolution/webhook", json=group_message_payload)
        assert response.status_code == 200
        assert response.json()["result"]["status"] == "ignored"
        assert response.json()["result"]["reason"] == "group"

    def test_duplicate_message_id_not_processed_twice(self, client, valid_text_message_payload):
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={"response": "Resposta", "flow_step": "idle"})
            response1 = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            assert response1.status_code == 200
            response2 = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            assert response2.json()["result"]["reason"] == "duplicate"

    def test_invalid_event_is_ignored(self, client):
        payload = {"event": "connection.update", "instance": "test", "data": {"status": "connected"}}
        response = client.post("/api/v1/evolution/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_media_message_is_ignored(self, client, media_message_payload):
        response = client.post("/api/v1/evolution/webhook", json=media_message_payload)
        assert response.status_code == 200
        assert response.json()["result"]["reason"] == "media_not_supported"
