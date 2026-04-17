from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict):
    remote_jid: str
    instance_name: str
    profile_type: str
    incoming_text: str
    intent: str
    flow_step: str
    chat_history: List[str]
    response: str
    is_human_active: bool
    should_end: bool


def default_state(**overrides: Any) -> AgentState:
    base: Dict[str, Any] = {
        "remote_jid": "",
        "instance_name": "LangGraph-T5",
        "profile_type": "default",
        "incoming_text": "",
        "intent": "FAQ",
        "flow_step": "idle",
        "chat_history": [],
        "response": "",
        "is_human_active": False,
        "should_end": False,
    }
    base.update(overrides)
    return base
