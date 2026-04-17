from typing import Optional
import asyncio

from .state import AgentState
from .nodes import conversation_node


class StateGraph:
    def __init__(self):
        self.entry = "conversation"
        self.nodes = {
            "conversation": conversation_node,
        }

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
            if not next_node or next_node == "END":
                break
            current = next_node
        return response

    async def ainvoke(self, state: AgentState) -> AgentState:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.run, state)
        return state


_graph_instance: Optional[StateGraph] = None


def get_fashion_graph() -> StateGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = StateGraph()
    return _graph_instance


fashion_graph = get_fashion_graph()