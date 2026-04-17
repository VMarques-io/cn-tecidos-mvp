"""Tests for triage node classification logic."""

import pytest
from unittest.mock import patch, MagicMock

from agents.nodes import triage_node, classify_with_gemini
from agents.state import AgentState, default_state


class TestTriageClassification:
    """Test suite for triage node intent classification."""

    def test_faq_classification_with_gemini(self):
        """Test FAQ classification using Gemini API."""
        state = default_state(
            incoming_text="Quais tecidos vocês têm para vestidos de festa?",
            flow_step="idle",
            is_human_active=False,
        )
        
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.return_value = "FAQ"
            
            result = triage_node(state)
            
            assert result["node"] == "faq"
            assert result["state_update"]["intent"] == "FAQ"
            mock_classify.assert_called_once()

    def test_humano_classification_with_keyword_fallback(self):
        """Test HUMANO classification using keyword fallback when Gemini unavailable."""
        state = default_state(
            incoming_text="Quero falar com um humano",
            flow_step="idle",
            is_human_active=False,
        )
        
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.side_effect = Exception("Gemini API unavailable")
            
            result = triage_node(state)
            
            assert result["node"] == "handoff"
            assert result["state_update"]["intent"] == "HUMANO"

    def test_cancel_classification(self):
        """Test CANCEL classification."""
        state = default_state(
            incoming_text="Cancelar atendimento",
            flow_step="idle",
            is_human_active=False,
        )
        
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.return_value = "CANCEL"
            
            result = triage_node(state)
            
            assert result["node"] == "cancel"
            assert result["state_update"]["intent"] == "CANCEL"

    def test_is_human_active_bypass(self):
        """Test that is_human_active=True bypasses classification and goes to handoff."""
        state = default_state(
            incoming_text="Qualquer mensagem",
            flow_step="idle",
            is_human_active=True,
        )
        
        result = triage_node(state)
        
        assert result["node"] == "handoff"
        assert result["state_update"]["flow_step"] == "handoff"
        assert result["state_update"]["intent"] == "HUMANO"


class TestClassifyWithGemini:
    """Test suite for classify_with_gemini function."""

    def test_classify_with_gemini_returns_faq(self):
        """Test that classify_with_gemini returns FAQ for fabric questions."""
        with patch("agents.nodes.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock()]
            mock_response.candidates[0].content = "FAQ"
            mock_genai.chat.return_value = mock_response
            
            result = classify_with_gemini("Quais tecidos vocês têm?")
            
            assert result == "FAQ"

    def test_classify_with_gemini_returns_humano(self):
        """Test that classify_with_gemini returns HUMANO for human requests."""
        with patch("agents.nodes.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock()]
            mock_response.candidates[0].content = "HUMANO"
            mock_genai.chat.return_value = mock_response
            
            result = classify_with_gemini("Quero falar com atendente")
            
            assert result == "HUMANO"

    def test_classify_with_gemini_keyword_fallback_humano(self):
        """Test keyword fallback for humano when Gemini fails."""
        with patch("agents.nodes.genai") as mock_genai:
            mock_genai.chat.side_effect = Exception("API Error")
            
            result = classify_with_gemini("Preciso de ajuda humana")
            
            assert result == "HUMANO"

    def test_classify_with_gemini_keyword_fallback_cancel(self):
        """Test keyword fallback for cancel when Gemini fails."""
        with patch("agents.nodes.genai") as mock_genai:
            mock_genai.chat.side_effect = Exception("API Error")
            
            result = classify_with_gemini("Cancelar conversa")
            
            assert result == "CANCEL"

    def test_classify_with_gemini_keyword_fallback_faq(self):
        """Test keyword fallback defaults to FAQ when no keywords match."""
        with patch("agents.nodes.genai") as mock_genai:
            mock_genai.chat.side_effect = Exception("API Error")
            
            result = classify_with_gemini("Qual o preço do algodão?")
            
            assert result == "FAQ"
