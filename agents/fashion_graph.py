from typing import Optional
import asyncio

from .state import AgentState, default_state
from .nodes import triage_node, faq_node, human_handoff_node, cancel_node


class StateGraph:
    def __init__(self):
        self.entry = "triage"
        self.nodes = {
            "triage": triage_node,
            "faq": faq_node,
            "handoff": human_handoff_node,
            "cancel": cancel_node,
        }

    def save_memory(self, state: AgentState) -> None:
        try:
            import os
            path = os.path.join(os.path.dirname(__file__), "memory.log")
            with open(path, "a", encoding="utf-8") as f:
                f.write(str(state) + "\n")
        except Exception:
            pass

    def run(self, state: AgentState) -> str:
        current = self.entry
        response: str = state.get("response", "")
        while current:
            node_func = self.nodes.get(current)
            if node_func is None:
                break
            result = node_func(state)
            if not isinstance(result, dict):
                break
            updates = result.get("state_update", {})
            if updates:
                try:
                    state.update(updates)
                except Exception:
                    pass
            if "response" in result and result["response"]:
                response = result["response"]
                state["response"] = response
            next_node = result.get("node")
            self.save_memory(state)
            if not next_node or next_node == "END":
                break
            current = next_node
        return response

    async def ainvoke(self, state: AgentState) -> AgentState:
        """
        Async version of graph execution for webhook handler.
        
        Executes the graph synchronously (nodes are sync) but provides
        async interface for FastAPI compatibility.
        
        Args:
            state: Initial AgentState with remote_jid, incoming_text, etc.
            
        Returns:
            Final AgentState after graph execution
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.run, state)
        return state


_graph_instance: Optional[StateGraph] = None


def get_fashion_graph() -> StateGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = StateGraph()
    return _graph_instance


# Global export para import direto: from agents.fashion_graph import fashion_graph
fashion_graph = get_fashion_graph()
