"""Tests for human handoff node."""
import pytest
import os
from unittest.mock import patch

from agents.nodes import human_handoff_node
from agents.state import default_state


class TestHumanHandoffNode:
    def test_response_contains_handoff_link(self):
        state = default_state(incoming_text="Quero falar com atendente", flow_step="triaged", intent="HUMANO", is_human_active=False)
        expected_link = os.environ.get("HANDOFF_LINK", "https://test-handoff.link")
        result = human_handoff_node(state)
        assert result["response"] == expected_link

    def test_is_human_active_set_to_true(self):
        state = default_state(incoming_text="Precisa de ajuda", flow_step="triaged", intent="HUMANO", is_human_active=False)
        result = human_handoff_node(state)
        assert result["state_update"]["is_human_active"] is True
        assert result["node"] == "idle"

    def test_handoff_link_from_environment(self):
        custom_link = "https://custom-handoff.example.com"
        with patch.dict(os.environ, {"HANDOFF_LINK": custom_link}):
            state = default_state(incoming_text="Atendimento", flow_step="triaged", intent="HUMANO")
            result = human_handoff_node(state)
            assert result["response"] == custom_link
