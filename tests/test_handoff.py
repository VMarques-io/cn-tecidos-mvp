"""Tests for human handoff node."""

import pytest
import os
from unittest.mock import patch

from agents.nodes import human_handoff_node
from agents.state import default_state


class TestHumanHandoffNode:
    """Test suite for human handoff functionality."""

    def test_response_contains_handoff_link(self):
        """Test that handoff response contains the HANDOFF_LINK."""
        state = default_state(
            incoming_text="Quero falar com atendente",
            flow_step="triaged",
            intent="HUMANO",
            is_human_active=False,
        )
        
        expected_link = os.environ.get("HANDOFF_LINK", "https://test-handoff.link")
        
        result = human_handoff_node(state)
        
        assert result["response"] == expected_link
        assert "http" in result["response"]

    def test_is_human_active_set_to_true(self):
        """Test that is_human_active is set to True after handoff."""
        state = default_state(
            incoming_text="Preciso de ajuda humana",
            flow_step="triaged",
            intent="HUMANO",
            is_human_active=False,
        )
        
        result = human_handoff_node(state)
        
        assert result["state_update"]["is_human_active"] is True
        assert result["state_update"]["flow_step"] == "handoff"
        assert result["node"] == "idle"

    def test_handoff_link_from_environment(self):
        """Test that handoff link is read from environment variable."""
        custom_link = "https://custom-handoff.example.com"
        
        with patch.dict(os.environ, {"HANDOFF_LINK": custom_link}):
            state = default_state(
                incoming_text="Atendimento humano",
                flow_step="triaged",
                intent="HUMANO",
            )
            
            result = human_handoff_node(state)
            
            assert result["response"] == custom_link
