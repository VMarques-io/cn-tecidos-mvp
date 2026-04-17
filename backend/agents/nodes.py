import os
from typing import Dict, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .state import AgentState


def _safe_import_knowledge():
    try:
        import services.knowledge as knowledge
        return knowledge
    except Exception:
        return None


def _get_fabric_context() -> str:
    knowledge = _safe_import_knowledge()
    if knowledge and hasattr(knowledge, "get_fabric_context"):
        try:
            return knowledge.get_fabric_context()
        except Exception:
            pass
    return "Fabric context: data about fabrics (cotton, silk, etc.) available in knowledge base."


def _resolve_color() -> str:
    return "Color palette: warm tones (terracotta, cream, almond)."


def classify_with_gemini(text: str) -> str:
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini API key not configured")
        genai.configure(api_key=api_key)
        resp = genai.chat(model="gemini-1.5-flash", messages=[{"role": "user", "content": text}], temperature=0.0)
        if hasattr(resp, "candidates") and resp.candidates:
            content = getattr(resp.candidates[0], "content", "")
        elif isinstance(resp, dict) and resp.get("content"):
            content = resp["content"]
        else:
            content = str(resp)
        if not content:
            raise ValueError("Empty Gemini response")
        lower = content.lower()
        if "hum" in lower:
            return "HUMANO"
        if "cancel" in lower:
            return "CANCEL"
        if "faq" in lower or "fabric" in lower or "tecido" in lower:
            return "FAQ"
        return "FAQ"
    except Exception:
        t = text.lower()
        if "handoff" in t or "hum" in t:
            return "HUMANO"
        if "cancel" in t or "end" in t:
            return "CANCEL"
        return "FAQ"


def triage_node(state: AgentState) -> Dict[str, Any]:
    if state.get("is_human_active"):
        return {"node": "handoff", "state_update": {"flow_step": "handoff", "intent": "HUMANO"}, "response": None}

    flow = state.get("flow_step", "idle")
    if str(flow).startswith("awaiting_"):
        intent = state.get("intent", "FAQ")
        target = "faq" if intent.upper().startswith("FAQ") else "handoff" if intent.upper().startswith("HUMANO") else "cancel"
        return {"node": target, "state_update": {"intent": intent}, "response": None}

    incoming = state.get("incoming_text", "")
    try:
        classification = classify_with_gemini(incoming)
    except Exception:
        t = incoming.lower()
        if "handoff" in t or "hum" in t or "atendente" in t or "humano" in t:
            classification = "HUMANO"
        elif "cancel" in t or "end" in t:
            classification = "CANCEL"
        else:
            classification = "FAQ"
    intent = classification
    target = {"FAQ": "faq", "HUMANO": "handoff", "CANCEL": "cancel"}.get(intent, "faq")
    return {"node": target, "state_update": {"intent": intent, "flow_step": "triaged"}, "response": None}


def faq_node(state: AgentState) -> Dict[str, Any]:
    fabric_context = _get_fabric_context()
    color_hint = _resolve_color()
    user_question = state.get("incoming_text", "")
    prompt = f"Respond in Camila persona (warm, <=3 paragraphs) to fabric-related question. Context: {fabric_context} {color_hint} User asks: {user_question}"
    try:
        answer = classify_with_gemini(prompt)
    except Exception:
        answer = f"Olá! Com base na nossa coleção: {fabric_context} {color_hint}"
    state_updates: Dict[str, Any] = {"response": answer, "flow_step": "idle"}
    return {"node": "faq", "state_update": state_updates, "response": answer}


def human_handoff_node(state: AgentState) -> Dict[str, Any]:
    state_updates = {"is_human_active": True, "flow_step": "handoff"}
    handoff_link = os.environ.get("HANDOFF_LINK", "https://api.whatsapp.com/send/?phone=558335073620...")
    return {"node": "idle", "state_update": state_updates, "response": handoff_link}


def cancel_node(state: AgentState) -> Dict[str, Any]:
    state_updates = {"flow_step": "idle", "incoming_text": "", "intent": "FAQ"}
    return {"node": "END", "state_update": state_updates, "response": "Goodbye!"}
