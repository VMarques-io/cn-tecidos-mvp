"""Tests for triage node classification logic."""
import pytest
from unittest.mock import patch, MagicMock

from agents.nodes import triage_node, classify_with_gemini
from agents.state import AgentState, default_state


class TestTriageClassification:
    def test_faq_classification_with_gemini(self):
        state = default_state(incoming_text="Quais tecidos vocês têm para vestidos de festa?", flow_step="idle", is_human_active=False)
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.return_value = "FAQ"
            result = triage_node(state)
            assert result["node"] == "faq"
            assert result["state_update"]["intent"] == "FAQ"

    def test_humano_classification_with_keyword_fallback(self):
        state = default_state(incoming_text="Quero falar com um humano", flow_step="idle", is_human_active=False)
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.side_effect = Exception("Gemini API unavailable")
            result = triage_node(state)
            assert result["node"] == "handoff"
            assert result["state_update"]["intent"] == "HUMANO"

    def test_cancel_classification(self):
        state = default_state(incoming_text="Cancelar atendimento", flow_step="idle", is_human_active=False)
        with patch("agents.nodes.classify_with_gemini") as mock_classify:
            mock_classify.return_value = "CANCEL"
            result = triage_node(state)
            assert result["node"] == "cancel"

    def test_is_human_active_bypass(self):
        state = default_state(incoming_text="Qualquer mensagem", flow_step="idle", is_human_active=True)
        result = triage_node(state)
        assert result["node"] == "handoff"


class TestClassifyWithGemini:
    def test_classify_with_gemini_returns_faq(self):
        with patch("agents.nodes.genai") as mock_genai:
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock()]
            mock_response.candidates[0].content = "FAQ"
            mock_genai.chat.return_value = mock_response
            result = classify_with_gemini("Quais tecidos vocês têm?")
            assert result == "FAQ"

    def test_classify_with_gemini_keyword_fallback_humano(self):
        with patch("agents.nodes.genai") as mock_genai:
            mock_genai.chat.side_effect = Exception("API Error")
            result = classify_with_gemini("Preciso de ajuda humana")
            assert result == "HUMANO"
