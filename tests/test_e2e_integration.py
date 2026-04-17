"""
End-to-end integration tests for C&N Tecidos WhatsApp Agent.

These tests verify the complete flow from webhook → graph → response,
testing the full integration between all components.

Test Scenarios:
1. Complete FAQ Flow - text message through webhook to response
2. Complete Handoff Flow - HUMANO intent triggers handoff link
3. Cancel Flow - cancel message ends gracefully
4. Multiple Messages (Conversation) - idempotency and sequence handling
5. Graceful Degradation - app works when fashion_graph fails
6. Health + Root Endpoints Integration - basic endpoint verification
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import copy


class TestE2EFAQFlow:
    """End-to-end tests for complete FAQ flow."""

    def test_complete_faq_flow_text_response(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test 1: Complete FAQ Flow
        
        - Send a text message via webhook POST
        - Mock the fashion_graph.ainvoke to return a FAQ response
        - Verify the webhook returns 200 with status 'processed'
        - Verify the response was sent (mock whatsapp.send_text was called)
        """
        payload = copy.deepcopy(valid_text_message_payload)
        payload["data"]["key"]["id"] = "faq-flow-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Olá! Temos algodão, seda e linho disponíveis. Como posso ajudar?",
                "flow_step": "idle",
                "is_human_active": False,
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["result"]["status"] == "success"
            assert data["result"]["flow_step"] == "idle"
            
            mock_graph.ainvoke.assert_called_once()
            call_args = mock_graph.ainvoke.call_args[0][0]
            assert call_args["remote_jid"] == "558399999999@s.whatsapp.net"
            assert call_args["incoming_text"] == "Olá, gostaria de saber sobre tecidos"
            assert call_args["instance_name"] == "test-instance"
            
            mock_send_text.assert_called_once()
            args = mock_send_text.call_args[0]
            assert args[0] == "test-instance"
            assert args[1] == "558399999999@s.whatsapp.net"
            assert "algodão, seda e linho" in args[2]

class TestE2EHandoffFlow:
    """End-to-end tests for human handoff flow."""

    def test_complete_handoff_flow(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test 2: Complete Handoff Flow
        
        - Send a message that triggers HUMANO intent
        - Verify handoff link is returned
        - Verify is_human_active is set to True
        """
        handoff_payload = copy.deepcopy(valid_text_message_payload)
        handoff_payload["data"]["key"]["id"] = "handoff-flow-001"
        handoff_payload["data"]["message"] = {"conversation": "Quero falar com atendente humano"}
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "https://test-handoff.link",
                "flow_step": "handoff",
                "is_human_active": True,
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=handoff_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            
            mock_graph.ainvoke.assert_called_once()
            call_args = mock_graph.ainvoke.call_args[0][0]
            assert call_args["incoming_text"] == "Quero falar com atendente humano"
            
            mock_send_text.assert_called_once()
            args = mock_send_text.call_args[0]
            assert args[2] == "https://test-handoff.link"


class TestE2ECancelFlow:
    """End-to-end tests for cancel flow."""

    def test_cancel_flow_ends_gracefully(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test 3: Cancel Flow
        
        - Send a cancel message
        - Verify the flow ends gracefully
        """
        cancel_payload = copy.deepcopy(valid_text_message_payload)
        cancel_payload["data"]["key"]["id"] = "cancel-flow-001"
        cancel_payload["data"]["message"] = {"conversation": "cancelar"}
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Goodbye!",
                "flow_step": "idle",
                "is_human_active": False,
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=cancel_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            
            mock_graph.ainvoke.assert_called_once()
            
            mock_send_text.assert_called_once()
            args = mock_send_text.call_args[0]
            assert args[2] == "Goodbye!"


class TestE2EMultipleMessages:
    """End-to-end tests for conversation with multiple messages."""

    def test_multiple_messages_processed_independently(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test 4: Multiple Messages (Conversation)
        
        - Send multiple messages in sequence
        - Verify idempotency (same message ID not processed twice)
        - Verify different message IDs are processed independently
        """
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            payload1 = copy.deepcopy(valid_text_message_payload)
            payload1["data"]["key"]["id"] = "msg-id-001"
            payload1["data"]["message"] = {"conversation": "Primeira mensagem"}
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta 1",
                "flow_step": "idle",
                
            })
            
            response1 = client.post("/api/v1/evolution/webhook", json=payload1)
            assert response1.status_code == 200
            assert response1.json()["status"] == "processed"
            
            payload2 = copy.deepcopy(valid_text_message_payload)
            payload2["data"]["key"]["id"] = "msg-id-002"
            payload2["data"]["message"] = {"conversation": "Segunda mensagem"}
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta 2",
                "flow_step": "idle",
                
            })
            
            response2 = client.post("/api/v1/evolution/webhook", json=payload2)
            assert response2.status_code == 200
            assert response2.json()["status"] == "processed"
            
            payload3 = copy.deepcopy(payload1)
            payload3["data"]["message"] = {"conversation": "Mensagem duplicada"}
            
            response3 = client.post("/api/v1/evolution/webhook", json=payload3)
            assert response3.status_code == 200
            data3 = response3.json()
            assert data3["result"]["status"] == "ignored"
            assert data3["result"]["reason"] == "duplicate"
            
            assert mock_send_text.call_count == 2

    def test_conversation_with_different_jids(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test that different JIDs (different users) are processed independently.
        """
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            payload1 = copy.deepcopy(valid_text_message_payload)
            payload1["data"]["key"]["id"] = "msg-user1-001"
            payload1["data"]["key"]["remoteJid"] = "558311111111@s.whatsapp.net"
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Olá usuário 1",
                "flow_step": "idle",
                
            })
            
            response1 = client.post("/api/v1/evolution/webhook", json=payload1)
            assert response1.status_code == 200
            
            payload2 = copy.deepcopy(valid_text_message_payload)
            payload2["data"]["key"]["id"] = "msg-user2-001"
            payload2["data"]["key"]["remoteJid"] = "558322222222@s.whatsapp.net"
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Olá usuário 2",
                "flow_step": "idle",
                
            })
            
            response2 = client.post("/api/v1/evolution/webhook", json=payload2)
            assert response2.status_code == 200
            
            assert mock_send_text.call_count == 2
            
            calls = mock_send_text.call_args_list
            assert calls[0][0][1] == "558311111111@s.whatsapp.net"
            assert calls[1][0][1] == "558322222222@s.whatsapp.net"


