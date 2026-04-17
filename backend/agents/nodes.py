import os
import logging
from typing import Dict, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .state import AgentState

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

HANDOFF_LINK = os.environ.get(
    "HANDOFF_LINK",
    "https://api.whatsapp.com/send/?phone=558335073620"
    "&text=Ol%C3%A1%21+Gostaria+de+falar+com+um+atendente+da+C%26N+Tecidos."
    "&type=phone_number&app_absent=0"
)

# Friendly fallback message when AI fails
AI_FAILURE_MESSAGE = (
    "Me perdoa, mas vou ter que transferir seu atendimento, tá bom? 🙏\n\n"
    f"É só clicar aqui pra falar com a gente: {HANDOFF_LINK}"
)


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
    return (
        "C&N Tecidos é uma loja de tecidos e aviamentos em Campina Grande, PB. "
        "Oferece tecidos variados: algodão, linho, seda, viscose, jeans, malha, "
        "tecido para festa, tecido para decoração, aviamentos como botões, "
        "zíperes, linhas, elásticos. Atende tanto pessoa física quanto profissional "
        "de moda e costura. Preços acessíveis e atendimento personalizado."
    )


def classify_with_gemini(text: str) -> str:
    """Classify user intent using Google Gemini API."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini API key not configured")
        if genai is None:
            raise RuntimeError("google-generativeai not installed")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(text)

        if not response or not response.text:
            raise ValueError("Empty Gemini response")

        content = response.text.strip().upper()
        if "HUMANO" in content or "HUMAN" in content:
            return "HUMANO"
        if "CANCEL" in content or "CANCELAR" in content:
            return "CANCEL"
        return "FAQ"
    except Exception as e:
        logger.warning(f"[GEMINI] Classification fallback: {e}")
        return _keyword_classify(text)


def _keyword_classify(text: str) -> str:
    """Fallback classification using keywords."""
    t = text.lower().strip()
    human_keywords = ["falar com atendente", "falar com humano", "atendente", "quero falar com", "pessoa real", "agente humano"]
    for kw in human_keywords:
        if kw in t:
            return "HUMANO"
    cancel_keywords = ["cancelar", "encerrar", "tchau", "bye", "não quero mais"]
    for kw in cancel_keywords:
        if kw in t:
            return "CANCEL"
    return "FAQ"


def generate_response_with_gemini(prompt: str) -> str:
    """Generate a response using Google Gemini API.
    
    Returns empty string on ANY failure (quota, auth, network, etc).
    Caller is responsible for handling the failure gracefully.
    """
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini API key not configured")
        if genai is None:
            raise RuntimeError("google-generativeai not installed")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)

        if response and response.text:
            return response.text
        raise ValueError("Empty Gemini response")
    except Exception as e:
        logger.error(f"[GEMINI] Response generation FAILED: {e}")
        return ""


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
        classification = classify_with_gemini(
            "Você é um classificador de mensagens de WhatsApp para uma loja de tecidos. "
            "Classifique a intenção da mensagem abaixo em EXATAMENTE uma palavra:\n\n"
            "- FAQ: Perguntas sobre produtos, preços, horário, localização, saudações, conversa geral\n"
            "- HUMANO: Cliente pede explicitamente para falar com atendente/humano\n"
            "- CANCEL: Cliente quer encerrar a conversa\n\n"
            "IMPORTANTE: Saudações como 'olá', 'bom dia', 'boa tarde' são sempre FAQ.\n"
            "Perguntas sobre tecidos, preços, horários são sempre FAQ.\n"
            "Só classifique como HUMANO se o cliente pedir EXPLICITAMENTE um atendente.\n\n"
            f"Mensagem: {incoming}\n\n"
            "Intenção:"
        )
    except Exception:
        classification = _keyword_classify(incoming)

    intent = classification
    target = {"FAQ": "faq", "HUMANO": "handoff", "CANCEL": "cancel"}.get(intent, "faq")
    logger.info(f"[TRIAGE] text=\"{incoming[:50]}\" → intent={intent} → node={target}")
    return {"node": target, "state_update": {"intent": intent, "flow_step": "triaged"}, "response": None}


def faq_node(state: AgentState) -> Dict[str, Any]:
    fabric_context = _get_fabric_context()
    user_question = state.get("incoming_text", "")

    greetings = ["olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "hello", "hi", "hey"]
    is_greeting = any(g in user_question.lower().strip() for g in greetings) and len(user_question.strip()) < 30

    if is_greeting:
        prompt = (
            "Você é Camila, consultora de moda da C&N Tecidos em Campina Grande, PB. "
            "O cliente acabou de mandar uma saudação no WhatsApp. "
            "Responda como uma pessoa real e simpática, não como um robô. "
            "Seja breve e natural (2-3 linhas máx). "
            "Cumprimente de volta e pergunte como pode ajudar. "
            "NÃO use emojis excessivos. NÃO se apresente como 'assistente' ou 'bot'. "
            "NÃO liste opções numeradas. Apenas converse naturalmente.\n\n"
            f"Cliente disse: {user_question}"
        )
    else:
        prompt = (
            "Você é Camila, consultora de moda da C&N Tecidos em Campina Grande, PB. "
            "Responda como uma pessoa real conversando no WhatsApp — direta, simpática e útil. "
            "Seja breve (3-4 linhas máx). Use linguagem informal e natural. "
            "NÃO use emojis excessivos. NÃO se apresente como 'assistente' ou 'bot'. "
            "NÃO diga 'como posso ajudar' se já está respondendo algo. "
            "Se não souber algo específico, seja honesta e sugira que o cliente visite a loja.\n\n"
            f"Contexto sobre a loja: {fabric_context}\n\n"
            f"Cliente pergunta: {user_question}"
        )

    answer = generate_response_with_gemini(prompt)

    # If Gemini failed (quota, error, etc), send friendly handoff message
    if not answer:
        logger.warning(f"[FAQ] Gemini failed for jid={state.get('remote_jid','')[:20]} — sending AI failure handoff")
        return {
            "node": "handoff",
            "state_update": {"intent": "HUMANO", "flow_step": "ai_failure_handoff"},
            "response": AI_FAILURE_MESSAGE,
        }

    state_updates: Dict[str, Any] = {"response": answer, "flow_step": "idle"}
    return {"node": "faq", "state_update": state_updates, "response": answer}


def human_handoff_node(state: AgentState) -> Dict[str, Any]:
    state_updates = {"is_human_active": True, "flow_step": "handoff"}
    handoff_msg = (
        "Claro! Vou te passar com um dos nossos atendentes. "
        f"É só clicar aqui: {HANDOFF_LINK}"
    )
    return {"node": "idle", "state_update": state_updates, "response": handoff_msg}


def cancel_node(state: AgentState) -> Dict[str, Any]:
    state_updates = {"flow_step": "idle", "incoming_text": "", "intent": "FAQ"}
    return {"node": "END", "state_update": state_updates, "response": "Tudo bem! Se precisar, é só mandar mensagem. Até mais! 👋"}