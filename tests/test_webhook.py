"""Tests for webhook endpoint handling."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


class TestWebhookEndpoint:
    """Test suite for Evolution API webhook endpoint."""

    def test_valid_text_message_returns_200(
        self, client: TestClient, valid_text_message_payload
    ):
        """Test that valid text message webhook returns 200."""
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Olá! Como posso ajudar?",
                "flow_step": "idle",

            })
            
            response = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"

    def test_from_me_true_is_ignored(self, client: TestClient, from_me_message_payload):
        """Test that messages with fromMe=True are ignored."""
        response = client.post("/api/v1/evolution/webhook", json=from_me_message_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["result"]["status"] == "ignored"
        assert data["result"]["reason"] == "from_me"

    def test_group_message_is_ignored(self, client: TestClient, group_message_payload):
        """Test that group messages (@g.us) are ignored."""
        response = client.post("/api/v1/evolution/webhook", json=group_message_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["result"]["status"] == "ignored"
        assert data["result"]["reason"] == "group"

    def test_duplicate_message_id_not_processed_twice(
        self, client: TestClient, valid_text_message_payload
    ):
        """Test that duplicate key.id is not processed twice."""
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",

            })
            
            # First request
            response1 = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            assert response1.status_code == 200
            
            # Second request with same message ID
            response2 = client.post("/api/v1/evolution/webhook", json=valid_text_message_payload)
            assert response2.status_code == 200
            
            data = response2.json()
            assert data["result"]["status"] == "ignored"
            assert data["result"]["reason"] == "duplicate"

    def test_empty_json_body_returns_200_graceful(self, client: TestClient):
        """Test that empty JSON body returns 200 gracefully."""
        response = client.post("/api/v1/evolution/webhook", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_invalid_event_is_ignored(self, client: TestClient):
        """Test that non-messages.upsert events are ignored."""
        payload = {
            "event": "connection.update",
            "instance": "test-instance",
            "data": {"status": "connected"}
        }
        
        response = client.post("/api/v1/evolution/webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["event"] == "connection.update"

    def test_messages_upsert_uppercase_event(self, client: TestClient, valid_text_message_payload):
        """Test that MESSAGES_UPSERT (uppercase) event is handled."""
        payload = valid_text_message_payload.copy()
        payload["event"] = "MESSAGES_UPSERT"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",

            })
            
            response = client.post("/api/v1/evolution/webhook", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"

    def test_extended_text_message_handled(self, client: TestClient, extended_text_message_payload):
        """Test that extendedTextMessage is properly parsed."""
        with patch("agents.fashion_graph.fashion_graph") as mock_graph:
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",

            })
            
            response = client.post("/api/v1/evolution/webhook", json=extended_text_message_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"

    def test_media_message_is_ignored(self, client: TestClient, media_message_payload):
        """Test that media messages are ignored (MVP only handles text)."""
        response = client.post("/api/v1/evolution/webhook", json=media_message_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["status"] == "ignored"
        assert data["result"]["reason"] == "media_not_supported"
