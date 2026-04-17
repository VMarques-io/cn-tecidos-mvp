"""End-to-end integration tests for C&N Tecidos WhatsApp Agent."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import copy


class TestE2EFAQFlow:
    def test_complete_faq_flow_text_response(self, client, valid_text_message_payload):
        payload = copy.deepcopy(valid_text_message_payload)
        payload["data"]["key"]["id"] = "faq-flow-001"
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, patch("services.whatsapp.send_text") as mock_send:
            mock_graph.ainvoke = AsyncMock(return_value={"response": "Temos algodão, seda e linho!", "flow_step": "idle", "is_human_active": False})
            mock_send.return_value = {"status": "simulated"}
            response = client.post("/api/v1/evolution/webhook", json=payload)
            assert response.status_code == 200
            assert response.json()["status"] == "processed"
            assert response.json()["result"]["status"] == "success"


class TestE2EHandoffFlow:
    def test_complete_handoff_flow(self, client, valid_text_message_payload):
        payload = copy.deepcopy(valid_text_message_payload)
        payload["data"]["key"]["id"] = "handoff-flow-001"
        payload["data"]["message"] = {"conversation": "Quero falar com atendente"}
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, patch("services.whatsapp.send_text") as mock_send:
            mock_graph.ainvoke = AsyncMock(return_value={"response": "https://wa.me/558335073620", "flow_step": "handoff", "is_human_active": True})
            mock_send.return_value = {"status": "simulated"}
            response = client.post("/api/v1/evolution/webhook", json=payload)
            assert response.status_code == 200
            assert response.json()["status"] == "processed"


class TestE2EMultipleMessages:
    def test_multiple_messages_processed_independently(self, client, valid_text_message_payload):
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, patch("services.whatsapp.send_text") as mock_send:
            mock_send.return_value = {"status": "simulated"}
            p1 = copy.deepcopy(valid_text_message_payload)
            p1["data"]["key"]["id"] = "msg-001"
            p1["data"]["message"] = {"conversation": "Primeira"}
            mock_graph.ainvoke = AsyncMock(return_value={"response": "Resposta 1", "flow_step": "idle"})
            r1 = client.post("/api/v1/evolution/webhook", json=p1)
            assert r1.json()["status"] == "processed"

            p2 = copy.deepcopy(valid_text_message_payload)
            p2["data"]["key"]["id"] = "msg-002"
            p2["data"]["message"] = {"conversation": "Segunda"}
            mock_graph.ainvoke = AsyncMock(return_value={"response": "Resposta 2", "flow_step": "idle"})
            r2 = client.post("/api/v1/evolution/webhook", json=p2)
            assert r2.json()["status"] == "processed"
            assert mock_send.call_count == 2


class TestE2EGracefulDegradation:
    def test_graceful_degradation_when_fashion_graph_fails(self, client, valid_text_message_payload):
        payload = copy.deepcopy(valid_text_message_payload)
        payload["data"]["key"]["id"] = "error-001"
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, patch("services.whatsapp.send_text") as mock_send:
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph failed"))
            mock_send.return_value = {"status": "simulated"}
            response = client.post("/api/v1/evolution/webhook", json=payload)
            assert response.status_code == 200
            assert response.json()["result"]["reason"] == "graph_error"


class TestE2EHealthAndRootEndpoints:
    def test_health_endpoint_integration(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