class TestE2EGracefulDegradation:
    """End-to-end tests for graceful degradation scenarios."""

    def test_graceful_degradation_when_fashion_graph_fails(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test 5: Graceful Degradation
        
        - Test that the app works even when fashion_graph fails
        - Verify error handling returns proper response
        """
        error_payload = copy.deepcopy(valid_text_message_payload)
        error_payload["data"]["key"]["id"] = "error-msg-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph compilation failed"))
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=error_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["result"]["status"] == "error"
            assert data["result"]["reason"] == "graph_error"
            
            mock_send_text.assert_called_once()
            args = mock_send_text.call_args[0]
            assert "Ops! Ocorreu um erro interno" in args[2]
            assert "api.whatsapp.com" in args[2]

    def test_graceful_degradation_when_whatsapp_send_fails(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test graceful handling when WhatsApp send fails.
        """
        error_payload = copy.deepcopy(valid_text_message_payload)
        error_payload["data"]["key"]["id"] = "send-error-msg-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta válida",
                "flow_step": "idle",
                
            })
            mock_send_text.side_effect = Exception("WhatsApp API unavailable")
            
            response = client.post("/api/v1/evolution/webhook", json=error_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["result"]["status"] == "error"
            assert data["result"]["reason"] == "send_failed"


class TestE2EHealthAndRootEndpoints:
    """End-to-end tests for health and root endpoints."""

    def test_health_endpoint_integration(
        self, client: TestClient
    ):
        """
        Test 6: Health + Root Endpoints Integration
        
        - Verify /health returns correct JSON
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"

    def test_root_endpoint_integration(
        self, client: TestClient
    ):
        """
        Verify / returns correct JSON.
        """
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cn_tecidos_ai"
        assert data["version"] == "1.0.0"

    def test_health_and_root_consistency(
        self, client: TestClient
    ):
        """
        Verify /health and / return consistent data.
        """
        health_response = client.get("/health")
        root_response = client.get("/")
        
        assert health_response.status_code == 200
        assert root_response.status_code == 200
        
        health_data = health_response.json()
        root_data = root_response.json()
        
        # Both should have same structure
        assert health_data["status"] == root_data["status"]
        assert health_data["service"] == root_data["service"]
        assert health_data["version"] == root_data["version"]


class TestE2EBatchMessages:
    """End-to-end tests for batch message processing."""

    def test_batch_messages_processing(
        self, client: TestClient
    ):
        """
        Test processing multiple messages in a single webhook payload.
        """
        batch_payload = {
            "event": "messages.upsert",
            "instance": "test-instance",
            "data": {
                "messages": [
                    {
                        "key": {
                            "remoteJid": "558399999999@s.whatsapp.net",
                            "fromMe": False,
                            "id": "batch-msg-001"
                        },
                        "message": {"conversation": "Primeira mensagem do batch"}
                    },
                    {
                        "key": {
                            "remoteJid": "558399999999@s.whatsapp.net",
                            "fromMe": False,
                            "id": "batch-msg-002"
                        },
                        "message": {"conversation": "Segunda mensagem do batch"}
                    }
                ]
            }
        }
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            # Mock different responses for each message
            responses = [
                {"response": "Resposta 1", "flow_step": "idle"},
                {"response": "Resposta 2", "flow_step": "idle"},
            ]
            mock_graph.ainvoke = AsyncMock(side_effect=responses)
            
            # Send batch webhook request
            response = client.post("/api/v1/evolution/webhook", json=batch_payload)
            
            # Verify webhook response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert len(data["results"]) == 2
            
            # Verify both messages were processed
            assert mock_graph.ainvoke.call_count == 2
            assert mock_send_text.call_count == 2


class TestE2EExtendedTextMessage:
    """End-to-end tests for extended text message handling."""

    def test_extended_text_message_e2e(
        self, client: TestClient, extended_text_message_payload
    ):
        """
        Test complete flow with extendedTextMessage (formatted text).
        """
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta para texto formatado",
                "flow_step": "idle",
                
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            # Send webhook request with extended text
            response = client.post("/api/v1/evolution/webhook", json=extended_text_message_payload)
            
            # Verify webhook response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            
            # Verify graph received the extended text
            mock_graph.ainvoke.assert_called_once()
            call_args = mock_graph.ainvoke.call_args[0][0]
            assert call_args["incoming_text"] == "Texto com formatação"


class TestE2EEventVariations:
    """End-to-end tests for different event format variations."""

    def test_messages_upsert_lowercase_event(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test that 'messages.upsert' (lowercase) event is handled.
        """
        payload = copy.deepcopy(valid_text_message_payload)
        payload["event"] = "messages.upsert"
        payload["data"]["key"]["id"] = "lowercase-event-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",
                
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=payload)
            
            assert response.status_code == 200
            assert response.json()["status"] == "processed"
            mock_graph.ainvoke.assert_called_once()

    def test_messages_upsert_uppercase_event(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test that 'MESSAGES_UPSERT' (uppercase) event is handled.
        """
        payload = copy.deepcopy(valid_text_message_payload)
        payload["event"] = "MESSAGES_UPSERT"
        payload["data"]["key"]["id"] = "uppercase-event-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",
                
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=payload)
            
            assert response.status_code == 200
            assert response.json()["status"] == "processed"
            mock_graph.ainvoke.assert_called_once()

    def test_messages_dot_upsert_event(
        self, client: TestClient, valid_text_message_payload
    ):
        """
        Test that 'MESSAGES.UPSERT' (dot notation) event is handled.
        """
        payload = copy.deepcopy(valid_text_message_payload)
        payload["event"] = "MESSAGES.UPSERT"
        payload["data"]["key"]["id"] = "dot-event-001"
        
        with patch("agents.fashion_graph.fashion_graph") as mock_graph, \
             patch("services.whatsapp.send_text") as mock_send_text:
            
            mock_graph.ainvoke = AsyncMock(return_value={
                "response": "Resposta",
                "flow_step": "idle",
                
            })
            mock_send_text.return_value = {"status": "simulated", "message": "sent"}
            
            response = client.post("/api/v1/evolution/webhook", json=payload)
            
            assert response.status_code == 200
            assert response.json()["status"] == "processed"
