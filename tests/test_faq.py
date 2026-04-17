"""Tests for FAQ node response generation."""

import pytest
from unittest.mock import patch, MagicMock

from agents.nodes import faq_node, _get_fabric_context, _resolve_color
from agents.state import default_state


class TestFAQResponseGeneration:
    """Test suite for FAQ node response generation."""

    def test_response_generation_with_knowledge_base(self):
        """Test that FAQ responses include knowledge base context."""
        state = default_state(
            incoming_text="Quais tecidos vocês recomendam para vestidos?",
            flow_step="triaged",
            intent="FAQ",
        )
        
        with patch("agents.nodes._get_fabric_context") as mock_context, \
             patch("agents.nodes.classify_with_gemini") as mock_gemini:
            
            mock_context.return_value = "Tecidos disponíveis: algodão, seda, linho"
            mock_gemini.return_value = "Recomendamos seda para vestidos de festa!"
            
            result = faq_node(state)
            
            assert result["node"] == "faq"
            assert result["response"] == "Recomendamos seda para vestidos de festa!"
            assert result["state_update"]["flow_step"] == "idle"
            mock_context.assert_called_once()

    def test_color_resolution_in_responses(self):
        """Test that color resolution is included in FAQ responses."""
        state = default_state(
            incoming_text="Quais cores estão em alta?",
            flow_step="triaged",
            intent="FAQ",
        )
        
        with patch("agents.nodes._resolve_color") as mock_color, \
             patch("agents.nodes._get_fabric_context") as mock_context, \
             patch("agents.nodes.classify_with_gemini") as mock_gemini:
            
            mock_color.return_value = "Paleta: tons terrosos (terracota, creme, amêndoa)"
            mock_context.return_value = "Tecidos em estoque"
            mock_gemini.return_value = "As cores em alta são terracota e creme!"
            
            result = faq_node(state)
            
            mock_color.assert_called_once()
            assert result["response"] is not None

    def test_graceful_degradation_when_gemini_unavailable(self):
        """Test graceful degradation when Gemini API is unavailable."""
        state = default_state(
            incoming_text="Qual o preço do algodão?",
            flow_step="triaged",
            intent="FAQ",
        )
        
        with patch("agents.nodes._get_fabric_context") as mock_context, \
             patch("agents.nodes.classify_with_gemini") as mock_gemini:
            
            mock_context.return_value = "Tecidos: algodão R$25/m, seda R$80/m"
            mock_gemini.side_effect = Exception("Gemini API unavailable")
            
            result = faq_node(state)
            
            assert result["node"] == "faq"
            assert result["state_update"]["flow_step"] == "idle"


class TestFabricContext:
    """Test suite for fabric context helper functions."""

    def test_get_fabric_context_with_service_available(self):
        """Test _get_fabric_context when knowledge service is available."""
        with patch("agents.nodes._safe_import_knowledge") as mock_import:
            mock_knowledge = MagicMock()
            mock_knowledge.get_fabric_context.return_value = "Tecidos: algodão, seda, linho"
            mock_import.return_value = mock_knowledge
            
            result = _get_fabric_context()
            
            assert result == "Tecidos: algodão, seda, linho"

    def test_get_fabric_context_with_service_unavailable(self):
        """Test _get_fabric_context fallback when knowledge service fails."""
        with patch("agents.nodes._safe_import_knowledge") as mock_import:
            mock_import.return_value = None
            
            result = _get_fabric_context()
            
            assert "Fabric context" in result
            assert "cotton" in result.lower() or "silk" in result.lower()

    def test_resolve_color_returns_string(self):
        """Test that _resolve_color returns a color hint string."""
        result = _resolve_color()
        
        assert isinstance(result, str)
        assert len(result) > 0
