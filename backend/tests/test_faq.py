"""Tests for FAQ node response generation."""
import pytest
from unittest.mock import patch, MagicMock

from agents.nodes import faq_node, _get_fabric_context, _resolve_color
from agents.state import default_state


class TestFAQResponseGeneration:
    def test_response_generation_with_knowledge_base(self):
        state = default_state(incoming_text="Quais tecidos vocês recomendam?", flow_step="triaged", intent="FAQ")
        with patch("agents.nodes._get_fabric_context") as mock_context, patch("agents.nodes.classify_with_gemini") as mock_gemini:
            mock_context.return_value = "Tecidos: algodão, seda, linho"
            mock_gemini.return_value = "Recomendamos seda!"
            result = faq_node(state)
            assert result["node"] == "faq"
            assert result["state_update"]["flow_step"] == "idle"

    def test_graceful_degradation_when_gemini_unavailable(self):
        state = default_state(incoming_text="Qual o preço?", flow_step="triaged", intent="FAQ")
        with patch("agents.nodes._get_fabric_context") as mock_context, patch("agents.nodes.classify_with_gemini") as mock_gemini:
            mock_context.return_value = "Tecidos disponíveis"
            mock_gemini.side_effect = Exception("Gemini API unavailable")
            result = faq_node(state)
            assert result["node"] == "faq"


class TestFabricContext:
    def test_get_fabric_context_with_service_unavailable(self):
        with patch("agents.nodes._safe_import_knowledge") as mock_import:
            mock_import.return_value = None
            result = _get_fabric_context()
            assert "Fabric context" in result

    def test_resolve_color_returns_string(self):
        result = _resolve_color()
        assert isinstance(result, str)
        assert len(result) > 0
